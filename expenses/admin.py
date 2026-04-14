"""
Admin configuration for SmartExpense app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Category, Account, Transaction, Subscription, Budget, SavingsGoal


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'currency', 'is_staff']
    list_filter = ['is_staff', 'is_superuser', 'currency']
    fieldsets = UserAdmin.fieldsets + (
        ('SmartExpense Settings', {'fields': ('currency', 'salary_day', 'phone', 'avatar', 'email_notifications')}),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'color', 'category_type', 'is_active']
    list_filter = ['category_type', 'is_active']
    search_fields = ['name']


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'account_type', 'balance', 'currency', 'is_active']
    list_filter = ['account_type', 'currency', 'is_active']
    search_fields = ['name', 'user__username']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['date', 'user', 'transaction_type', 'amount', 'category', 'account']
    list_filter = ['transaction_type', 'category', 'date']
    search_fields = ['description', 'user__username']
    date_hierarchy = 'date'


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'amount', 'cycle', 'next_payment', 'is_active']
    list_filter = ['cycle', 'is_active']
    search_fields = ['name', 'user__username']


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['category', 'user', 'amount', 'month', 'year']
    list_filter = ['month', 'year']


@admin.register(SavingsGoal)
class SavingsGoalAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'target_amount', 'current_amount', 'deadline', 'status']
    list_filter = ['status']
    search_fields = ['name', 'user__username']
