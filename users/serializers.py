"""
Serializers for user authentication and management
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, Company


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'country', 'currency', 'created_at']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    company_name = serializers.CharField(write_only=True, required=False)
    country = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 'password', 
            'password_confirm', 'phone', 'role', 'company_name', 'country'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'role': {'default': 'employee'}
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        password_confirm = validated_data.pop('password_confirm')
        company_name = validated_data.pop('company_name', None)
        country = validated_data.pop('country', None)
        
        # Create company if this is the first user (admin)
        if validated_data.get('role') == 'admin' and company_name:
            company = Company.objects.create(
                name=company_name,
                country=country or 'United States',
                currency='USD'  # Default currency
            )
            validated_data['company'] = company
        elif validated_data.get('role') == 'admin':
            # If admin but no company name, create default company
            company = Company.objects.create(
                name=f"{validated_data['first_name']}'s Company",
                country=country or 'United States',
                currency='USD'
            )
            validated_data['company'] = company
        
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include username and password')
        
        return attrs


class UserSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'full_name', 'role', 'phone', 'is_active', 'company', 
            'manager', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'role', 'manager']
    
    def update(self, instance, validated_data):
        # Only admins can change roles and managers
        if not self.context['request'].user.is_admin():
            validated_data.pop('role', None)
            validated_data.pop('manager', None)
        
        return super().update(instance, validated_data)
