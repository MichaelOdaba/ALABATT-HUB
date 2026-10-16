from django.urls import path

from .views import (
    PaymentDetailView,
    PaymentInitiateView,
    PaymentListView,
    PaymentVerifyView,
    PaystackWebhookView,
    RefundDetailView,
    RefundListCreateView,
)

urlpatterns = [
    path('payments/', PaymentListView.as_view(), name='payment-list'),
    path('payments/initiate/', PaymentInitiateView.as_view(), name='payment-initiate'),
    path('payments/verify/<str:reference>/', PaymentVerifyView.as_view(), name='payment-verify'),
    path('payments/webhook/paystack/', PaystackWebhookView.as_view(), name='paystack-webhook'),
    path('payments/<int:pk>/', PaymentDetailView.as_view(), name='payment-detail'),
    path('refunds/', RefundListCreateView.as_view(), name='refund-list-create'),
    path('refunds/<int:pk>/', RefundDetailView.as_view(), name='refund-detail'),
]
