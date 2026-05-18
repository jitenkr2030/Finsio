"""
Core models for Finsio.

Provides:
  - TimeStampedModel: abstract base with UUID pk and timestamps
  - Entity: business entity that owns accounting records
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Abstract base model with UUID primary key, created/updated
    timestamps, and an optional created_by reference.

    Every concrete model in Finsio inherits from this.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class Entity(TimeStampedModel):
    """
    Business entity that owns accounting records.

    Maps one-to-one to a django-ledger EntityModel for the
    operational ledger. The beancount_entity_name is used when
    writing .beancount audit files.

    Example:
        Entity(
            name="Acme Corporation",
            slug="acme",
            base_currency="USD",
            beancount_entity_name="Acme",
        )
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=100)
    ledger_entity_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="References the django-ledger EntityModel UUID",
    )
    beancount_entity_name = models.CharField(
        max_length=100,
        help_text="Entity name used in .beancount files (e.g. Acme)",
    )
    base_currency = models.CharField(max_length=3, default="USD")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "entities"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        # Auto-generate beancount entity name if empty
        if not self.beancount_entity_name:
            self.beancount_entity_name = self.name.replace(" ", "")
        super().save(*args, **kwargs)
