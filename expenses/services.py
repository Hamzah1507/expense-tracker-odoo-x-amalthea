"""
Services for expense management functionality
"""
import requests
import json
from decimal import Decimal
from typing import Dict, Optional, List
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class CurrencyService:
    """Service for currency conversion and country/currency data"""
    
    @staticmethod
    def get_countries_and_currencies() -> List[Dict]:
        """Fetch countries and their currencies from REST Countries API"""
        try:
            response = requests.get(
                'https://restcountries.com/v3.1/all?fields=name,currencies',
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch countries data: {e}")
            return []
    
    @staticmethod
    def convert_currency(amount: Decimal, from_currency: str, to_currency: str) -> Dict:
        """
        Convert currency using ExchangeRate API
        Returns: {'converted_amount': Decimal, 'exchange_rate': Decimal}
        """
        try:
            if from_currency == to_currency:
                return {
                    'converted_amount': amount,
                    'exchange_rate': Decimal('1.0')
                }
            
            response = requests.get(
                f'https://api.exchangerate-api.com/v4/latest/{from_currency}',
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if to_currency not in data['rates']:
                raise ValueError(f"Currency {to_currency} not found in exchange rates")
            
            exchange_rate = Decimal(str(data['rates'][to_currency]))
            converted_amount = amount * exchange_rate
            
            return {
                'converted_amount': converted_amount,
                'exchange_rate': exchange_rate
            }
            
        except requests.RequestException as e:
            logger.error(f"Currency conversion failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Currency conversion error: {e}")
            raise


class OCRService:
    """Service for OCR functionality to extract data from receipts"""
    
    @staticmethod
    def extract_receipt_data(image_path: str) -> Dict:
        """
        Extract data from receipt image using OCR
        This is a placeholder implementation - you'll need to integrate with
        actual OCR service like Google Vision API, AWS Textract, or Tesseract
        """
        # Placeholder implementation
        # In production, integrate with actual OCR service
        return {
            'amount': None,
            'date': None,
            'merchant_name': None,
            'description': None,
            'category': None,
            'confidence': 0.0,
            'raw_text': '',
            'line_items': []
        }
    
    @staticmethod
    def process_receipt_with_ocr(expense, image_path: str) -> Dict:
        """
        Process receipt image and populate expense fields
        """
        try:
            ocr_data = OCRService.extract_receipt_data(image_path)
            
            # Update expense with OCR data
            expense.ocr_data = ocr_data
            
            # Auto-populate fields if confidence is high enough
            if ocr_data.get('confidence', 0) > 0.8:
                if ocr_data.get('amount'):
                    expense.amount = Decimal(str(ocr_data['amount']))
                
                if ocr_data.get('date'):
                    expense.expense_date = ocr_data['date']
                
                if ocr_data.get('description'):
                    expense.description = ocr_data['description']
                
                if ocr_data.get('merchant_name'):
                    expense.description = f"{expense.description} - {ocr_data['merchant_name']}"
            
            expense.save()
            return ocr_data
            
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            return {}


class ApprovalWorkflowService:
    """Service for managing approval workflows"""
    
    @staticmethod
    def get_applicable_rules(expense) -> List:
        """Get approval rules that apply to the given expense"""
        from .models import ApprovalRule
        
        rules = ApprovalRule.objects.filter(
            company=expense.company,
            is_active=True
        )
        
        applicable_rules = []
        for rule in rules:
            if rule.applies_to_expense(expense):
                applicable_rules.append(rule)
        
        return applicable_rules
    
    @staticmethod
    def create_approval_workflow(expense):
        """Create approval workflow for an expense based on applicable rules"""
        from .models import ExpenseApproval, ApprovalStep, Notification
        from django.utils import timezone
        
        rules = ApprovalWorkflowService.get_applicable_rules(expense)
        
        if not rules:
            # No approval needed - auto-approve
            expense.status = 'approved'
            expense.approved_at = timezone.now()
            expense.save()
            return
        
        # Create approval records for each rule
        for rule in rules:
            # Manager approval first if required
            if rule.is_manager_approver and expense.user.manager:
                approval, created = ExpenseApproval.objects.get_or_create(
                    expense=expense,
                    approver=expense.user.manager,
                    defaults={'status': 'pending'}
                )
                
                if created:
                    # Create notification
                    Notification.objects.create(
                        user=expense.user.manager,
                        notification_type='approval_request',
                        title=f'Approval Request: {expense.user.full_name}',
                        message=f'New expense requires your approval: {expense.amount} {expense.currency}',
                        expense=expense
                    )
            
            # Create approvals for rule steps
            for step in rule.steps.all():
                approval, created = ExpenseApproval.objects.get_or_create(
                    expense=expense,
                    approver=step.approver,
                    defaults={'status': 'pending', 'step': step}
                )
                
                if created:
                    # Create notification
                    Notification.objects.create(
                        user=step.approver,
                        notification_type='approval_request',
                        title=f'Approval Request: {expense.user.full_name}',
                        message=f'New expense requires your approval: {expense.amount} {expense.currency}',
                        expense=expense
                    )
    
    @staticmethod
    def process_approval(expense_approval, status: str, comments: str = None):
        """Process an approval decision"""
        from .models import Notification
        from django.utils import timezone
        
        expense_approval.status = status
        expense_approval.comments = comments
        expense_approval.approved_at = timezone.now()
        expense_approval.save()
        
        # Create notification for expense submitter
        Notification.objects.create(
            user=expense_approval.expense.user,
            notification_type=f'expense_{status}',
            title=f'Expense {status.title()}',
            message=f'Your expense has been {status} by {expense_approval.approver.full_name}',
            expense=expense_approval.expense
        )
        
        # Check if expense should be auto-approved/rejected
        ApprovalWorkflowService.check_expense_status(expense_approval.expense)
    
    @staticmethod
    def check_expense_status(expense):
        """Check if expense should be auto-approved or rejected based on rules"""
        from .models import ApprovalRule
        from django.utils import timezone
        
        rules = ApprovalWorkflowService.get_applicable_rules(expense)
        
        for rule in rules:
            if rule.rule_type == 'percentage':
                # Check if percentage threshold is met
                total_approvers = expense.approvals.count()
                approved_count = expense.approvals.filter(status='approved').count()
                
                if total_approvers > 0:
                    approval_percentage = (approved_count / total_approvers) * 100
                    if approval_percentage >= rule.percentage_threshold:
                        expense.status = 'approved'
                        expense.approved_at = timezone.now()
                        expense.save()
                        return
            
            elif rule.rule_type == 'specific':
                # Check if specific approver approved
                if expense.approvals.filter(
                    approver=rule.specific_approver,
                    status='approved'
                ).exists():
                    expense.status = 'approved'
                    expense.approved_at = timezone.now()
                    expense.save()
                    return
            
            elif rule.rule_type == 'hybrid':
                # Check both percentage and specific approver
                # Implementation depends on business logic
                pass
        
        # Check if any approval was rejected
        if expense.approvals.filter(status='rejected').exists():
            expense.status = 'rejected'
            expense.save()
