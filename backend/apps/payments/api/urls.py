"""
URL routes for payment API endpoints (under /internal/payments/).
"""

from django.urls import path

from . import views

urlpatterns = [
    path("prepare", views.prepare_payment, name="payment-prepare"),
    path("processors", views.list_processors, name="payment-processors"),
    path("", views.payment_list, name="payment-list"),
    path("<uuid:payment_id>", views.payment_status, name="payment-status"),
]
