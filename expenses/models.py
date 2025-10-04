from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
import uuid
from decimal import Decimal

User = get_user_model()


class ExpenseCategory(models.Model):
    """Categories for expense types (Travel, Food, Office Supplies, etc.)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    company = models.ForeignKey('users.Company', on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Expense Categories"
        unique_together = ['name', 'company']

    def __str__(self):
        return self.name


class Expense(models.Model):
    """Main expense model"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')
    company = models.ForeignKey('users.Company', on_delete=models.CASCADE)
    
    # Expense details
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    currency = models.CharField(max_length=10, default='USD')
    amount_in_company_currency = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE)
    description = models.TextField()
    expense_date = models.DateField()
    
    # Status and workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    rejection_reason = models.TextField(blank=True, null=True)
    
    # OCR and receipt data
    receipt_image = models.ImageField(upload_to='receipts/', blank=True, null=True)
    ocr_data = models.JSONField(blank=True, null=True)  # Store OCR extracted data
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.full_name} - {self.amount} {self.currency} - {self.status}"

    def save(self, *args, **kwargs):
        # Auto-convert to company currency if different from company default
        if self.currency != self.company.currency:
            # This will be handled by the currency conversion service
            pass
        super().save(*args, **kwargs)


class ApprovalRule(models.Model):
    """Approval rules configuration"""
    RULE_TYPES = [
        ('percentage', 'Percentage'),
        ('specific', 'Specific Approver'),
        ('hybrid', 'Hybrid'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey('users.Company', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    # Rule configuration
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    percentage_threshold = models.IntegerField(null=True, blank=True, help_text="Percentage of approvers needed")
    specific_approver = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    # Manager approval requirement
    is_manager_approver = models.BooleanField(default=True)
    
    # Amount thresholds
    min_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.company.name}"

    def applies_to_expense(self, expense):
        """Check if this rule applies to the given expense"""
        if not self.is_active:
            return False
        
        # Check amount thresholds
        if self.min_amount and expense.amount_in_company_currency < self.min_amount:
            return False
        if self.max_amount and expense.amount_in_company_currency > self.max_amount:
            return False
        
        return True


class ApprovalStep(models.Model):
    """Individual steps in approval workflow"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule = models.ForeignKey(ApprovalRule, on_delete=models.CASCADE, related_name='steps')
    step_number = models.PositiveIntegerField()
    approver = models.ForeignKey(User, on_delete=models.CASCADE)
    is_required = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['rule', 'step_number']
        ordering = ['step_number']

    def __str__(self):
        return f"Step {self.step_number}: {self.approver.full_name}"


class ExpenseApproval(models.Model):
    """Individual approval records for expenses"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='approvals')
    approver = models.ForeignKey(User, on_delete=models.CASCADE)
    step = models.ForeignKey(ApprovalStep, on_delete=models.CASCADE, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    comments = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['expense', 'approver']
        ordering = ['created_at']

    def __str__(self):
        return f"{self.expense} - {self.approver.full_name} - {self.status}"


class Notification(models.Model):
    """Notification system for approval requests"""
    NOTIFICATION_TYPES = [
        ('approval_request', 'Approval Request'),
        ('expense_approved', 'Expense Approved'),
        ('expense_rejected', 'Expense Rejected'),
        ('expense_submitted', 'Expense Submitted'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Related objects
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, null=True, blank=True)
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.full_name} - {self.title}"
