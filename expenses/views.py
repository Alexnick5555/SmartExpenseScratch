"""
Views for SmartExpense - Personal Expense & Subscription Tracker
Developed by Nitish Mishra & Nishant Singh
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Q, Count
from django.db.models.functions import TruncMonth, TruncDay
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from dateutil.relativedelta import relativedelta
import csv
import json
from .models import User, Account, Transaction, Subscription, Budget, SavingsGoal, Category, TransactionTemplate, RecurringTransaction
from .forms import (
    UserRegistrationForm, UserLoginForm, UserProfileForm,
    AccountForm, TransactionForm, QuickTransactionForm,
    SubscriptionForm, BudgetForm, SavingsGoalForm, DateRangeForm,
    PasswordChangeForm, DeleteAccountForm, AdvancedSearchForm, TransactionTemplateForm, RecurringTransactionForm
)


# ─── Smart Engine helpers ─────────────────────────────────────────────────────

def _compute_health_score(month_income, month_expenses, budget_data, last_month_expense, tx_count_30):
    score = 0

    # 1. Savings rate (0–35 pts)
    if month_income > 0:
        rate = float((month_income - month_expenses) / month_income * 100)
        s = 35 if rate >= 30 else 28 if rate >= 20 else 18 if rate >= 10 else 8 if rate > 0 else 0
    else:
        s = 12
    score += s

    # 2. Budget adherence (0–25 pts)
    if budget_data:
        avg_pct = sum(float(b['percentage']) for b in budget_data) / len(budget_data)
        s = 25 if avg_pct <= 60 else 18 if avg_pct <= 80 else 10 if avg_pct <= 95 else 3
    else:
        s = 12
    score += s

    # 3. Expense trend vs last month (0–20 pts)
    if last_month_expense > 0:
        change = float((month_expenses - last_month_expense) / last_month_expense * 100)
        s = 20 if change <= -10 else 15 if change <= 0 else 10 if change <= 10 else 4 if change <= 25 else 0
    else:
        s = 10
    score += s

    # 4. Logging consistency – transactions in last 30 days (0–20 pts)
    s = 20 if tx_count_30 >= 20 else 15 if tx_count_30 >= 10 else 10 if tx_count_30 >= 5 else 5 if tx_count_30 >= 1 else 0
    score += s

    grade = 'A' if score >= 80 else 'B' if score >= 60 else 'C' if score >= 40 else 'D'
    color = '#22c55e' if score >= 80 else '#3b82f6' if score >= 60 else '#f59e0b' if score >= 40 else '#ef4444'
    label = 'Excellent' if score >= 80 else 'Good' if score >= 60 else 'Fair' if score >= 40 else 'Needs Work'
    dash = round((score / 100) * 301.6, 1)

    return {'score': score, 'grade': grade, 'color': color, 'label': label, 'dash': dash}


def _compute_forecast(today, month_start, month_end, month_expenses):
    days_elapsed = max((today - month_start).days + 1, 1)
    days_in_month = (month_end - month_start).days + 1
    if month_expenses > 0:
        daily_rate = month_expenses / days_elapsed
        return daily_rate * days_in_month
    return Decimal('0')


def _compute_insights(month_income, month_expenses, budget_data,
                      category_expenses, upcoming_subscriptions, forecast, today):
    insights = []

    # Budget alerts
    for b in budget_data:
        pct = float(b['percentage'])
        remaining = float(b['budget'] - b['spent'])
        if pct >= 100:
            insights.append({
                'icon': 'bi-exclamation-triangle-fill', 'color': '#EF4444', 'bg': '#FEE2E2',
                'text': f"Over budget on {b['category'].name}! Spent ₹{float(b['spent']):,.0f} of ₹{float(b['budget']):,.0f}.",
            })
        elif pct >= 80:
            insights.append({
                'icon': 'bi-exclamation-circle-fill', 'color': '#F59E0B', 'bg': '#FEF3C7',
                'text': f"{b['category'].name} budget is {pct:.0f}% used. Only ₹{remaining:,.0f} left.",
            })

    # Forecast vs income
    if forecast > 0 and month_income > 0:
        if forecast > month_income:
            insights.append({
                'icon': 'bi-graph-up-arrow', 'color': '#EF4444', 'bg': '#FEE2E2',
                'text': f"Overspend alert! You're on pace to spend ₹{float(forecast):,.0f} vs income ₹{float(month_income):,.0f}.",
            })
        elif float(forecast) > float(month_income) * 0.85:
            insights.append({
                'icon': 'bi-graph-up', 'color': '#F59E0B', 'bg': '#FEF3C7',
                'text': f"You're on pace to spend ₹{float(forecast):,.0f} this month. Consider cutting back.",
            })
        else:
            proj_save = float(month_income - forecast)
            insights.append({
                'icon': 'bi-piggy-bank-fill', 'color': '#22C55E', 'bg': '#DCFCE7',
                'text': f"Great pace! Projected savings this month: ₹{proj_save:,.0f}.",
            })

    # Top category
    cat_list = list(category_expenses)
    if cat_list:
        top = cat_list[0]
        insights.append({
            'icon': 'bi-tag-fill', 'color': '#6366F1', 'bg': '#EEF2FF',
            'text': f"Biggest spend: {top['category__name']} at ₹{float(top['total']):,.0f} this month.",
        })

    # Upcoming subscriptions
    due_soon = [s for s in upcoming_subscriptions if (s.next_payment - today).days <= 5]
    if due_soon:
        total_due = sum(float(s.amount) for s in due_soon)
        names = ', '.join([s.name for s in due_soon[:2]])
        extra = f' (+{len(due_soon)-2} more)' if len(due_soon) > 2 else ''
        insights.append({
            'icon': 'bi-calendar-check-fill', 'color': '#8B5CF6', 'bg': '#F5F3FF',
            'text': f"Subscriptions due soon: {names}{extra} — ₹{total_due:,.0f} total.",
        })

    # Savings milestone or overspend
    if month_income > 0:
        rate = float((month_income - month_expenses) / month_income * 100)
        if rate >= 25:
            insights.append({
                'icon': 'bi-stars', 'color': '#22C55E', 'bg': '#DCFCE7',
                'text': f"Excellent! You're saving {rate:.0f}% of income — above the 20% recommended target!",
            })
        elif rate < 0:
            insights.append({
                'icon': 'bi-emoji-frown-fill', 'color': '#EF4444', 'bg': '#FEE2E2',
                'text': f"You're spending ₹{float(month_expenses - month_income):,.0f} more than you earn. Time to review!",
            })

    if not insights:
        insights.append({
            'icon': 'bi-lightbulb-fill', 'color': '#6366F1', 'bg': '#EEF2FF',
            'text': 'Add transactions and set budgets to unlock personalized smart insights!',
        })

    return insights[:5]

# ──────────────────────────────────────────────────────────────────────────────


def home(request):
    """Home/Landing page."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html')


def register(request):
    """User registration."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create default cash account for new user
            Account.objects.create(
                user=user,
                name='Cash',
                account_type='cash',
                balance=0,
                currency=user.currency
            )
            login(request, user)
            messages.success(request, 'Welcome to SmartExpense! Your account has been created.')
            return redirect('dashboard')
    else:
        form = UserRegistrationForm()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    return render(request, 'auth/register.html', {'form': form, 'is_ajax': is_ajax})


def user_login(request):
    """User login."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name() or username}!')
                return redirect('dashboard')
        messages.error(request, 'Invalid username or password.')
    else:
        form = UserLoginForm()
    return render(request, 'auth/login.html', {'form': form})


