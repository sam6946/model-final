"""Routes des paiements, factures et décaissements."""
from django.urls import include, path

from apps.payments.views import (
    AdminInvoiceViewSet,
    AdminPaymentViewSet,
    AdminPayoutViewSet,
    MyInvoiceViewSet,
    MyPaymentViewSet,
    PaymentInitiateView,
    PaymentWebhookView,
)

urlpatterns = [
    path("payments/initiate/", PaymentInitiateView.as_view(), name="payments-initiate"),
    path("payments/webhook/<str:provider>/", PaymentWebhookView.as_view(), name="payments-webhook"),
    path(
        "payments/",
        include(
            [
                path("", MyPaymentViewSet.as_view({"get": "list"}), name="my-payments"),
                path("stats/", MyPaymentViewSet.as_view({"get": "stats"}), name="my-payments-stats"),
                path("<int:pk>/", MyPaymentViewSet.as_view({"get": "retrieve"}), name="my-payment-detail"),
            ]
        ),
    ),
    path(
        "invoices/",
        include(
            [
                path("", MyInvoiceViewSet.as_view({"get": "list"}), name="my-invoices"),
                path("summary/", MyInvoiceViewSet.as_view({"get": "summary"}), name="my-invoices-summary"),
                path("<int:pk>/", MyInvoiceViewSet.as_view({"get": "retrieve"}), name="my-invoice-detail"),
            ]
        ),
    ),
    path(
        "admin/payments/",
        include(
            [
                path("", AdminPaymentViewSet.as_view({"get": "list"}), name="admin-payments"),
                path("stats/", AdminPaymentViewSet.as_view({"get": "stats"}), name="admin-payments-stats"),
                path("<int:pk>/", AdminPaymentViewSet.as_view({"get": "retrieve"}), name="admin-payment-detail"),
                path("<int:pk>/confirm/", AdminPaymentViewSet.as_view({"post": "confirm"}), name="admin-payment-confirm"),
                path("<int:pk>/fail/", AdminPaymentViewSet.as_view({"post": "fail"}), name="admin-payment-fail"),
            ]
        ),
    ),
    path(
        "admin/invoices/",
        include(
            [
                path("", AdminInvoiceViewSet.as_view({"get": "list", "post": "create"}), name="admin-invoices"),
                path("<int:pk>/", AdminInvoiceViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="admin-invoice-detail"),
                path("<int:pk>/send/", AdminInvoiceViewSet.as_view({"post": "send"}), name="admin-invoice-send"),
            ]
        ),
    ),
    path(
        "admin/payouts/",
        include(
            [
                path("", AdminPayoutViewSet.as_view({"get": "list", "post": "create"}), name="admin-payouts"),
                path("<int:pk>/approve/", AdminPayoutViewSet.as_view({"post": "approve"}), name="admin-payout-approve"),
                path("<int:pk>/mark-paid/", AdminPayoutViewSet.as_view({"post": "mark_paid"}), name="admin-payout-mark-paid"),
            ]
        ),
    ),
]
