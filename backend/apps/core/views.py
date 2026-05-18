"""
Core views for Finsio.

Includes:
  - HealthCheckView: service health status
  - EntityListView/CreateView/DetailView: entity CRUD
"""

import logging

import redis as redis_lib
from django.conf import settings
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Entity
from .serializers import EntityCreateSerializer, EntitySerializer

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    GET /health/

    Returns the health status of all Finsio components:
    database, Redis, and the gateway (if reachable).
    No authentication required.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        db_status = self._check_database()
        redis_status = self._check_redis()

        overall = "healthy" if all(
            s == "ok" for s in [db_status, redis_status]
        ) else "degraded"

        code = status.HTTP_200_OK if overall == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE

        from django.utils import timezone
        return Response(
            {
                "status": overall,
                "version": "1.0.0",
                "timestamp": timezone.now().isoformat(),
                "database": db_status,
                "redis": redis_status,
            },
            status=code,
        )

    @staticmethod
    def _check_database() -> str:
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return "ok"
        except Exception as e:
            logger.error("Database health check failed: %s", e)
            return "error"

    @staticmethod
    def _check_redis() -> str:
        try:
            r = redis_lib.from_url(settings.CELERY_BROKER_URL)
            r.ping()
            return "ok"
        except Exception as e:
            logger.error("Redis health check failed: %s", e)
            return "error"


class EntityListView(generics.ListAPIView):
    """
    GET /internal/entities/

    List all active business entities.
    """

    serializer_class = EntitySerializer
    queryset = Entity.objects.filter(is_active=True)


class EntityCreateView(generics.CreateAPIView):
    """
    POST /internal/entities/create

    Create a new business entity.
    """

    serializer_class = EntityCreateSerializer
    queryset = Entity.objects.all()


class EntityDetailView(generics.RetrieveAPIView):
    """
    GET /internal/entities/{slug}

    Retrieve a single entity by slug.
    """

    serializer_class = EntitySerializer
    queryset = Entity.objects.all()
    lookup_field = "slug"
