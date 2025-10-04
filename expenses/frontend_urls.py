"""
Frontend URL patterns for expense management
"""
from django.urls import path
from . import frontend_views

urlpatterns = [
    # Authentication
    path('login/', frontend_views.login_view, name='login'),
    path('register/', frontend_views.register_view, name='register'),
    path('logout/', frontend_views.logout_view, name='logout'),
    
    # Main application
    path('', frontend_views.dashboard, name='dashboard'),
    path('expenses/', frontend_views.expenses_list, name='expenses'),
    path('submit-expense/', frontend_views.submit_expense, name='submit_expense'),
    path('expense/<uuid:expense_id>/', frontend_views.expense_detail, name='expense_detail'),
    path('approvals/', frontend_views.approvals_list, name='approvals'),
    path('approve/<uuid:approval_id>/', frontend_views.approve_expense, name='approve_expense'),
    path('notifications/', frontend_views.notifications_list, name='notifications'),
    path('users/', frontend_views.users_list, name='users'),
    path('approval-rules/', frontend_views.approval_rules_list, name='approval_rules'),
    path('profile/', frontend_views.profile, name='profile'),
]
