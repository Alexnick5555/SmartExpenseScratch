"""
URL configuration for SmartExpense project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from expenses import views as expense_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', expense_views.home, name='home'),
    path('dashboard/', expense_views.dashboard, name='dashboard'),
    path('expenses/', include('expenses.urls')),
    path('accounts/', include('expenses.urls_accounts')),
    path('subscriptions/', include('expenses.urls_subscriptions')),
    path('budgets/', include('expenses.urls_budgets')),
    path('reports/', include('expenses.urls_reports')),
    path('savings-goals/', include('expenses.urls_savings')),
    path('settings/', expense_views.settings_view, name='settings'),
    path('profile/', expense_views.profile, name='profile'),
    path('change-password/', expense_views.change_password, name='change_password'),
    path('delete-account/', expense_views.delete_account, name='delete_account'),
    path('update-username/', expense_views.update_username, name='update_username'),
    path('update-email/', expense_views.update_email, name='update_email'),
    path('quick-add-expense/', expense_views.quick_add_expense, name='quick_add_expense'),
    path('get-monthly-data/', expense_views.get_monthly_data, name='get_monthly_data'),
    path('smart-insights/', expense_views.smart_insights_api, name='smart_insights_api'),
    path('financial-calendar/', expense_views.financial_calendar, name='financial_calendar'),
    path('export-transactions/', expense_views.export_transactions, name='export_transactions'),
    path('spending-trends/', expense_views.spending_trends, name='spending_trends'),
    path('category-breakdown/', expense_views.category_breakdown, name='category_breakdown'),
    path('annual-summary/', expense_views.annual_summary, name='annual_summary'),
    path('analytics/', expense_views.analytics, name='analytics'),
    path('auth/', include('django.contrib.auth.urls')),
    path('register/', expense_views.register, name='register'),
    path('login/', expense_views.user_login, name='login'),
    path('logout/', expense_views.user_logout, name='logout'),
    path('service-worker.js', RedirectView.as_view(url='/static/service-worker.js', permanent=False), name='service_worker'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
