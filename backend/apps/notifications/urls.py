"""Routes des notifications."""
from django.urls import include, path

from apps.notifications.views import (
    AdminNotificationViewSet,
    NotificationListView,
    NotificationMarkReadView,
    NotificationPreferenceView,
    NotificationUnreadCountView,
)

urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name="notifications-list"),
    path("notifications/unread-count/", NotificationUnreadCountView.as_view(), name="notifications-unread"),
    path("notifications/read-all/", NotificationMarkReadView.as_view(), name="notifications-read-all"),
    path("notifications/<int:pk>/read/", NotificationMarkReadView.as_view(), name="notification-read"),
    path("notifications/preferences/", NotificationPreferenceView.as_view(), name="notifications-preferences"),
    path(
        "admin/notifications/",
        include(
            [
                path("", AdminNotificationViewSet.as_view({"get": "list", "post": "create"}), name="admin-notifications"),
                path("broadcast/", AdminNotificationViewSet.as_view({"post": "broadcast"}), name="admin-notifications-broadcast"),
                path("stats/", AdminNotificationViewSet.as_view({"get": "stats"}), name="admin-notifications-stats"),
                path("<int:pk>/", AdminNotificationViewSet.as_view({"get": "retrieve"}), name="admin-notification-detail"),
            ]
        ),
    ),
]
