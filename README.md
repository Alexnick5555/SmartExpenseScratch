# SmartExpense

Personal Expense & Subscription Tracker

## Features

- Track expenses and income
- Budget management
- Subscription tracking
- Visual charts and analytics
- Savings goals with progress
- Spending streaks
- Export to CSV
- Analytics dashboard

## Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

## Tech Stack

- Django 4.2
- Python 3.12
- Bootstrap 5
- Chart.js
- SQLite (default)

## License

MIT