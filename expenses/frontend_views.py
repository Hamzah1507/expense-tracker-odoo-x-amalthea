"""
Frontend views for expense management
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal
import json
import requests

from .models import Expense, ExpenseCategory, ApprovalRule, ExpenseApproval, Notification
from .services import ApprovalWorkflowService, CurrencyService
from users.models import User, Company


@login_required
def dashboard(request):
    """Main dashboard view"""
    user = request.user

    if user.is_admin():
        total_expenses = Expense.objects.filter(company=user.company).count()
        pending_approvals = ExpenseApproval.objects.filter(expense__company=user.company, status='pending').count()
        total_users = user.company.user_set.count()
        recent_expenses = Expense.objects.filter(company=user.company).order_by('-created_at')[:5]

        context = {
            'total_expenses': total_expenses,
            'pending_approvals': pending_approvals,
            'total_users': total_users,
            'recent_expenses': recent_expenses,
            'user_role': 'admin'
        }

    elif user.is_manager():
        team_members = user.user_set.all()
        team_expenses = Expense.objects.filter(Q(user=user) | Q(user__in=team_members))
        total_expenses = team_expenses.count()
        pending_approvals = ExpenseApproval.objects.filter(approver=user, status='pending').count()
        recent_expenses = team_expenses.order_by('-created_at')[:5]

        context = {
            'total_expenses': total_expenses,
            'pending_approvals': pending_approvals,
            'team_members': team_members,
            'recent_expenses': recent_expenses,
            'user_role': 'manager'
        }

    else:
        user_expenses = Expense.objects.filter(user=user)
        total_expenses = user_expenses.count()
        pending_expenses = user_expenses.filter(status='pending').count()
        approved_expenses = user_expenses.filter(status='approved').count()
        recent_expenses = user_expenses.order_by('-created_at')[:5]

        context = {
            'total_expenses': total_expenses,
            'pending_expenses': pending_expenses,
            'approved_expenses': approved_expenses,
            'recent_expenses': recent_expenses,
            'user_role': 'employee'
        }

    return render(request, 'expenses/dashboard.html', context)


@login_required
def expenses_list(request):
    """List expenses for current user"""
    user = request.user

    if user.is_admin():
        expenses = Expense.objects.filter(company=user.company)
    elif user.is_manager():
        team_members = user.user_set.all()
        expenses = Expense.objects.filter(Q(user=user) | Q(user__in=team_members))
    else:
        expenses = Expense.objects.filter(user=user)

    status_filter = request.GET.get('status')
    if status_filter:
        expenses = expenses.filter(status=status_filter)

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        expenses = expenses.filter(expense_date__gte=date_from)
    if date_to:
        expenses = expenses.filter(expense_date__lte=date_to)

    expenses = expenses.order_by('-created_at')

    context = {
        'expenses': expenses,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
    }

    return render(request, 'expenses/expenses_list.html', context)


@login_required
def submit_expense(request):
    """Submit new expense form"""
    if request.method == 'POST':
        try:
            amount = request.POST.get('amount')
            currency = request.POST.get('currency')
            category_id = request.POST.get('category')
            description = request.POST.get('description')
            expense_date = request.POST.get('expense_date')

            category = get_object_or_404(ExpenseCategory, id=category_id, company=request.user.company)

            expense = Expense.objects.create(
                user=request.user,
                company=request.user.company,
                amount=amount,
                currency=currency,
                category=category,
                description=description,
                expense_date=expense_date,
                status='draft'
            )

            # Currency conversion
            if currency != request.user.company.currency:
                conversion = CurrencyService.convert_currency(
                    Decimal(amount),
                    currency,
                    request.user.company.currency
                )
                expense.amount_in_company_currency = conversion['converted_amount']
                expense.exchange_rate = conversion['exchange_rate']
            else:
                expense.amount_in_company_currency = Decimal(amount)
                expense.exchange_rate = 1.0

            # Save expense
            expense.save()

            # Handle receipt upload
            if 'receipt_image' in request.FILES:
                expense.receipt_image = request.FILES['receipt_image']
                expense.save()

            messages.success(request, 'Expense created successfully!')
            return redirect('expenses')

        except Exception as e:
            messages.error(request, f'Error creating expense: {str(e)}')

    # GET request: send categories and other context
    categories = ExpenseCategory.objects.filter(company=request.user.company, is_active=True)
    countries_data = CurrencyService.get_countries_and_currencies()

    context = {
        'categories': categories,
        'countries_data': countries_data[:50],
        'company_currency': request.user.company.currency,
        'today': timezone.now(),  # ✅ Add this so the date input works
    }

    return render(request, 'expenses/submit_expense.html', context)


@login_required
def expense_detail(request, expense_id):
    """View expense details"""
    user = request.user

    if user.is_admin():
        expense = get_object_or_404(Expense, id=expense_id, company=user.company)
    elif user.is_manager():
        team_members = user.user_set.all()
        expense = Expense.objects.filter(Q(user=user) | Q(user__in=team_members), id=expense_id).first()
        if not expense:
            from django.http import Http404
            raise Http404("Expense not found")
    else:
        expense = get_object_or_404(Expense, id=expense_id, user=user)

    approvals = ExpenseApproval.objects.filter(expense=expense).order_by('created_at')
    return render(request, 'expenses/expense_detail.html', {'expense': expense, 'approvals': approvals})


@login_required
def approvals_list(request):
    """List pending approvals for managers/admins"""
    user = request.user

    if not (user.is_manager() or user.is_admin()):
        messages.error(request, 'You do not have permission to view approvals.')
        return redirect('dashboard')

    if user.is_admin():
        pending_approvals = ExpenseApproval.objects.filter(expense__company=user.company, status='pending').order_by('-created_at')
    else:
        pending_approvals = ExpenseApproval.objects.filter(approver=user, status='pending').order_by('-created_at')

    return render(request, 'expenses/approvals_list.html', {'pending_approvals': pending_approvals})


@login_required
def approve_expense(request, approval_id):
    """Approve or reject an expense"""
    if request.method == 'POST':
        approval = get_object_or_404(ExpenseApproval, id=approval_id, approver=request.user)
        action = request.POST.get('action')
        comments = request.POST.get('comments', '')

        try:
            if action == 'approve':
                ApprovalWorkflowService.process_approval(approval, 'approved', comments)
                messages.success(request, 'Expense approved successfully!')
            elif action == 'reject':
                ApprovalWorkflowService.process_approval(approval, 'rejected', comments)
                messages.success(request, 'Expense rejected.')
            else:
                messages.error(request, 'Invalid action.')
                return redirect('approvals')

            return redirect('approvals')

        except Exception as e:
            messages.error(request, f'Error processing approval: {str(e)}')
            return redirect('approvals')

    return redirect('approvals')


@login_required
def notifications_list(request):
    """List user notifications"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    notifications.update(is_read=True)
    return render(request, 'expenses/notifications_list.html', {'notifications': notifications})