def user_logout(request):
    """User logout."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')


@login_required
def dashboard(request):
    """Main dashboard view."""
    user = request.user
    today = timezone.now().date()
    current_month = today.month
    current_year = today.year

    # Get user's accounts
    accounts = Account.objects.filter(user=user, is_active=True)
    total_balance = accounts.aggregate(Sum('balance'))['balance__sum'] or Decimal('0')

    # Get current month transactions
    month_start = datetime(current_year, current_month, 1).date()
    if current_month == 12:
        month_end = datetime(current_year + 1, 1, 1).date() - timedelta(days=1)
    else:
        month_end = datetime(current_year, current_month + 1, 1).date() - timedelta(days=1)

    month_expenses = Transaction.objects.filter(
        user=user,
        transaction_type='expense',
        date__gte=month_start,
        date__lte=month_end
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')

    month_income = Transaction.objects.filter(
        user=user,
        transaction_type='income',
        date__gte=month_start,
        date__lte=month_end
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')

    savings_rate = 0
    if month_income > 0:
        savings_rate = ((month_income - month_expenses) / month_income) * 100

    # Recent transactions
    recent_transactions = Transaction.objects.filter(user=user).order_by('-date', '-created_at')[:10]

    # Upcoming subscriptions
    upcoming_subscriptions = Subscription.objects.filter(
        user=user,
        is_active=True,
        next_payment__gte=today
    ).order_by('next_payment')[:5]

    # Budget overview
    budgets = Budget.objects.filter(user=user, month=current_month, year=current_year)
    budget_data = []
    for budget in budgets:
        spent = Transaction.objects.filter(
            user=user,
            category=budget.category,
            transaction_type='expense',
            date__gte=month_start,
            date__lte=month_end
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        percentage = (spent / budget.amount * 100) if budget.amount > 0 else 0
        budget_data.append({
            'category': budget.category,
            'budget': budget.amount,
            'spent': spent,
            'percentage': min(percentage, 100)
        })

    # Category breakdown for pie chart
    category_expenses_raw = list(Transaction.objects.filter(
        user=user,
        transaction_type='expense',
        date__gte=month_start,
        date__lte=month_end
    ).values('category__name', 'category__color').annotate(total=Sum('amount')).order_by('-total'))

    category_expenses = [
        {'category__name': item['category__name'], 'category__color': item['category__color'], 'total': float(item['total'])}
        for item in category_expenses_raw
    ]

    # ── Smart Engine data ──────────────────────────────────────────────────────
    # Last month expenses (for trend)
    lm = current_month - 1 if current_month > 1 else 12
    ly = current_year if current_month > 1 else current_year - 1
    lm_start = datetime(ly, lm, 1).date()
    lm_end = (datetime(ly, lm + 1, 1).date() - timedelta(days=1)) if lm < 12 else datetime(ly + 1, 1, 1).date() - timedelta(days=1)
    last_month_expense = Transaction.objects.filter(
        user=user, transaction_type='expense', date__gte=lm_start, date__lte=lm_end
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')

    tx_count_30 = Transaction.objects.filter(
        user=user, date__gte=today - timedelta(days=30)
    ).count()

    spending_forecast = _compute_forecast(today, month_start, month_end, month_expenses)
    health_score = _compute_health_score(month_income, month_expenses, budget_data, last_month_expense, tx_count_30)
    smart_insights = _compute_insights(
        month_income, month_expenses, budget_data, category_expenses,
        upcoming_subscriptions, spending_forecast, today
    )
    # ──────────────────────────────────────────────────────────────────────────

    # Monthly trend (last 6 months)
    monthly_data = []
    for i in range(5, -1, -1):
        m = current_month - i
        y = current_year
        while m <= 0:
            m += 12
            y -= 1
        m_start = datetime(y, m, 1).date()
        if m == 12:
            m_end = datetime(y + 1, 1, 1).date() - timedelta(days=1)
        else:
            m_end = datetime(y, m + 1, 1).date() - timedelta(days=1)

        income = Transaction.objects.filter(
            user=user,
            transaction_type='income',
            date__gte=m_start,
            date__lte=m_end
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        expense = Transaction.objects.filter(
            user=user,
            transaction_type='expense',
            date__gte=m_start,
            date__lte=m_end
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')

        monthly_data.append({
            'month': m_start.strftime('%b %Y'),
            'income': float(income),
            'expense': float(expense)
        })

    context = {
        'total_balance': total_balance,
        'month_expenses': month_expenses,
        'month_income': month_income,
        'savings_rate': savings_rate,
        'recent_transactions': recent_transactions,
        'upcoming_subscriptions': upcoming_subscriptions,
        'budget_data': budget_data,
        'category_expenses': category_expenses,
        'monthly_data': monthly_data,
        'accounts': accounts,
        'quick_form': QuickTransactionForm(),
        # Smart Engine
        'health_score': health_score,
        'smart_insights': smart_insights,
        'spending_forecast': spending_forecast,
    }
    
    return render(request, 'dashboard.html', context)


@login_required
def expense_list(request):
    """List all expenses with advanced search."""
    user = request.user
    expenses = Transaction.objects.filter(user=user, transaction_type='expense')

    # Advanced search filters
    search_form = AdvancedSearchForm(user=user, data=request.GET or None)
    
    if search_form.is_valid():
        # Description search
        description = search_form.cleaned_data.get('description')
        if description:
            expenses = expenses.filter(description__icontains=description)
        
        # Amount range
        min_amount = search_form.cleaned_data.get('min_amount')
        max_amount = search_form.cleaned_data.get('max_amount')
        if min_amount:
            expenses = expenses.filter(amount__gte=min_amount)
        if max_amount:
            expenses = expenses.filter(amount__lte=max_amount)
        
        # Date range
        start_date = search_form.cleaned_data.get('start_date')
        end_date = search_form.cleaned_data.get('end_date')
        if start_date:
            expenses = expenses.filter(date__gte=start_date)
        if end_date:
            expenses = expenses.filter(date__lte=end_date)
        
        # Category filter (multiple)
        categories = search_form.cleaned_data.get('category')
        if categories:
            expenses = expenses.filter(category__in=categories)
        
        # Account filter (multiple)
        accounts = search_form.cleaned_data.get('account')
        if accounts:
            expenses = expenses.filter(account__in=accounts)
        
        # Tags search
        tags = search_form.cleaned_data.get('tags')
        if tags:
            expenses = expenses.filter(tags__icontains=tags)
    
    expenses = expenses.order_by('-date', '-created_at')

    # Get all categories for filter form
    all_categories = Category.objects.filter(is_active=True, category_type__in=['expense', 'both'])

    context = {
        'transactions': expenses,
        'categories': all_categories,
        'search_form': search_form,
        'has_filters': any(search_form.cleaned_data.values()) if search_form.is_valid() else False,
    }
    return render(request, 'expenses/expense_list.html', context)


@login_required
def expense_add(request):
    """Add new expense."""
    if request.method == 'POST':
        form = TransactionForm(request.user, request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            messages.success(request, f'Expense of ₹{expense.amount} added successfully!')
            return redirect('expense_list')
    else:
        form = TransactionForm(request.user, initial={'transaction_type': 'expense'})
    return render(request, 'expenses/expense_form.html', {'form': form, 'title': 'Add Expense'})


@login_required
def expense_edit(request, pk):
    """Edit expense."""
    expense = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == 'POST':
        form = TransactionForm(request.user, request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense updated successfully!')
            return redirect('expense_list')
    else:
        form = TransactionForm(request.user, instance=expense)
    return render(request, 'expenses/expense_form.html', {'form': form, 'title': 'Edit Expense'})


@login_required
def expense_delete(request, pk):
    """Delete expense."""
    expense = get_object_or_404(Transaction, pk=pk, user=request.user)
    if expense.account:
        expense.account.balance += expense.amount
        expense.account.save()
    expense.delete()
    messages.success(request, 'Expense deleted successfully!')
    return redirect('expense_list')


@login_required
def bulk_transaction_action(request):
    """Handle bulk actions on transactions."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
    
    transaction_ids = request.POST.getlist('transaction_ids[]')
    action = request.POST.get('action')
    
    if not transaction_ids or not action:
        return JsonResponse({'success': False, 'error': 'Missing required parameters'}, status=400)
    
    # Get transactions belonging to user
    transactions = Transaction.objects.filter(pk__in=transaction_ids, user=request.user)
    
    if not transactions.exists():
        return JsonResponse({'success': False, 'error': 'No valid transactions found'}, status=404)
    
    count = 0
    
    try:
        if action == 'delete':
            # Delete transactions and update account balances
            for tx in transactions:
                if tx.account:
                    if tx.transaction_type == 'expense':
                        tx.account.balance += tx.amount
                    else:
                        tx.account.balance -= tx.amount
                    tx.account.save()
                tx.delete()
                count += 1
            messages.success(request, f'{count} transaction(s) deleted successfully!')
        
        elif action == 'update_category':
            category_id = request.POST.get('category_id')
            if not category_id:
                return JsonResponse({'success': False, 'error': 'Category ID required'}, status=400)
            
            category = get_object_or_404(Category, pk=category_id, is_active=True)
            transactions.update(category=category)
            count = transactions.count()
            messages.success(request, f'{count} transaction(s) updated with new category!')
        
        elif action == 'update_account':
            account_id = request.POST.get('account_id')
            if not account_id:
                return JsonResponse({'success': False, 'error': 'Account ID required'}, status=400)
            
            account = get_object_or_404(Account, pk=account_id, user=request.user, is_active=True)
            
            # Update account balances for old and new accounts
            for tx in transactions:
                if tx.account and tx.account != account:
                    # Reverse old account balance
                    if tx.transaction_type == 'expense':
                        tx.account.balance += tx.amount
                    else:
                        tx.account.balance -= tx.amount
                    tx.account.save()
                
                # Apply to new account
                if tx.transaction_type == 'expense':
                    account.balance -= tx.amount
                else:
                    account.balance += tx.amount
            
            account.save()
            transactions.update(account=account)
            count = transactions.count()
            messages.success(request, f'{count} transaction(s) moved to new account!')
        
        elif action == 'add_tags':
            tags = request.POST.get('tags', '')
            if not tags:
                return JsonResponse({'success': False, 'error': 'Tags required'}, status=400)
            
            for tx in transactions:
                existing_tags = tx.tags.split(',') if tx.tags else []
                new_tags = tags.split(',')
                combined_tags = list(set(existing_tags + new_tags))
                tx.tags = ','.join(filter(None, combined_tags))
                tx.save()
                count += 1
            messages.success(request, f'{count} transaction(s) updated with new tags!')
        
        else:
            return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)
        
        return JsonResponse({'success': True, 'count': count})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def income_list(request):
    """List all income with advanced search."""
    user = request.user
    income_list = Transaction.objects.filter(user=user, transaction_type='income')

    # Advanced search filters
    search_form = AdvancedSearchForm(user=user, data=request.GET or None)
    
    if search_form.is_valid():
        # Description search
        description = search_form.cleaned_data.get('description')
        if description:
            income_list = income_list.filter(description__icontains=description)
        
        # Amount range
        min_amount = search_form.cleaned_data.get('min_amount')
        max_amount = search_form.cleaned_data.get('max_amount')
        if min_amount:
            income_list = income_list.filter(amount__gte=min_amount)
        if max_amount:
            income_list = income_list.filter(amount__lte=max_amount)
        
        # Date range
        start_date = search_form.cleaned_data.get('start_date')
        end_date = search_form.cleaned_data.get('end_date')
        if start_date:
            income_list = income_list.filter(date__gte=start_date)
        if end_date:
            income_list = income_list.filter(date__lte=end_date)
        
        # Category filter (multiple)
        categories = search_form.cleaned_data.get('category')
        if categories:
            income_list = income_list.filter(category__in=categories)
        
        # Account filter (multiple)
        accounts = search_form.cleaned_data.get('account')
        if accounts:
            income_list = income_list.filter(account__in=accounts)
        
        # Tags search
        tags = search_form.cleaned_data.get('tags')
        if tags:
            income_list = income_list.filter(tags__icontains=tags)
    
    income_list = income_list.order_by('-date', '-created_at')

    # Get all categories for filter form
    all_categories = Category.objects.filter(is_active=True, category_type__in=['income', 'both'])

    context = {
        'transactions': income_list,
        'categories': all_categories,
        'search_form': search_form,
        'has_filters': any(search_form.cleaned_data.values()) if search_form.is_valid() else False,
    }
    return render(request, 'expenses/income_list.html', context)


