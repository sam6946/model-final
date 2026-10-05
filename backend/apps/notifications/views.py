"""API des notifications : liste paginée, compteur, lecture, préférences."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.notifications.models import Notification
from apps.notifications.serializers import (
    NotificationCreateSerializer,
    NotificationPreferenceSerializer,
    NotificationSerializer,
)
from apps.notifications.services import mark_all_read, notify, preferences_for, unread_count
from common.pagination import KemtaCursorPagination, KemtaPageNumberPagination
from common.permission_codes import Perm
from common.permissions import HasPermission

User = get_user_model()


class NotificationListView(APIView):
    """Fil de notifications de l'utilisateur connecté (pagination par curseur)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Notification.objects.filter(recipient=request.user).order_by("-created_at", "-id")
        if request.query_params.get("unread") in {"1", "true"}:
            queryset = queryset.filter(read_at__isnull=True)
        if request.query_params.get("type"):
            queryset = queryset.filter(notification_type=request.query_params["type"])

        paginator = KemtaCursorPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = NotificationSerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data)
        response.data["unread_count"] = unread_count(user=request.user)
        return response


class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"unread_count": unread_count(user=request.user)})


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int | None = None):
        if pk is None:
            updated = mark_all_read(user=request.user)
            return Response({"message": "Toutes vos notifications sont marquées comme lues.", "updated": updated})
        notification = Notification.objects.filter(pk=pk, recipient=request.user).first()
        if notification is None:
            return Response(
                {"error": {"code": "not_found", "message": "Cette notification est introuvable."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        notification.mark_read()
        return Response({"message": "Notification marquée comme lue.", "unread_count": unread_count(user=request.user)})


class NotificationPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(NotificationPreferenceSerializer(preferences_for(request.user)).data)

    def patch(self, request):
        serializer = NotificationPreferenceSerializer(
            preferences_for(request.user), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AdminNotificationViewSet(ModelViewSet):
    """Back-office : historique global et envoi manuel de messages."""

    permission_classes = [IsAuthenticated, HasPermission(Perm.MANAGE_NOTIFICATIONS)]
    serializer_class = NotificationSerializer
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["notification_type", "status", "level", "recipient"]
    search_fields = ["title", "body", "recipient__phone", "recipient__first_name", "recipient__last_name"]
    ordering = ["-created_at"]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return Notification.objects.select_related("recipient").all()

    @action(detail=False, methods=["post"], url_path="broadcast")
    def broadcast(self, request):
        serializer = NotificationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        recipients = User.objects.filter(pk__in=data["recipients"], is_active=True)
        sent = 0
        for recipient in recipients:
            result = notify(
                recipient=recipient,
                notification_type=data["notification_type"],
                title=data["title"],
                body=data["body"],
                action_url=data.get("action_url", ""),
                also_sms=data.get("also_sms", False),
                payload={"reference": "MESSAGE"},
                dedupe_key=f"manual:{request.user.pk}:{timezone.now().timestamp()}:{recipient.pk}",
            )
            sent += 1 if result is not None else 0
        return Response({"message": f"{sent} message(s) programmé(s).", "sent": sent})

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        from django.db.models import Count, Q

        from common.constants import NotificationStatus

        aggregates = Notification.objects.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status=NotificationStatus.PENDING)),
            failed=Count("id", filter=Q(status=NotificationStatus.FAILED)),
            sent=Count("id", filter=Q(status__in=[NotificationStatus.SENT, NotificationStatus.READ])),
        )
        by_type = list(Notification.objects.values("notification_type").annotate(total=Count("id")).order_by("-total")[:10])
        return Response({**aggregates, "by_type": by_type})
