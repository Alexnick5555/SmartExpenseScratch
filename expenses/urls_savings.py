"""
URL patterns for savings goals.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.savings_goal_list, name='savings_goal_list'),
    path('add/', views.savings_goal_add, name='savings_goal_add'),
    path('edit/<int:pk>/', views.savings_goal_edit, name='savings_goal_edit'),
    path('delete/<int:pk>/', views.savings_goal_delete, name='savings_goal_delete'),
]
