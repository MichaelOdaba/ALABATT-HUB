from django.urls import path

from .views import (
    PaymentDetailView,
    PaymentListCreateView,
    RefundDetailView,
    RefundListCreateView,
)

urlpatterns = [
    path('payments/', PaymentListCreateView.as_view(), name='payment-list-create'),
    path('payments/<int:pk>/', PaymentDetailView.as_view(), name='payment-detail'),
    path('refunds/', RefundListCreateView.as_view(), name='refund-list-create'),
    path('refunds/<int:pk>/', RefundDetailView.as_view(), name='refund-detail'),
]
