"""
URL patterns for reports.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.reports, name='reports'),
    path('export/', views.export_csv, name='export_csv'),
]
