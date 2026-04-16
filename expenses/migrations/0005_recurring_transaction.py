# Generated manually for RecurringTransaction model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0004_transaction_template'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecurringTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=15)),
                ('description', models.TextField(blank=True)),
                ('tags', models.CharField(blank=True, help_text='Comma-separated tags', max_length=255)),
                ('frequency', models.CharField(choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('biweekly', 'Bi-weekly'), ('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('yearly', 'Yearly')], default='monthly', max_length=20)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField(blank=True, help_text='Leave blank for indefinite', null=True)),
                ('next_due_date', models.DateField()),
                ('status', models.CharField(choices=[('active', 'Active'), ('paused', 'Paused'), ('completed', 'Completed')], default='active', max_length=20)),
                ('last_processed_date', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('account', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recurring_transactions', to='expenses.account')),
                ('category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recurring_transactions', to='expenses.category')),
                ('transaction_type', models.CharField(choices=[('expense', 'Expense'), ('income', 'Income')], default='expense', max_length=10)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recurring_transactions', to='expenses.user')),
            ],
            options={
                'verbose_name_plural': 'Recurring Transactions',
                'ordering': ['next_due_date'],
            },
        ),
    ]
