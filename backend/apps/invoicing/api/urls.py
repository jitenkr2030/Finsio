"""
URL routes for invoice API endpoints (under /internal/invoicing/).
"""

from django.urls import path

from . import views

urlpatterns = [
    path("invoices", views.invoice_list, name="invoice-list"),
    path("invoices/create", views.invoice_create, name="invoice-create"),
    path("invoices/<uuid:invoice_id>", views.invoice_detail, name="invoice-detail"),
]
