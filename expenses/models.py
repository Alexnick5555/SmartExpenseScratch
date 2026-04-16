"""
Models for SmartExpense - Personal Expense & Subscription Tracker
Developed by Nitish Mishra & Nishant Singh
"""
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from decimal import Decimal


class User(AbstractUser):
    """Extended User model with additional preferences."""
    currency = models.CharField(
        max_length=3,
        default='INR',
        choices=[
            ('INR', 'Indian Rupee (₹)'),
            ('USD', 'US Dollar ($)'),
            ('EUR', 'Euro (€)'),
        ]
    )
    salary_day = models.IntegerField(
        default=1,
        help_text='Day of month when salary is credited'
    )
    phone = models.CharField(max_length=15, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    email_notifications = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.get_full_name() or self.username}"


class Category(models.Model):
    """Expense and Income categories."""
    CATEGORY_TYPE_CHOICES = [
        ('expense', 'Expense'),
        ('income', 'Income'),
        ('both', 'Both'),
    ]

    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, default='bi-tag')
    color = models.CharField(max_length=7, default='#6B7280')
    category_type = models.CharField(
        max_length=10,
        choices=CATEGORY_TYPE_CHOICES,
        default='expense'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Account(models.Model):
    """User's financial accounts."""
    ACCOUNT_TYPE_CHOICES = [
        ('cash', 'Cash'),
        ('savings', 'Savings Account'),
        ('current', 'Current Account'),
        ('credit_card', 'Credit Card'),
        ('bank', 'Bank Account'),
        ('fixed_deposit', 'Fixed Deposit'),
        ('investment', 'Investment Account'),
        ('wallet', 'Digital Wallet'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts')
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='INR')
    color = models.CharField(max_length=7, default='#4CAF50')
    icon = models.CharField(max_length=50, default='bi-wallet2')
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Accounts'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} (₹{self.balance})"
    
    def get_available_balance(self):
        """Get available balance for credit cards."""
        if self.account_type == 'credit_card' and self.credit_limit:
            return self.credit_limit - self.balance
        return self.balance
        return f"{self.name} ({self.get_account_type_display()})"


class Transaction(models.Model):
    """Financial transactions (expenses and income)."""
    TRANSACTION_TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, related_name='transactions')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.TextField(blank=True)
    date = models.DateField(default=timezone.now)
    tags = models.CharField(max_length=255, blank=True, help_text='Comma-separated tags')
    notes = models.TextField(blank=True, null=True, help_text='Additional notes or details')
    is_recurring = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.transaction_type.capitalize()}: ₹{self.amount} - {self.description[:30]}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        if not is_new and self.account:
            try:
                old_transaction = Transaction.objects.get(pk=self.pk)
                old_account = old_transaction.account
                new_account = self.account
                
                if old_account and old_account != new_account:
                    if old_transaction.transaction_type == 'income':
                        old_account.balance -= old_transaction.amount
                    else:
                        old_account.balance += old_transaction.amount
                    old_account.save()
            except Transaction.DoesNotExist:
                pass
        
        if self.account:
            if self.transaction_type == 'income':
                self.account.balance += self.amount
            else:
                self.account.balance -= self.amount
            self.account.save()
        
        super().save(*args, **kwargs)


class Subscription(models.Model):
    """Recurring subscriptions and payments."""
    CYCLE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    cycle = models.CharField(max_length=15, choices=CYCLE_CHOICES, default='monthly')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='subscriptions')
    next_payment = models.DateField()
    reminder_days = models.IntegerField(default=3)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['next_payment']

    def __str__(self):
        return f"{self.name} - ₹{self.amount}/{self.get_cycle_display()}"

    def get_monthly_amount(self):
        """Calculate monthly equivalent amount."""
        cycle_amounts = {
            'daily': Decimal('30'),
            'weekly': Decimal('4'),
            'monthly': Decimal('1'),
            'quarterly': Decimal('0.33'),
            'yearly': Decimal('0.083'),
        }
        return self.amount * cycle_amounts.get(self.cycle, Decimal('1'))


class Budget(models.Model):
    """Monthly budget for categories."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='budgets')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    month = models.IntegerField()
    year = models.IntegerField()

    class Meta:
        unique_together = ['user', 'category', 'month', 'year']
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.category.name}: ₹{self.amount} ({self.month}/{self.year})"


class SavingsGoal(models.Model):
    """Savings goals with progress tracking."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
    ]

    GOAL_TYPE_CHOICES = [
        ('emergency', 'Emergency Fund'),
        ('vacation', 'Vacation'),
        ('purchase', 'Big Purchase'),
        ('investment', 'Investment'),
        ('debt', 'Debt Payoff'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='savings_goals')
    name = models.CharField(max_length=200)
    goal_type = models.CharField(max_length=20, choices=GOAL_TYPE_CHOICES, default='other')
    target_amount = models.DecimalField(max_digits=15, decimal_places=2)
    current_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    icon = models.CharField(max_length=50, default='bi-piggy-bank')
    color = models.CharField(max_length=7, default='#4CAF50')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name}: ₹{self.current_amount}/₹{self.target_amount}"

    def get_progress_percentage(self):
        """Calculate progress percentage."""
        if self.target_amount > 0:
            return min(100, (float(self.current_amount) / float(self.target_amount)) * 100)
        return 0
    
    def get_days_remaining(self):
        """Days until deadline."""
        if self.deadline:
            from django.utils import timezone
            delta = self.deadline - timezone.now().date()
            return max(0, delta.days)
        return None
    
    def get_monthly_needed(self):
        """Monthly amount needed to reach goal."""
        days = self.get_days_remaining()
        if days and days > 0:
            remaining = float(self.target_amount - self.current_amount)
            months = days / 30
            if months > 0:
                return remaining / months
        return float(self.target_amount)