@login_required
def income_add(request):
    """Add new income."""
    if request.method == 'POST':
        form = TransactionForm(request.user, request.POST)
        if form.is_valid():
            income = form.save(commit=False)
            income.user = request.user
            income.save()
            messages.success(request, f'Income of ₹{income.amount} added successfully!')
            return redirect('income_list')
    else:
        form = TransactionForm(request.user, initial={'transaction_type': 'income'})
    return render(request, 'expenses/expense_form.html', {'form': form, 'title': 'Add Income'})


@login_required
def income_edit(request, pk):
    """Edit income."""
    income = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == 'POST':
        form = TransactionForm(request.user, request.POST, instance=income)
        if form.is_valid():
            form.save()
            messages.success(request, 'Income updated successfully!')
            return redirect('income_list')
    else:
        form = TransactionForm(request.user, instance=income)
    return render(request, 'expenses/expense_form.html', {'form': form, 'title': 'Edit Income'})


@login_required
def income_delete(request, pk):
    """Delete income."""
    income = get_object_or_404(Transaction, pk=pk, user=request.user)
    if income.account:
        income.account.balance -= income.amount
        income.account.save()
    income.delete()
    messages.success(request, 'Income deleted successfully!')
    return redirect('income_list')


# ─── Transaction Templates ─────────────────────────────────────────────────────

@login_required
def template_list(request):
    """List all transaction templates."""
    templates = TransactionTemplate.objects.filter(user=request.user)
    return render(request, 'transactions/template_list.html', {'templates': templates})


