"""
URL patterns for analytics.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.analytics, name='analytics'),
    path('spending-heatmap/', views.spending_heatmap, name='spending_heatmap'),
    path('top-spending/', views.top_spending_analysis, name='top_spending'),
    path('income-vs-expense/', views.income_vs_expense_trends, name='income_vs_expense_trends'),
    path('net-worth/', views.net_worth_dashboard, name='net_worth_dashboard'),
]
