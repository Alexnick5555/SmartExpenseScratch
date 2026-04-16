"""
URL patterns for recurring transactions.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.recurring_transaction_list, name='recurring_transaction_list'),
    path('add/', views.recurring_transaction_add, name='recurring_transaction_add'),
    path('<int:pk>/edit/', views.recurring_transaction_edit, name='recurring_transaction_edit'),
    path('<int:pk>/delete/', views.recurring_transaction_delete, name='recurring_transaction_delete'),
    path('<int:pk>/process/', views.recurring_transaction_process, name='recurring_transaction_process'),
    path('<int:pk>/pause/', views.recurring_transaction_pause, name='recurring_transaction_pause'),
    path('<int:pk>/resume/', views.recurring_transaction_resume, name='recurring_transaction_resume'),
]