@login_required
def template_add(request):
    """Add a new transaction template."""
    if request.method == 'POST':
        form = TransactionTemplateForm(request.user, request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.user = request.user
            template.save()
            messages.success(request, 'Template created successfully!')
            return redirect('template_list')
    else:
        form = TransactionTemplateForm(request.user)
    return render(request, 'transactions/template_form.html', {'form': form, 'title': 'Add Template'})


@login_required
def template_edit(request, pk):
    """Edit a transaction template."""
    template = get_object_or_404(TransactionTemplate, pk=pk, user=request.user)
    if request.method == 'POST':
        form = TransactionTemplateForm(request.user, request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, 'Template updated successfully!')
            return redirect('template_list')
    else:
        form = TransactionTemplateForm(request.user, instance=template)
    return render(request, 'transactions/template_form.html', {'form': form, 'title': 'Edit Template'})


@login_required
def template_delete(request, pk):
    """Delete a transaction template."""
    template = get_object_or_404(TransactionTemplate, pk=pk, user=request.user)
    template.delete()
    messages.success(request, 'Template deleted successfully!')
    return redirect('template_list')


@login_required
def use_template(request, pk):
    """Use a template to create a transaction."""
    template = get_object_or_404(TransactionTemplate, pk=pk, user=request.user)
    
    # Create transaction from template
    transaction = Transaction(
        user=request.user,
        account=template.account,
        category=template.category,
        transaction_type=template.transaction_type,
        amount=template.amount,
        description=template.description,
        tags=template.tags,
        date=timezone.now().date()
    )
    transaction.save()
    
    # Update template usage count
    template.use_template()
    
    messages.success(request, f'Transaction created from "{template.name}"!')
    return redirect('expense_list' if template.transaction_type == 'expense' else 'income_list')


# ─── Spending Heatmap ─────────────────────────────────────────────────────

@login_required
def spending_heatmap(request):
    """Spending heatmap visualization."""
    user = request.user
    today = timezone.now().date()
    
    # Get date range from query params (default to last 90 days)
    days_back = int(request.GET.get('days', 90))
    start_date = today - timedelta(days=days_back)
    
    # Get daily spending data
    daily_spending = Transaction.objects.filter(
        user=user,
        transaction_type='expense',
        date__gte=start_date,
        date__lte=today
    ).values('date').annotate(
        daily_total=Sum('amount')
    ).order_by('date')
    
    # Calculate max spending for color intensity
    max_spending = 0
    for item in daily_spending:
        if item['daily_total']:
            max_spending = max(max_spending, float(item['daily_total']))
    
    # Prepare heatmap data
    heatmap_data = []
    current_date = start_date
    while current_date <= today:
        day_data = next((d for d in daily_spending if d['date'] == current_date), None)
        amount = float(day_data['daily_total']) if day_data and day_data['daily_total'] else 0
        
        # Calculate intensity (0-100)
        intensity = int((amount / max_spending * 100)) if max_spending > 0 else 0
        intensity = min(intensity, 100)
        
        heatmap_data.append({
            'date': current_date,
            'amount': amount,
            'intensity': intensity,
            'day_name': current_date.strftime('%a'),
            'day_num': current_date.day
        })
        
        current_date += timedelta(days=1)
    
    # Calculate statistics
    total_spending = sum(d['amount'] for d in heatmap_data)
    avg_spending = total_spending / len(heatmap_data) if heatmap_data else 0
    max_day = max(heatmap_data, key=lambda x: x['amount']) if heatmap_data else None
    
    context = {
        'heatmap_data': heatmap_data,
        'total_spending': total_spending,
        'avg_spending': avg_spending,
        'max_day': max_day,
        'days_back': days_back,
        'start_date': start_date,
        'end_date': today,
    }
    return render(request, 'analytics/spending_heatmap.html', context)


@login_required
def top_spending_analysis(request):
    """Top spending analysis view."""
    user = request.user
    today = timezone.now().date()
    
    # Get date range from query params (default to current month)
    days_back = int(request.GET.get('days', 30))
    start_date = today - timedelta(days=days_back)
    
    # Top 5 categories by spending
    top_categories = Transaction.objects.filter(
        user=user,
        transaction_type='expense',
        date__gte=start_date,
        date__lte=today
    ).values('category__name', 'category__color', 'category__icon').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')[:5]
    
    # Top 5 merchants (from description)
    top_merchants = Transaction.objects.filter(
        user=user,
        transaction_type='expense',
        date__gte=start_date,
        date__lte=today
    ).values('description').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')[:5]
    
    # Top 5 days of week by spending
    day_of_week_spending = Transaction.objects.filter(
        user=user,
        transaction_type='expense',
        date__gte=start_date,
        date__lte=today
    ).annotate(day_of_week=TruncDay('date')).values('day_of_week').annotate(
        total=Sum('amount')
    ).order_by('-total')[:7]
    
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    context = {
        'top_categories': top_categories,
        'top_merchants': top_merchants,
        'day_of_week_spending': day_of_week_spending,
        'day_names': day_names,
        'days_back': days_back,
        'start_date': start_date,
        'end_date': today,
    }
    return render(request, 'analytics/top_spending.html', context)


@login_required
def income_vs_expense_trends(request):
    """Income vs Expense Trends view showing the gap between income and expenses over time."""
    user = request.user
    today = timezone.now().date()
    
    # Get period from query params (default to 6 months)
    period = request.GET.get('period', '6m')
    
    if period == '1m':
        months = 1
    elif period == '3m':
        months = 3
    elif period == '12m':
        months = 12
    else:
        months = 6
    
    # Calculate start date
    start_date = today - relativedelta(months=months)
    
    # Get monthly income and expense data
    monthly_data = []
    current_date = start_date
    
    while current_date <= today:
        # Get first and last day of the month
        month_start = current_date.replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)
        
        # Calculate totals for the month
        month_income = Transaction.objects.filter(
            user=user,
            transaction_type='income',
            date__gte=month_start,
            date__lte=month_end
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        month_expense = Transaction.objects.filter(
            user=user,
            transaction_type='expense',
            date__gte=month_start,
            date__lte=month_end
        ).aggregate(total=Sum('amount'))['total']
        
        month_income = float(month_income) if month_income is not None else 0
        month_expense = float(month_expense) if month_expense is not None else 0
        
        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'income': month_income,
            'expense': month_expense,
            'net': month_income - month_expense,
            'savings_rate': round((month_income - month_expense) / month_income * 100, 1) if month_income > 0 else 0
        })
        
        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1, day=1)
    
    # Calculate totals and averages
    total_income = sum(d['income'] for d in monthly_data)
    total_expense = sum(d['expense'] for d in monthly_data)
    total_net = total_income - total_expense
    avg_monthly_income = total_income / len(monthly_data) if monthly_data else 0
    avg_monthly_expense = total_expense / len(monthly_data) if monthly_data else 0
    avg_savings_rate = sum(d['savings_rate'] for d in monthly_data) / len(monthly_data) if monthly_data else 0
    
    # Find best and worst months
    best_month = max(monthly_data, key=lambda x: x['net']) if monthly_data else None
    worst_month = min(monthly_data, key=lambda x: x['net']) if monthly_data else None
    
    context = {
        'monthly_data': monthly_data,
        'total_income': total_income,
        'total_expense': total_expense,
        'total_net': total_net,
        'avg_monthly_income': avg_monthly_income,
        'avg_monthly_expense': avg_monthly_expense,
        'avg_savings_rate': avg_savings_rate,
        'best_month': best_month,
        'worst_month': worst_month,
        'period': period,
        'start_date': start_date,
        'end_date': today,
    }
    return render(request, 'analytics/income_vs_expense_trends.html', context)


@login_required
def net_worth_dashboard(request):
    """Net Worth Dashboard showing total net worth over time."""
    user = request.user
    today = timezone.now().date()
    
    # Get period from query params (default to 12 months)
    period = request.GET.get('period', '12m')
    
    if period == '3m':
        months = 3
    elif period == '6m':
        months = 6
    elif period == '24m':
        months = 24
    else:
        months = 12
    
    # Calculate start date
    start_date = today - relativedelta(months=months)
    
    # Get all accounts for the user
    accounts = Account.objects.filter(user=user)
    
    # Calculate current net worth
    current_assets = sum(account.get_available_balance() for account in accounts if account.account_type in ['checking', 'savings', 'cash'])
    current_investments = sum(account.get_available_balance() for account in accounts if account.account_type == 'investment')
    current_liabilities = sum(abs(account.get_available_balance()) for account in accounts if account.account_type in ['credit_card', 'loan'])
    current_net_worth = current_assets + current_investments - current_liabilities
    
    # Get monthly net worth data
    monthly_net_worth = []
    current_date = start_date
    
    while current_date <= today:
        # Get first and last day of the month
        month_start = current_date.replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)
        
        # Calculate net worth at the end of the month
        # For simplicity, we'll use current balances and adjust by transactions
        month_assets = sum(account.get_available_balance() for account in accounts if account.account_type in ['checking', 'savings', 'cash'])
        month_investments = sum(account.get_available_balance() for account in accounts if account.account_type == 'investment')
        month_liabilities = sum(abs(account.get_available_balance()) for account in accounts if account.account_type in ['credit_card', 'loan'])
        month_net_worth = month_assets + month_investments - month_liabilities
        
        monthly_net_worth.append({
            'month': month_start.strftime('%b %Y'),
            'assets': float(month_assets),
            'investments': float(month_investments),
            'liabilities': float(month_liabilities),
            'net_worth': float(month_net_worth)
        })
        
        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1, day=1)
    
    # Calculate growth
    if len(monthly_net_worth) > 1:
        start_net_worth = monthly_net_worth[0]['net_worth']
        end_net_worth = monthly_net_worth[-1]['net_worth']
        net_worth_change = end_net_worth - start_net_worth
        net_worth_change_percent = (net_worth_change / start_net_worth * 100) if start_net_worth != 0 else 0
    else:
        net_worth_change = 0
        net_worth_change_percent = 0
    
    # Account breakdown
    account_breakdown = []
    for account in accounts:
        balance = account.get_available_balance()
        if account.account_type in ['credit_card', 'loan']:
            balance = abs(balance)
        
        account_breakdown.append({
            'name': account.name,
            'type': account.account_type,
            'balance': float(balance),
            'icon': account.icon or 'bi-wallet2',
            'color': account.color or '#6B7280'
        })
    
    context = {
        'current_assets': current_assets,
        'current_investments': current_investments,
        'current_liabilities': current_liabilities,
        'current_net_worth': current_net_worth,
        'monthly_net_worth': monthly_net_worth,
        'net_worth_change': net_worth_change,
        'net_worth_change_percent': net_worth_change_percent,
        'account_breakdown': account_breakdown,
        'period': period,
        'start_date': start_date,
        'end_date': today,
    }
    return render(request, 'analytics/net_worth_dashboard.html', context)


