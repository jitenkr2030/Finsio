"""
Serializers for core Finsio models.

Used by DRF views to validate input and serialize output
for Entity and Health endpoints.
"""

from rest_framework import serializers

from .models import Entity


class EntitySerializer(serializers.ModelSerializer):
    """Serializer for the Entity model."""

    class Meta:
        model = Entity
        fields = [
            "id",
            "name",
            "slug",
            "base_currency",
            "beancount_entity_name",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class EntityCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new Entity."""

    class Meta:
        model = Entity
        fields = [
            "name",
            "slug",
            "base_currency",
            "beancount_entity_name",
        ]

    def validate_slug(self, value):
        if Entity.objects.filter(slug=value).exists():
            raise serializers.ValidationError("An entity with this slug already exists.")
        return value


class HealthSerializer(serializers.Serializer):
    """Serializer for the health check response."""
    status = serializers.CharField()
    version = serializers.CharField()
    database = serializers.CharField()
    redis = serializers.CharField()
