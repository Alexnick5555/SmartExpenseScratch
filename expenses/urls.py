"""
URL patterns for expenses app.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Expense URLs
    path('', views.expense_list, name='expense_list'),
    path('add/', views.expense_add, name='expense_add'),
    path('edit/<int:pk>/', views.expense_edit, name='expense_edit'),
    path('delete/<int:pk>/', views.expense_delete, name='expense_delete'),
    path('bulk/', views.bulk_transaction_action, name='bulk_transaction_action'),

    # Income URLs
    path('income/', views.income_list, name='income_list'),
    path('income/add/', views.income_add, name='income_add'),
    path('income/edit/<int:pk>/', views.income_edit, name='income_edit'),
    path('income/delete/<int:pk>/', views.income_delete, name='income_delete'),

    # Transaction Template URLs
    path('templates/', views.template_list, name='template_list'),
    path('templates/add/', views.template_add, name='template_add'),
    path('templates/edit/<int:pk>/', views.template_edit, name='template_edit'),
    path('templates/delete/<int:pk>/', views.template_delete, name='template_delete'),
    path('templates/use/<int:pk>/', views.use_template, name='use_template'),
]
