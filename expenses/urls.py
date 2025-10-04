"""
URL configuration for expenses app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ExpenseViewSet, ExpenseCategoryViewSet, ApprovalRuleViewSet,
    ExpenseApprovalViewSet, NotificationViewSet, CountryCurrencyAPIView,
    CurrencyConversionAPIView, OCRProcessAPIView
)

router = DefaultRouter()
router.register(r'expenses', ExpenseViewSet)
router.register(r'categories', ExpenseCategoryViewSet)
router.register(r'approval-rules', ApprovalRuleViewSet)
router.register(r'approvals', ExpenseApprovalViewSet)
router.register(r'notifications', NotificationViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('countries-currencies/', CountryCurrencyAPIView.as_view(), name='countries-currencies'),
    path('currency-conversion/', CurrencyConversionAPIView.as_view(), name='currency-conversion'),
    path('ocr-process/', OCRProcessAPIView.as_view(), name='ocr-process'),
]
