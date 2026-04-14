"""
URL patterns for accounts.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.account_list, name='account_list'),
    path('add/', views.account_add, name='account_add'),
    path('edit/<int:pk>/', views.account_edit, name='account_edit'),
    path('delete/<int:pk>/', views.account_delete, name='account_delete'),
]