@login_required
def recurring_transaction_list(request):
    """List all recurring transactions."""
    user = request.user
    recurring_transactions = RecurringTransaction.objects.filter(user=user)
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        recurring_transactions = recurring_transactions.filter(status=status_filter)
    
    # Calculate upcoming due dates
    today = timezone.now().date()
    for rt in recurring_transactions:
        rt.days_until_due = (rt.next_due_date - today).days if rt.next_due_date else None
        rt.is_overdue = rt.next_due_date < today if rt.next_due_date else False
    
    context = {
        'recurring_transactions': recurring_transactions,
        'status_filter': status_filter,
    }
    return render(request, 'recurring_transactions/recurring_transaction_list.html', context)


@login_required
def recurring_transaction_add(request):
    """Add a new recurring transaction."""
    if request.method == 'POST':
        form = RecurringTransactionForm(request.user, request.POST)
        if form.is_valid():
            recurring_transaction = form.save(commit=False)
            recurring_transaction.user = request.user
            recurring_transaction.save()
            messages.success(request, f'Recurring transaction "{recurring_transaction.name}" has been created.')
            return redirect('recurring_transaction_list')
    else:
        form = RecurringTransactionForm(request.user)
    
    context = {'form': form, 'title': 'Add Recurring Transaction'}
    return render(request, 'recurring_transactions/recurring_transaction_form.html', context)


@login_required
def recurring_transaction_edit(request, pk):
    """Edit an existing recurring transaction."""
    recurring_transaction = get_object_or_404(RecurringTransaction, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = RecurringTransactionForm(request.user, request.POST, instance=recurring_transaction)
        if form.is_valid():
            form.save()
            messages.success(request, f'Recurring transaction "{recurring_transaction.name}" has been updated.')
            return redirect('recurring_transaction_list')
    else:
        form = RecurringTransactionForm(request.user, instance=recurring_transaction)
    
    context = {'form': form, 'title': 'Edit Recurring Transaction', 'recurring_transaction': recurring_transaction}
    return render(request, 'recurring_transactions/recurring_transaction_form.html', context)


@login_required
def recurring_transaction_delete(request, pk):
    """Delete a recurring transaction."""
    recurring_transaction = get_object_or_404(RecurringTransaction, pk=pk, user=request.user)
    
    if request.method == 'POST':
        name = recurring_transaction.name
        recurring_transaction.delete()
        messages.success(request, f'Recurring transaction "{name}" has been deleted.')
        return redirect('recurring_transaction_list')
    
    context = {'recurring_transaction': recurring_transaction}
    return render(request, 'recurring_transactions/recurring_transaction_confirm_delete.html', context)


@login_required
def recurring_transaction_process(request, pk):
    """Manually process a recurring transaction."""
    recurring_transaction = get_object_or_404(RecurringTransaction, pk=pk, user=request.user)
    
    if recurring_transaction.status != 'active':
        messages.warning(request, 'Only active recurring transactions can be processed.')
        return redirect('recurring_transaction_list')
    
    try:
        transaction = recurring_transaction.process_transaction()
        messages.success(request, f'Transaction "{transaction.description}" of ₹{transaction.amount} has been created.')
    except Exception as e:
        messages.error(request, f'Error processing transaction: {str(e)}')
    
    return redirect('recurring_transaction_list')


@login_required
def recurring_transaction_pause(request, pk):
    """Pause a recurring transaction."""
    recurring_transaction = get_object_or_404(RecurringTransaction, pk=pk, user=request.user)
    recurring_transaction.status = 'paused'
    recurring_transaction.save()
    messages.success(request, f'Recurring transaction "{recurring_transaction.name}" has been paused.')
    return redirect('recurring_transaction_list')


@login_required
def recurring_transaction_resume(request, pk):
    """Resume a paused recurring transaction."""
    recurring_transaction = get_object_or_404(RecurringTransaction, pk=pk, user=request.user)
    recurring_transaction.status = 'active'
    recurring_transaction.save()
    messages.success(request, f'Recurring transaction "{recurring_transaction.name}" has been resumed.')
    return redirect('recurring_transaction_list')


@login_required
def account_list(request):
    """List all accounts."""
    accounts = Account.objects.filter(user=request.user)
    return render(request, 'accounts/account_list.html', {'accounts': accounts})


@login_required
def account_add(request):
    """Add new account."""
    if request.method == 'POST':
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.user = request.user
            account.save()
            messages.success(request, f'Account "{account.name}" created successfully!')
            return redirect('account_list')
    else:
        form = AccountForm(initial={'currency': request.user.currency})
    return render(request, 'accounts/account_form.html', {'form': form, 'title': 'Add Account'})


@login_required
def account_edit(request, pk):
    """Edit account."""
    account = get_object_or_404(Account, pk=pk, user=request.user)
    if request.method == 'POST':
        form = AccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, f'Account "{account.name}" updated successfully!')
            return redirect('account_list')
    else:
        form = AccountForm(instance=account)
    return render(request, 'accounts/account_form.html', {'form': form, 'title': 'Edit Account'})


@login_required
def account_delete(request, pk):
    """Delete account."""
    account = get_object_or_404(Account, pk=pk, user=request.user)
    account.delete()
    messages.success(request, 'Account deleted successfully!')
    return redirect('account_list')


@login_required
def subscription_list(request):
    """List all subscriptions."""
    subscriptions = Subscription.objects.filter(user=request.user)

    # Calculate totals
    monthly_total = sum([sub.get_monthly_amount() for sub in subscriptions.filter(is_active=True)])
    yearly_total = monthly_total * 12

    context = {
        'subscriptions': subscriptions,
        'monthly_total': monthly_total,
        'yearly_total': yearly_total,
    }
    return render(request, 'subscriptions/subscription_list.html', context)


@login_required
def subscription_add(request):
    """Add new subscription."""
    if request.method == 'POST':
        form = SubscriptionForm(request.user, request.POST)
        if form.is_valid():
            subscription = form.save(commit=False)
            subscription.user = request.user
            subscription.save()
            messages.success(request, f'Subscription "{subscription.name}" added!')
            return redirect('subscription_list')
    else:
        form = SubscriptionForm(request.user)
    return render(request, 'subscriptions/subscription_form.html', {'form': form, 'title': 'Add Subscription'})


@login_required
def subscription_edit(request, pk):
    """Edit subscription."""
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    if request.method == 'POST':
        form = SubscriptionForm(request.user, request.POST, instance=subscription)
        if form.is_valid():
            form.save()
            messages.success(request, 'Subscription updated!')
            return redirect('subscription_list')
    else:
        form = SubscriptionForm(request.user, instance=subscription)
    return render(request, 'subscriptions/subscription_form.html', {'form': form, 'title': 'Edit Subscription'})


@login_required
def subscription_delete(request, pk):
    """Delete subscription."""
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    subscription.delete()
    messages.success(request, 'Subscription deleted!')
    return redirect('subscription_list')


