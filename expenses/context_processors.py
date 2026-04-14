from django.utils import timezone
from datetime import timedelta


def bill_reminders(request):
    if not request.user.is_authenticated:
        return {}
    today = timezone.now().date()
    try:
        due_soon = list(
            request.user.subscriptions.filter(
                is_active=True,
                next_payment__gte=today,
                next_payment__lte=today + timedelta(days=3)
            ).order_by('next_payment')
        )
    except Exception:
        due_soon = []
    return {'bill_reminders': due_soon}
