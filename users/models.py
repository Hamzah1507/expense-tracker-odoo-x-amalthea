from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator
import uuid


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    country = models.CharField(max_length=255)
    currency = models.CharField(max_length=10, default='USD')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("manager", "Manager"),
        ("employee", "Employee"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='employee')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    manager = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}" or self.username

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

    def is_manager(self):
        return self.role == 'manager'
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_employee(self):
        return self.role == 'employee'
