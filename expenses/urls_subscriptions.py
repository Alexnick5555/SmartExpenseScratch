"""
URL patterns for subscriptions.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.subscription_list, name='subscription_list'),
    path('add/', views.subscription_add, name='subscription_add'),
    path('edit/<int:pk>/', views.subscription_edit, name='subscription_edit'),
    path('delete/<int:pk>/', views.subscription_delete, name='subscription_delete'),
]