@login_required
def budget_list(request):
    """List budgets."""
    user = request.user
    today = timezone.now().date()

    # Get or set default month/year
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))

    budgets = Budget.objects.filter(user=user, month=month, year=year)
    categories = Category.objects.filter(is_active=True, category_type__in=['expense', 'both'])

    month_start = datetime(year, month, 1).date()
    if month == 12:
        month_end = datetime(year + 1, 1, 1).date() - timedelta(days=1)
    else:
        month_end = datetime(year, month + 1, 1).date() - timedelta(days=1)

    budget_data = []
    for budget in budgets:
        spent = Transaction.objects.filter(
            user=user,
            category=budget.category,
            transaction_type='expense',
            date__gte=month_start,
            date__lte=month_end
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        percentage = (spent / budget.amount * 100) if budget.amount > 0 else 0
        budget_data.append({
            'budget': budget,
            'spent': spent,
            'remaining': budget.amount - spent,
            'percentage': min(percentage, 100),
            'is_over': spent > budget.amount
        })

    total_budget = sum([b['budget'].amount for b in budget_data])
    total_spent = sum([b['spent'] for b in budget_data])

    context = {
        'budget_data': budget_data,
        'categories': categories,
        'total_budget': total_budget,
        'total_spent': total_spent,
        'month': month,
        'year': year,
    }
    return render(request, 'budgets/budget_list.html', context)


@login_required
def budget_add(request):
    """Add budget."""
    user = request.user
    today = timezone.now().date()

    if request.method == 'POST':
        form = BudgetForm(request.POST)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.user = user
            budget.month = int(request.POST.get('month', today.month))
            budget.year = int(request.POST.get('year', today.year))
            budget.save()
            messages.success(request, 'Budget added!')
            return redirect('budget_list')
    else:
        form = BudgetForm()
        form.fields['category'].queryset = Category.objects.filter(
            is_active=True,
            category_type__in=['expense', 'both']
        ).exclude(
            id__in=Budget.objects.filter(user=user, month=today.month, year=today.year).values_list('category_id', flat=True)
        )

    return render(request, 'budgets/budget_form.html', {
        'form': form,
        'title': 'Add Budget',
        'month': today.month,
        'year': today.year
    })


@login_required
def budget_edit(request, pk):
    """Edit budget."""
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    if request.method == 'POST':
        form = BudgetForm(request.POST, instance=budget)
        if form.is_valid():
            form.save()
            messages.success(request, 'Budget updated!')
            return redirect('budget_list')
    else:
        form = BudgetForm(instance=budget)
    return render(request, 'budgets/budget_form.html', {'form': form, 'title': 'Edit Budget'})


@login_required
def budget_delete(request, pk):
    """Delete budget."""
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    budget.delete()
    messages.success(request, 'Budget deleted!')
    return redirect('budget_list')


@login_required
def savings_goal_list(request):
    """List savings goals."""
    goals = SavingsGoal.objects.filter(user=request.user)
    return render(request, 'savings_goal_list.html', {'goals': goals})


@login_required
def savings_goal_add(request):
    """Add savings goal."""
    if request.method == 'POST':
        form = SavingsGoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            messages.success(request, f'Savings goal "{goal.name}" created!')
            return redirect('savings_goal_list')
    else:
        form = SavingsGoalForm()
    return render(request, 'savings_goal_form.html', {'form': form, 'title': 'Add Savings Goal'})


@login_required
def savings_goal_edit(request, pk):
    """Edit savings goal."""
    goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)
    if request.method == 'POST':
        form = SavingsGoalForm(request.POST, instance=goal)
        if form.is_valid():
            form.save()
            messages.success(request, 'Savings goal updated!')
            return redirect('savings_goal_list')
    else:
        form = SavingsGoalForm(instance=goal)
    return render(request, 'savings_goal_form.html', {'form': form, 'title': 'Edit Savings Goal'})


@login_required
def savings_goal_delete(request, pk):
    """Delete savings goal."""
    goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)
    goal.delete()
    messages.success(request, 'Savings goal deleted!')
    return redirect('savings_goal_list')


@login_required
def reports(request):
    """Reports and analytics."""
    user = request.user
    today = timezone.now().date()

    # Default to current month
    start_date = request.GET.get('start_date', datetime(today.year, today.month, 1).date())
    end_date = request.GET.get('end_date', today)

    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    # Expense breakdown by category
    expense_by_category = list(Transaction.objects.filter(
        user=user,
        transaction_type='expense',
        date__gte=start_date,
        date__lte=end_date
    ).values('category__name', 'category__color', 'category__icon').annotate(
        total=Sum('amount')
    ).order_by('-total'))

    # Convert Decimal to float
    for item in expense_by_category:
        item['total'] = float(item['total']) if item['total'] else 0

    # Income breakdown by category
    income_by_category = list(Transaction.objects.filter(
        user=user,
        transaction_type='income',
        date__gte=start_date,
        date__lte=end_date
    ).values('category__name', 'category__color', 'category__icon').annotate(
        total=Sum('amount')
    ).order_by('-total'))

    # Convert Decimal to float
    for item in income_by_category:
        item['total'] = float(item['total']) if item['total'] else 0

    # Monthly summary
    total_expense = Transaction.objects.filter(
        user=user,
        transaction_type='expense',
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')

    total_income = Transaction.objects.filter(
        user=user,
        transaction_type='income',
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')

    # Daily transactions
    daily_transactions = list(Transaction.objects.filter(
        user=user,
        date__gte=start_date,
        date__lte=end_date
    ).annotate(day=TruncDay('date')).values('day').annotate(
        income=Sum('amount', filter=Q(transaction_type='income')),
        expense=Sum('amount', filter=Q(transaction_type='expense'))
    ).order_by('day'))

    # Convert Decimal to float and datetime to string
    for item in daily_transactions:
        item['income'] = float(item['income']) if item['income'] else 0
        item['expense'] = float(item['expense']) if item['expense'] else 0
        if item.get('day'):
            item['day'] = item['day'].strftime('%Y-%m-%d')

    context = {
        'expense_by_category': list(expense_by_category),
        'income_by_category': list(income_by_category),
        'total_expense': total_expense,
        'total_income': total_income,
        'net_savings': total_income - total_expense,
        'daily_transactions': list(daily_transactions),
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
    }
    return render(request, 'reports/reports.html', context)


@login_required
def export_csv(request):
    """Export transactions to CSV."""
    user = request.user
    transactions = Transaction.objects.filter(user=user).order_by('-date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="smart_expense_transactions.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Type', 'Category', 'Amount', 'Account', 'Description', 'Tags'])

    for t in transactions:
        writer.writerow([
            t.date.strftime('%Y-%m-%d'),
            t.transaction_type,
            t.category.name if t.category else '',
            str(t.amount),
            t.account.name if t.account else '',
            t.description,
            t.tags
        ])

    return response


@login_required
def profile(request):
    """User profile view."""
    user = request.user
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=user)

    # Stats
    total_transactions = Transaction.objects.filter(user=user).count()
    total_accounts = Account.objects.filter(user=user).count()
    active_subscriptions = Subscription.objects.filter(user=user, is_active=True).count()

    context = {
        'form': form,
        'total_transactions': total_transactions,
        'total_accounts': total_accounts,
        'active_subscriptions': active_subscriptions,
    }
    return render(request, 'profile.html', context)


@login_required
def settings_view(request):
    """User settings."""
    return render(request, 'settings.html')


@login_required
def change_password(request):
    """Change password view."""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            request.user.set_password(form.cleaned_data['new_password2'])
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password changed successfully!')
            return redirect('settings')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'change_password.html', {'form': form})


@login_required
def delete_account(request):
    """Delete account view."""
    if request.method == 'POST':
        form = DeleteAccountForm(request.user, request.POST)
        if form.is_valid():
            user = request.user
            username = user.username
            # Logout first
            logout(request)
            # Delete user data
            Transaction.objects.filter(user=user).delete()
            Account.objects.filter(user=user).delete()
            Subscription.objects.filter(user=user).delete()
            Budget.objects.filter(user=user).delete()
            SavingsGoal.objects.filter(user=user).delete()
            user.delete()
            messages.success(request, f'Account {username} has been deleted.')
            return redirect('home')
    else:
        form = DeleteAccountForm(request.user)
    
    return render(request, 'delete_account.html', {'form': form})


@login_required
def update_username(request):
    """AJAX update username."""
    if request.method == 'POST':
        new_username = request.POST.get('username', '').strip()
        if new_username and len(new_username) >= 3:
            if User.objects.exclude(pk=request.user.pk).filter(username=new_username).exists():
                return JsonResponse({'error': 'Username already taken'}, status=400)
            request.user.username = new_username
            request.user.save()
            return JsonResponse({'success': True})
        return JsonResponse({'error': 'Username too short'}, status=400)
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def update_email(request):
    """AJAX update email."""
    if request.method == 'POST':
        new_email = request.POST.get('email', '').strip()
        if new_email and '@' in new_email:
            if User.objects.exclude(pk=request.user.pk).filter(email=new_email).exists():
                return JsonResponse({'error': 'Email already registered'}, status=400)
            request.user.email = new_email
            request.user.save()
            return JsonResponse({'success': True})
        return JsonResponse({'error': 'Invalid email'}, status=400)
    return JsonResponse({'error': 'Invalid request'}, status=400)