# Default categories to be created
class UserStreak(models.Model):
    """Track user logging streaks."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='streak')
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_logged = models.DateField(null=True, blank=True)
    total_days_logged = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.current_streak} day streak"

    def update_streak(self):
        """Update streak based on last logged date."""
        from django.utils import timezone
        today = timezone.now().date()
        
        if self.last_logged:
            delta = (today - self.last_logged).days
            if delta == 0:
                return  # Already logged today
            elif delta == 1:
                self.current_streak += 1
            else:
                self.current_streak = 1
        else:
            self.current_streak = 1
        
        self.last_logged = today
        self.total_days_logged += 1
        
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak
        
        self.save()
    
    def get_streak_status(self):
        """Get streak status message."""
        if self.current_streak >= 30:
            return "Legendary!"
        elif self.current_streak >= 14:
            return "On fire!"
        elif self.current_streak >= 7:
            return "Great week!"
        elif self.current_streak >= 3:
            return "Building momentum!"
        elif self.current_streak > 0:
            return "Keep it up!"
        return "Start logging!"


DEFAULT_EXPENSE_CATEGORIES = [
    ('Food & Dining', 'bi-utensils', '#E53935'),
    ('Transportation', 'bi-car-front', '#1565C0'),
    ('Shopping', 'bi-bag', '#9C27B0'),
    ('Bills & Utilities', 'bi-receipt', '#FF6F00'),
    ('Entertainment', 'bi-film', '#E91E63'),
    ('Health & Fitness', 'bi-heart-pulse', '#43A047'),
    ('Education', 'bi-book', '#3F51B5'),
    ('Travel', 'bi-airplane', '#00BCD4'),
    ('Groceries', 'bi-cart3', '#8BC34A'),
    ('Others', 'bi-three-dots', '#6B7280'),
]

DEFAULT_INCOME_CATEGORIES = [
    ('Salary', 'bi-briefcase', '#43A047'),
    ('Freelance', 'bi-laptop', '#1565C0'),
    ('Investment', 'bi-graph-up', '#FFD700'),
    ('Gift', 'bi-gift', '#E91E63'),
    ('Others', 'bi-three-dots', '#6B7280'),
]


class TransactionTemplate(models.Model):
    """Transaction templates for quick entry."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transaction_templates')
    name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, related_name='templates')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='templates')
    transaction_type = models.CharField(
        max_length=10,
        choices=Transaction.TRANSACTION_TYPE_CHOICES,
        default='expense'
    )
    description = models.TextField(blank=True)
    tags = models.CharField(max_length=255, blank=True, help_text='Comma-separated tags')
    is_favorite = models.BooleanField(default=False)
    usage_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Transaction Templates'
        ordering = ['-is_favorite', '-usage_count', '-created_at']

    def __str__(self):
        return f"{self.name}: {self.transaction_type} ₹{self.amount}"
    
    def use_template(self):
        """Increment usage count when template is used."""
        self.usage_count += 1
        self.save()


class RecurringTransaction(models.Model):
    """Recurring transactions for automated bill payments."""
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_transactions')
    name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, related_name='recurring_transactions')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='recurring_transactions')
    transaction_type = models.CharField(
        max_length=10,
        choices=Transaction.TRANSACTION_TYPE_CHOICES,
        default='expense'
    )
    description = models.TextField(blank=True)
    tags = models.CharField(max_length=255, blank=True, help_text='Comma-separated tags')
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='monthly')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text='Leave blank for indefinite')
    next_due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    last_processed_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'Recurring Transactions'
        ordering = ['next_due_date']
    
    def __str__(self):
        return f"{self.name}: {self.transaction_type} ₹{self.amount} ({self.frequency})"
    
    def calculate_next_due_date(self):
        """Calculate the next due date based on frequency."""
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta
        
        if self.frequency == 'daily':
            return self.next_due_date + timedelta(days=1)
        elif self.frequency == 'weekly':
            return self.next_due_date + timedelta(weeks=1)
        elif self.frequency == 'biweekly':
            return self.next_due_date + timedelta(weeks=2)
        elif self.frequency == 'monthly':
            return self.next_due_date + relativedelta(months=1)
        elif self.frequency == 'quarterly':
            return self.next_due_date + relativedelta(months=3)
        elif self.frequency == 'yearly':
            return self.next_due_date + relativedelta(years=1)
        return self.next_due_date
    
    def process_transaction(self):
        """Create a transaction from this recurring transaction."""
        from django.utils import timezone
        
        transaction = Transaction.objects.create(
            user=self.user,
            amount=self.amount,
            account=self.account,
            category=self.category,
            transaction_type=self.transaction_type,
            description=self.description or self.name,
            tags=self.tags,
            date=timezone.now().date()
        )
        
        # Update the recurring transaction
        self.last_processed_date = self.next_due_date
        self.next_due_date = self.calculate_next_due_date()
        
        # Check if we've reached the end date
        if self.end_date and self.next_due_date > self.end_date:
            self.status = 'completed'
        
        self.save()
        
        return transaction
