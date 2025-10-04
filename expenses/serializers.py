"""
Serializers for expense management API
"""
from rest_framework import serializers
from .models import (
    Expense, ExpenseCategory, ApprovalRule, ApprovalStep, 
    ExpenseApproval, Notification
)
from users.models import User, Company


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'country', 'currency', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'full_name', 'role', 'phone', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name', 'description', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class ExpenseSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    category = ExpenseCategorySerializer(read_only=True)
    category_id = serializers.UUIDField(write_only=True)
    amount_in_company_currency = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    exchange_rate = serializers.DecimalField(max_digits=10, decimal_places=6, read_only=True)
    
    class Meta:
        model = Expense
        fields = [
            'id', 'user', 'amount', 'currency', 'amount_in_company_currency', 
            'exchange_rate', 'category', 'category_id', 'description', 
            'expense_date', 'status', 'rejection_reason', 'receipt_image', 
            'ocr_data', 'created_at', 'updated_at', 'submitted_at', 'approved_at'
        ]
        read_only_fields = [
            'id', 'user', 'amount_in_company_currency', 'exchange_rate', 
            'created_at', 'updated_at', 'submitted_at', 'approved_at'
        ]


class ExpenseCreateSerializer(serializers.ModelSerializer):
    category_id = serializers.UUIDField()
    
    class Meta:
        model = Expense
        fields = [
            'amount', 'currency', 'category_id', 'description', 
            'expense_date', 'receipt_image'
        ]
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        validated_data['company'] = validated_data['user'].company
        
        # Convert currency if needed
        from .services import CurrencyService
        from decimal import Decimal
        
        if validated_data['currency'] != validated_data['company'].currency:
            conversion = CurrencyService.convert_currency(
                validated_data['amount'],
                validated_data['currency'],
                validated_data['company'].currency
            )
            validated_data['amount_in_company_currency'] = conversion['converted_amount']
            validated_data['exchange_rate'] = conversion['exchange_rate']
        else:
            validated_data['amount_in_company_currency'] = validated_data['amount']
            validated_data['exchange_rate'] = Decimal('1.0')
        
        return super().create(validated_data)


class ApprovalStepSerializer(serializers.ModelSerializer):
    approver = UserSerializer(read_only=True)
    approver_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = ApprovalStep
        fields = ['id', 'step_number', 'approver', 'approver_id', 'is_required']
        read_only_fields = ['id']


class ApprovalRuleSerializer(serializers.ModelSerializer):
    steps = ApprovalStepSerializer(many=True, read_only=True)
    specific_approver = UserSerializer(read_only=True)
    specific_approver_id = serializers.UUIDField(write_only=True, required=False)
    
    class Meta:
        model = ApprovalRule
        fields = [
            'id', 'name', 'description', 'rule_type', 'percentage_threshold',
            'specific_approver', 'specific_approver_id', 'is_manager_approver',
            'min_amount', 'max_amount', 'is_active', 'steps', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ExpenseApprovalSerializer(serializers.ModelSerializer):
    approver = UserSerializer(read_only=True)
    expense = ExpenseSerializer(read_only=True)
    
    class Meta:
        model = ExpenseApproval
        fields = [
            'id', 'expense', 'approver', 'status', 'comments',
            'created_at', 'updated_at', 'approved_at'
        ]
        read_only_fields = ['id', 'expense', 'approver', 'created_at', 'updated_at']


class ExpenseApprovalActionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['approved', 'rejected'])
    comments = serializers.CharField(required=False, allow_blank=True)


class NotificationSerializer(serializers.ModelSerializer):
    expense = ExpenseSerializer(read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message',
            'expense', 'is_read', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class CountryCurrencySerializer(serializers.Serializer):
    """Serializer for country and currency data from external API"""
    name = serializers.DictField()
    currencies = serializers.DictField()
    
    def to_representation(self, instance):
        return {
            'country': instance['name']['common'],
            'currency_code': list(instance['currencies'].keys())[0] if instance['currencies'] else None,
            'currency_name': list(instance['currencies'].values())[0]['name'] if instance['currencies'] else None
        }