# API Views
@login_required
def quick_add_expense(request):
    """Quick add expense from dashboard."""
    if request.method == 'POST':
        form = QuickTransactionForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description']
            category = form.cleaned_data.get('category')

            account = Account.objects.filter(user=request.user, is_active=True).first()
            if not account:
                return JsonResponse({'success': False, 'error': 'No account found'}, status=400)

            recent_same = Transaction.objects.filter(
                user=request.user,
                account=account,
                amount=amount,
                description=description,
                transaction_type='expense',
                created_at__gte=timezone.now() - timedelta(seconds=3)
            ).exists()
            
            if recent_same:
                return JsonResponse({'success': False, 'error': 'Duplicate transaction detected'}, status=400)

            transaction = Transaction.objects.create(
                user=request.user,
                account=account,
                category=category,
                transaction_type='expense',
                amount=amount,
                description=description
            )

            return JsonResponse({
                'success': True,
                'message': f'Expense of ₹{amount} added!',
                'transaction_id': transaction.id
            })
        return JsonResponse({'success': False, 'error': 'Invalid form data'}, status=400)
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)


@login_required
def financial_calendar(request):
    """Financial calendar showing subscriptions, salary day, goals and spending."""
    import calendar as cal_module
    user = request.user
    today = timezone.now().date()

    month = int(request.GET.get('month', today.month))
    year  = int(request.GET.get('year',  today.year))

    # Clamp valid values
    month = max(1, min(12, month))

    # Navigation months
    prev_month = 12 if month == 1 else month - 1
    prev_year  = year - 1 if month == 1 else year
    next_month = 1  if month == 12 else month + 1
    next_year  = year + 1 if month == 12 else year

    month_start = datetime(year, month, 1).date()
    month_end   = (datetime(year, next_month, 1).date() - timedelta(days=1)) if month < 12 \
                  else datetime(year + 1, 1, 1).date() - timedelta(days=1)

    month_name = month_start.strftime('%B %Y')

    # ── Gather events per day ──────────────────────────────────────────────────
    events = {}  # {day_num: [event_dicts]}

    # Subscriptions due this month
    for sub in Subscription.objects.filter(
        user=user, is_active=True,
        next_payment__year=year, next_payment__month=month
    ):
        events.setdefault(sub.next_payment.day, []).append({
            'type': 'subscription', 'name': sub.name,
            'amount': float(sub.amount), 'icon': 'bi-repeat',
            'color': '#D97706', 'bg': '#FEF3C7',
        })

    # Salary day
    sd = getattr(user, 'salary_day', None)
    if sd and 1 <= sd <= 28:
        events.setdefault(sd, []).append({
            'type': 'salary', 'name': 'Salary Day', 'amount': None,
            'icon': 'bi-briefcase-fill', 'color': '#16A34A', 'bg': '#DCFCE7',
        })

    # Savings goal deadlines
    for goal in SavingsGoal.objects.filter(
        user=user, status='active',
        deadline__year=year, deadline__month=month
    ):
        events.setdefault(goal.deadline.day, []).append({
            'type': 'goal', 'name': goal.name,
            'amount': float(goal.target_amount - goal.current_amount),
            'icon': 'bi-flag-fill', 'color': '#7C3AED', 'bg': '#F5F3FF',
        })

    # Daily transaction totals and list
    tx_by_day = {}
    tx_list_by_day = {}
    for tx in Transaction.objects.filter(
        user=user, date__gte=month_start, date__lte=month_end
    ).values('date').annotate(
        expense=Sum('amount', filter=Q(transaction_type='expense')),
        income=Sum('amount',  filter=Q(transaction_type='income')),
        count=Count('id')
    ):
        day = tx['date'].day
        tx_by_day[day] = {
            'expense': float(tx['expense'] or 0),
            'income':  float(tx['income']  or 0),
            'count':   tx['count'],
        }
        tx_list_by_day[day] = list(Transaction.objects.filter(
            user=user, date=tx['date']
        ).select_related('category', 'account').order_by('-created_at').values(
            'id', 'amount', 'transaction_type', 'description', 
            'category__name', 'category__color', 'category__icon'
        ))

    # ── Build calendar grid ───────────────────────────────────────────────────
    # calendar.monthcalendar returns weeks; 0 = day outside the month
    calendar_grid = []
    for week in cal_module.monthcalendar(year, month):
        week_days = []
        for day in week:
            if day == 0:
                week_days.append(None)
            else:
                week_days.append({
                    'day':      day,
                    'events':   events.get(day, []),
                    'tx':       tx_by_day.get(day),
                    'tx_list':  tx_list_by_day.get(day, []),
                    'is_today': (day == today.day and month == today.month and year == today.year),
                })
        calendar_grid.append(week_days)

    # Upcoming bills (next 7 days) for sidebar summary
    upcoming_bills = Subscription.objects.filter(
        user=user, is_active=True,
        next_payment__gte=today,
        next_payment__lte=today + timedelta(days=7)
    ).order_by('next_payment')

    context = {
        'month_name':    month_name,
        'month':         month,
        'year':          year,
        'prev_month':    prev_month,
        'prev_year':     prev_year,
        'next_month':    next_month,
        'next_year':     next_year,
        'calendar_grid': calendar_grid,
        'today':         today,
        'upcoming_bills': upcoming_bills,
        'total_events':  sum(len(v) for v in events.values()),
    }
    return render(request, 'calendar/calendar.html', context)


