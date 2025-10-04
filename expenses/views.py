"""
API Views for expense management
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from .models import (
    Expense, ExpenseCategory, ApprovalRule, ApprovalStep,
    ExpenseApproval, Notification
)
from .serializers import (
    ExpenseSerializer, ExpenseCreateSerializer, ExpenseCategorySerializer,
    ApprovalRuleSerializer, ExpenseApprovalSerializer, ExpenseApprovalActionSerializer,
    NotificationSerializer, CountryCurrencySerializer
)
from .services import CurrencyService, ApprovalWorkflowService
from users.models import User


class ExpenseViewSet(viewsets.ModelViewSet):
    """ViewSet for expense management"""
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Expense.objects.all()
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_admin():
            # Admin can see all expenses in their company
            return Expense.objects.filter(company=user.company)
        elif user.is_manager():
            # Manager can see their own expenses and their team's expenses
            team_members = User.objects.filter(manager=user)
            return Expense.objects.filter(
                Q(user=user) | Q(user__in=team_members)
            )
        else:
            # Employee can only see their own expenses
            return Expense.objects.filter(user=user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ExpenseCreateSerializer
        return ExpenseSerializer
    
    def perform_create(self, serializer):
        expense = serializer.save()
        
        # Create approval workflow
        ApprovalWorkflowService.create_approval_workflow(expense)
        
        # Create notification for expense submission
        Notification.objects.create(
            user=expense.user,
            notification_type='expense_submitted',
            title='Expense Submitted',
            message=f'Your expense of {expense.amount} {expense.currency} has been submitted for approval',
            expense=expense
        )
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit expense for approval"""
        expense = self.get_object()
        
        if expense.status != 'draft':
            return Response(
                {'error': 'Expense can only be submitted from draft status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        expense.status = 'pending'
        expense.submitted_at = timezone.now()
        expense.save()
        
        # Create approval workflow
        ApprovalWorkflowService.create_approval_workflow(expense)
        
        return Response({'status': 'submitted'})
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel expense"""
        expense = self.get_object()
        
        if expense.status not in ['draft', 'pending']:
            return Response(
                {'error': 'Expense cannot be cancelled in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        expense.status = 'cancelled'
        expense.save()
        
        return Response({'status': 'cancelled'})
    
    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        """Get expenses pending approval for current user"""
        user = request.user
        
        if not (user.is_manager() or user.is_admin()):
            return Response(
                {'error': 'Only managers and admins can view pending approvals'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        pending_expenses = Expense.objects.filter(
            approvals__approver=user,
            approvals__status='pending',
            status='pending'
        ).distinct()
        
        serializer = self.get_serializer(pending_expenses, many=True)
        return Response(serializer.data)


class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for expense categories"""
    serializer_class = ExpenseCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ExpenseCategory.objects.all()
    
    def get_queryset(self):
        return ExpenseCategory.objects.filter(
            company=self.request.user.company,
            is_active=True
        )
    
    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class ApprovalRuleViewSet(viewsets.ModelViewSet):
    """ViewSet for approval rules"""
    serializer_class = ApprovalRuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ApprovalRule.objects.all()
    
    def get_queryset(self):
        if not self.request.user.is_admin():
            return ApprovalRule.objects.none()
        return ApprovalRule.objects.filter(company=self.request.user.company)
    
    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class ExpenseApprovalViewSet(viewsets.ModelViewSet):
    """ViewSet for expense approvals"""
    serializer_class = ExpenseApprovalSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ExpenseApproval.objects.all()
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_admin():
            return ExpenseApproval.objects.filter(expense__company=user.company)
        else:
            return ExpenseApproval.objects.filter(approver=user)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve an expense"""
        approval = self.get_object()
        
        if approval.status != 'pending':
            return Response(
                {'error': 'Approval is not in pending status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ExpenseApprovalActionSerializer(data=request.data)
        if serializer.is_valid():
            status_value = serializer.validated_data['status']
            comments = serializer.validated_data.get('comments', '')
            
            # Process approval
            ApprovalWorkflowService.process_approval(approval, status_value, comments)
            
            return Response({'status': 'processed'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet for notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Notification.objects.all()
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked_read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)
        return Response({'status': 'all_marked_read'})


class CountryCurrencyAPIView(APIView):
    """API for fetching countries and currencies"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get list of countries and their currencies"""
        countries_data = CurrencyService.get_countries_and_currencies()
        
        # Filter out countries without currencies
        filtered_data = [
            country for country in countries_data 
            if country.get('currencies')
        ]
        
        serializer = CountryCurrencySerializer(filtered_data, many=True)
        return Response(serializer.data)


class CurrencyConversionAPIView(APIView):
    """API for currency conversion"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Convert currency"""
        amount = request.data.get('amount')
        from_currency = request.data.get('from_currency')
        to_currency = request.data.get('to_currency')
        
        if not all([amount, from_currency, to_currency]):
            return Response(
                {'error': 'Missing required fields: amount, from_currency, to_currency'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from decimal import Decimal
            amount_decimal = Decimal(str(amount))
            
            conversion = CurrencyService.convert_currency(
                amount_decimal, from_currency, to_currency
            )
            
            return Response({
                'original_amount': amount,
                'from_currency': from_currency,
                'converted_amount': str(conversion['converted_amount']),
                'to_currency': to_currency,
                'exchange_rate': str(conversion['exchange_rate'])
            })
            
        except Exception as e:
            return Response(
                {'error': f'Currency conversion failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class OCRProcessAPIView(APIView):
    """API for OCR processing of receipts"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Process receipt image with OCR"""
        expense_id = request.data.get('expense_id')
        image_file = request.FILES.get('image')
        
        if not expense_id or not image_file:
            return Response(
                {'error': 'Missing required fields: expense_id, image'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            expense = get_object_or_404(Expense, id=expense_id, user=request.user)
            
            # Save image to expense
            expense.receipt_image = image_file
            expense.save()
            
            # Process with OCR
            from .services import OCRService
            ocr_data = OCRService.process_receipt_with_ocr(expense, image_file)
            
            return Response({
                'status': 'processed',
                'ocr_data': ocr_data,
                'expense': ExpenseSerializer(expense).data
            })
            
        except Exception as e:
            return Response(
                {'error': f'OCR processing failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