@login_required
def users_list(request):
    """List company users (Admin/Manager)"""
    if not (request.user.is_admin() or request.user.is_manager()):
        messages.error(request, 'You do not have permission to view users.')
        return redirect('dashboard')

    users = User.objects.filter(company=request.user.company).order_by('role', 'first_name')
    return render(request, 'expenses/users_list.html', {'users': users})


@login_required
def approval_rules_list(request):
    """List approval rules (Admin only)"""
    if not request.user.is_admin():
        messages.error(request, 'You do not have permission to view approval rules.')
        return redirect('dashboard')

    rules = ApprovalRule.objects.filter(company=request.user.company).order_by('-created_at')
    return render(request, 'expenses/approval_rules_list.html', {'rules': rules})


@login_required
def profile(request):
    user = request.user

    approved_expenses = user.expenses.filter(status='approved')
    pending_expenses = user.expenses.filter(status='pending')

    context = {
        'approved_expenses_count': approved_expenses.count(),
        'pending_expenses_count': pending_expenses.count(),
        'approved_expenses': approved_expenses,
        'pending_expenses': pending_expenses,
    }

    return render(request, 'expenses/profile.html', context)


def login_view(request):
    """Login view"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, f'Welcome back, {user.full_name}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'expenses/login.html')


def register_view(request):
    """Registration view"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        try:
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            username = request.POST.get('username')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            role = request.POST.get('role')
            password = request.POST.get('password')
            password_confirm = request.POST.get('password_confirm')
            company_name = request.POST.get('company_name')
            country = request.POST.get('country')

            if password != password_confirm:
                messages.error(request, 'Passwords do not match.')
                return render(request, 'expenses/register.html')

            company = None
            if role == 'admin':
                company = Company.objects.create(
                    name=company_name or f"{first_name}'s Company",
                    country=country or 'United States',
                    currency='USD'
                )

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role=role,
                company=company
            )

            login(request, user)
            messages.success(request, f'Account created successfully! Welcome, {user.full_name}!')
            return redirect('dashboard')

        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')

    return render(request, 'expenses/register.html')


@login_required
def logout_view(request):
    """Logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')

@login_required
def approval_rules_list(request):
    if not request.user.is_admin():
        messages.error(request, 'You do not have permission to view approval rules.')
        return redirect('dashboard')
    
    rules = ApprovalRule.objects.filter(company=request.user.company).order_by('-created_at')
    
    context = {'rules': rules}
    
    return render(request, 'expenses/approval_rules_list.html', context)

@login_required
def expense_detail(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    return render(request, 'expenses/expense_detail.html', {'expense': expense})