@login_required
def smart_insights_api(request):
    """Return smart insights and health score as JSON for live refresh."""
    user = request.user
    today = timezone.now().date()
    current_month, current_year = today.month, today.year

    month_start = datetime(current_year, current_month, 1).date()
    month_end = (datetime(current_year, current_month + 1, 1).date() - timedelta(days=1)) \
        if current_month < 12 else datetime(current_year + 1, 1, 1).date() - timedelta(days=1)

    month_expenses = Transaction.objects.filter(
        user=user, transaction_type='expense', date__gte=month_start, date__lte=month_end
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')

    month_income = Transaction.objects.filter(
        user=user, transaction_type='income', date__gte=month_start, date__lte=month_end
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')

    budgets = Budget.objects.filter(user=user, month=current_month, year=current_year)
    budget_data = []
    for budget in budgets:
        spent = Transaction.objects.filter(
            user=user, category=budget.category, transaction_type='expense',
            date__gte=month_start, date__lte=month_end
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        pct = (spent / budget.amount * 100) if budget.amount > 0 else 0
        budget_data.append({'category': budget.category, 'budget': budget.amount,
                            'spent': spent, 'remaining': budget.amount - spent,
                            'percentage': min(float(pct), 100)})

    category_expenses = Transaction.objects.filter(
        user=user, transaction_type='expense', date__gte=month_start, date__lte=month_end
    ).values('category__name', 'category__color').annotate(total=Sum('amount')).order_by('-total')

    upcoming_subs = Subscription.objects.filter(
        user=user, is_active=True, next_payment__gte=today
    ).order_by('next_payment')[:5]

    lm = current_month - 1 if current_month > 1 else 12
    ly = current_year if current_month > 1 else current_year - 1
    lm_start = datetime(ly, lm, 1).date()
    lm_end = (datetime(ly, lm + 1, 1).date() - timedelta(days=1)) if lm < 12 else datetime(ly + 1, 1, 1).date() - timedelta(days=1)
    last_month_expense = Transaction.objects.filter(
        user=user, transaction_type='expense', date__gte=lm_start, date__lte=lm_end
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')

    tx_count_30 = Transaction.objects.filter(user=user, date__gte=today - timedelta(days=30)).count()
    forecast = _compute_forecast(today, month_start, month_end, month_expenses)
    health = _compute_health_score(month_income, month_expenses, budget_data, last_month_expense, tx_count_30)
    insights = _compute_insights(month_income, month_expenses, budget_data,
                                 category_expenses, upcoming_subs, forecast, today)

    return JsonResponse({
        'health_score': health,
        'insights': insights,
        'forecast': float(forecast),
        'month_expenses': float(month_expenses),
        'month_income': float(month_income),
    })


@login_required
def get_monthly_data(request):
    """Get monthly data for charts."""
    user = request.user
    months = int(request.GET.get('months', 6))

    today = timezone.now().date()
    data = []

    for i in range(months - 1, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1

        m_start = datetime(y, m, 1).date()
        if m == 12:
            m_end = datetime(y + 1, 1, 1).date() - timedelta(days=1)
        else:
            m_end = datetime(y, m + 1, 1).date() - timedelta(days=1)

        income = Transaction.objects.filter(
            user=user,
            transaction_type='income',
            date__gte=m_start,
            date__lte=m_end
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')

        expense = Transaction.objects.filter(
            user=user,
            transaction_type='expense',
            date__gte=m_start,
            date__lte=m_end
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')

        data.append({
            'month': m_start.strftime('%b %Y'),
            'income': float(income),
            'expense': float(expense),
            'savings': float(income - expense)
        })

    return JsonResponse(data, safe=False)


@login_required
def transaction_history(request):
    """Show all transactions with filtering."""
    user = request.user
    transactions = Transaction.objects.filter(user=user).select_related('category', 'account').order_by('-date', '-created_at')
    
    tx_type = request.GET.get('type')
    category_id = request.GET.get('category')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    search = request.GET.get('search')
    
    if tx_type:
        transactions = transactions.filter(transaction_type=tx_type)
    if category_id:
        transactions = transactions.filter(category_id=category_id)
    if start_date:
        transactions = transactions.filter(date__gte=start_date)
    if end_date:
        transactions = transactions.filter(date__lte=end_date)
    if search:
        transactions = transactions.filter(description__icontains=search)
    
    total_expense = transactions.filter(transaction_type='expense').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    total_income = transactions.filter(transaction_type='income').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    categories = Category.objects.filter(is_active=True)
    total_count = transactions.count()
    
    return render(request, 'transactions/transaction_list.html', {
        'transactions': transactions[:100],
        'total_expense': total_expense,
        'total_income': total_income,
        'net_flow': total_income - total_expense,
        'total_count': total_count,
        'categories': categories,
    })


@login_required
def export_transactions(request):
    """Export transactions to CSV or Excel."""
    export_format = request.GET.get('format', 'csv')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    transaction_type = request.GET.get('type', 'expense')
    
    transactions = Transaction.objects.filter(
        user=request.user,
        transaction_type=transaction_type
    ).select_related('category', 'account').order_by('-date')
    
    if start_date:
        transactions = transactions.filter(date__gte=start_date)
    if end_date:
        transactions = transactions.filter(date__lte=end_date)
    
    if export_format == 'csv':
        import csv
        import io
        from django.http import HttpResponse
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Date', 'Type', 'Category', 'Amount', 'Description', 'Account', 'Tags'])
        
        for tx in transactions:
            writer.writerow([
                tx.date.strftime('%Y-%m-%d'),
                tx.transaction_type,
                tx.category.name if tx.category else '',
                float(tx.amount),
                tx.description,
                tx.account.name if tx.account else '',
                tx.tags
            ])
        
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{transaction_type}s_{start_date or "all"}_{end_date or ""}.csv"'
        return response
    
    return JsonResponse({'error': 'Invalid format'})


@login_required
def spending_trends(request):
    """Get weekly spending trends."""
    user = request.user
    weeks = int(request.GET.get('weeks', 12))
    today = timezone.now().date()
    
    trends = []
    for i in range(weeks - 1, -1, -1):
        week_start = today - timedelta(days=(i * 7) + 7)
        week_end = today - timedelta(days=i * 7)
        
        total = Transaction.objects.filter(
            user=user,
            transaction_type='expense',
            date__gte=week_start,
            date__lt=week_end
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        trends.append({
            'week': f"W{(weeks - i)}",
            'start': week_start.strftime('%b %d'),
            'end': week_end.strftime('%b %d'),
            'total': float(total)
        })
    
    return JsonResponse(trends, safe=False)


@login_required
def category_breakdown(request):
    """Get category breakdown for a period."""
    user = request.user
    period = request.GET.get('period', 'month')
    today = timezone.now().date()
    
    if period == 'week':
        start = today - timedelta(days=7)
    elif period == 'year':
        start = today.replace(month=1, day=1)
    else:
        start = today.replace(day=1)
    
    expenses = Transaction.objects.filter(
        user=user,
        transaction_type='expense',
        date__gte=start
    ).values('category__name', 'category__color').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    data = [{
        'category': e['category__name'],
        'color': e['category__color'],
        'total': float(e['total'])
    } for e in expenses]
    
    return JsonResponse(data, safe=False)


@login_required
def annual_summary(request):
    """Get annual summary report."""
    user = request.user
    year = int(request.GET.get('year', timezone.now().year))
    
    total_income = Decimal('0')
    total_expense = Decimal('0')
    category_breakdown = {}
    
    for month in range(1, 13):
        m_start = datetime(year, month, 1).date()
        if month == 12:
            m_end = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            m_end = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        income = Transaction.objects.filter(
            user=user,
            transaction_type='income',
            date__gte=m_start,
            date__lte=m_end
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        expense = Transaction.objects.filter(
            user=user,
            transaction_type='expense',
            date__gte=m_start,
            date__lte=m_end
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        total_income += income
        total_expense += expense
    
    # Category breakdown for the year
    year_expenses = Transaction.objects.filter(
        user=user,
        transaction_type='expense',
        date__year=year
    ).values('category__name').annotate(total=Sum('amount')).order_by('-total')
    
    for cat in year_expenses:
        category_breakdown[cat['category__name']] = float(cat['total'])
    
    return JsonResponse({
        'year': year,
        'total_income': float(total_income),
        'total_expense': float(total_expense),
        'net_savings': float(total_income - total_expense),
        'category_breakdown': category_breakdown,
        'average_monthly_expense': float(total_expense) / 12
    })


@login_required
def analytics(request):
    """Analytics dashboard view."""
    from datetime import datetime
    from django.utils import timezone
    
    user = request.user
    today = timezone.now().date()
    current_year = today.year
    
    # Get annual stats
    annual_income = Transaction.objects.filter(
        user=user, transaction_type='income', date__year=current_year
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    annual_expense = Transaction.objects.filter(
        user=user, transaction_type='expense', date__year=current_year
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    # Monthly data
    monthly_data = []
    for i in range(5, -1, -1):
        m = today.month - i
        y = current_year
        while m <= 0:
            m += 12
            y -= 1
        m_start = datetime(y, m, 1).date()
        if m == 12:
            m_end = datetime(y + 1, 1, 1).date() - timedelta(days=1)
        else:
            m_end = datetime(y, m + 1, 1).date() - timedelta(days=1)
        
        income = Transaction.objects.filter(
            user=user, transaction_type='income', date__gte=m_start, date__lte=m_end
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        expense = Transaction.objects.filter(
            user=user, transaction_type='expense', date__gte=m_start, date__lte=m_end
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        monthly_data.append({
            'month': m_start.strftime('%b %Y'),
            'income': float(income),
            'expense': float(expense)
        })
    
    # Category expenses
    month_start = today.replace(day=1)
    category_expenses = list(Transaction.objects.filter(
        user=user, transaction_type='expense', date__gte=month_start
    ).values('category__name', 'category__color').annotate(total=Sum('amount')).order_by('-total')[:5])
    
    # Savings goals
    savings_goals = SavingsGoal.objects.filter(user=user, status='active')[:5]
    
    # Streak
    try:
        streak = user.streak
        current_streak = streak.current_streak
        streak_status = streak.get_streak_status()
    except:
        current_streak = 0
        streak_status = "Start logging!"
    
    context = {
        'annual_income': annual_income,
        'annual_expense': annual_expense,
        'net_savings': annual_income - annual_expense,
        'avg_expense': annual_expense / 12 if annual_expense > 0 else 0,
        'monthly_data': monthly_data,
        'category_expenses': category_expenses,
        'savings_goals': savings_goals,
        'current_streak': current_streak,
        'streak_status': streak_status,
        'current_year': current_year,
    }
    return render(request, 'analytics/analytics.html', context)
