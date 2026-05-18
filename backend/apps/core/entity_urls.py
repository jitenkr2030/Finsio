"""
URL routes for Entity management.
"""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.EntityListView.as_view(), name="entity-list"),
    path("create", views.EntityCreateView.as_view(), name="entity-create"),
    path("<slug:slug>", views.EntityDetailView.as_view(), name="entity-detail"),
]
