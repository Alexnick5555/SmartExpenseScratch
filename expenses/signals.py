"""
Signal handlers for SmartExpense app.
"""
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import Category, DEFAULT_EXPENSE_CATEGORIES, DEFAULT_INCOME_CATEGORIES


@receiver(post_migrate)
def create_default_categories(sender, **kwargs):
    """Create default categories after migration."""
    if sender.name == 'expenses':
        for name, icon, color in DEFAULT_EXPENSE_CATEGORIES:
            Category.objects.get_or_create(
                name=name,
                defaults={
                    'icon': icon,
                    'color': color,
                    'category_type': 'expense'
                }
            )

        for name, icon, color in DEFAULT_INCOME_CATEGORIES:
            Category.objects.get_or_create(
                name=name,
                defaults={
                    'icon': icon,
                    'color': color,
                    'category_type': 'income'
                }
            )
