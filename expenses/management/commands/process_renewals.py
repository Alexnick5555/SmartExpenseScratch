from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from expenses.models import Subscription, Account, Transaction
from datetime import timedelta
from decimal import Decimal


class Command(BaseCommand):
    help = 'Process subscription renewals - deduct amounts from accounts and update next payment dates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = timezone.now().date()

        subscriptions = Subscription.objects.filter(
            Q(next_payment__lte=today) & Q(is_active=True)
        ).select_related('user', 'category')

        if not subscriptions:
            self.stdout.write(self.style.WARNING('No subscriptions due for renewal today.'))
            return

        processed = 0
        errors = 0

        for sub in subscriptions:
            try:
                # Get user's default account or first active account
                account = Account.objects.filter(
                    user=sub.user,
                    is_active=True
                ).order_by('-is_default', '-balance').first()

                if not account:
                    self.stdout.write(self.style.WARNING(
                        f'No active account found for user {sub.user.username}. Skipping {sub.name}'
                    ))
                    errors += 1
                    continue

                # Check if sufficient balance (except for credit cards)
                if account.account_type != 'credit_card' and account.balance < sub.amount:
                    self.stdout.write(self.style.WARNING(
                        f'Insufficient balance in {account.name} for {sub.name}. Skipping'
                    ))
                    errors += 1
                    continue

                if dry_run:
                    self.stdout.write(self.style.WARNING(
                        f'[DRY RUN] Would process: {sub.name} - ₹{sub.amount} from {account.name}'
                    ))
                    processed += 1
                    continue

                # Create expense transaction
                Transaction.objects.create(
                    user=sub.user,
                    account=account,
                    category=sub.category,
                    transaction_type='expense',
                    amount=sub.amount,
                    description=f'Auto-renewal: {sub.name}',
                    date=today,
                    is_recurring=True,
                )

                # Deduct from account
                account.balance -= sub.amount
                account.save()

                # Update next_payment date
                sub.next_payment = self._calculate_next_payment(sub.next_payment, sub.cycle)
                sub.save()

                processed += 1
                self.stdout.write(self.style.SUCCESS(
                    f'Processed: {sub.name} - ₹{sub.amount} deducted from {account.name}'
                ))

            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(
                    f'Error processing {sub.name}: {str(e)}'
                ))

        self.stdout.write(self.style.WARNING(
            f'\nProcessed: {processed} subscriptions'
        ))
        if errors > 0:
            self.stdout.write(self.style.ERROR(f'Errors: {errors}'))
        if dry_run:
            self.stdout.write(self.style.WARNING('(Dry run - no changes made)'))

    def _calculate_next_payment(self, current_date, cycle):
        """Calculate the next payment date based on cycle."""
        if cycle == 'daily':
            return current_date + timedelta(days=1)
        elif cycle == 'weekly':
            return current_date + timedelta(weeks=1)
        elif cycle == 'monthly':
            return self._add_months(current_date, 1)
        elif cycle == 'quarterly':
            return self._add_months(current_date, 3)
        elif cycle == 'yearly':
            return self._add_months(current_date, 12)
        return current_date + timedelta(days=30)

    def _add_months(self, date, months):
        """Add months to a date, handling month-end edge cases."""
        from calendar import monthrange
        year = date.year
        month = date.month + months
        while month > 12:
            month -= 12
            year += 1
        day = min(date.day, monthrange(year, month)[1])
        return date.replace(year=year, month=month, day=day)
