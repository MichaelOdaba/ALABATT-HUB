from django.urls import path

from .views import (
    EquipmentDetailView,
    EquipmentListCreateView,
    EquipmentLoanDetailView,
    EquipmentLoanListCreateView,
)

urlpatterns = [
    path('equipment/', EquipmentListCreateView.as_view(), name='equipment-list-create'),
    path('equipment/<int:pk>/', EquipmentDetailView.as_view(), name='equipment-detail'),
    path('equipment-loans/', EquipmentLoanListCreateView.as_view(), name='equipment-loan-list-create'),
    path('equipment-loans/<int:pk>/', EquipmentLoanDetailView.as_view(), name='equipment-loan-detail'),
]
