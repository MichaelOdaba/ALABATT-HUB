from django.urls import path

from .views import (
    BookingDetailView,
    BookingListCreateView,
    BookingCancelView,
    BookingDecisionView,
    FacilityDetailView,
    FacilityListCreateView,
    SportsCentreDetailView,
    SportsCentreListCreateView,
)

urlpatterns = [
    path('centres/', SportsCentreListCreateView.as_view(), name='sports-centre-list-create'),
    path('centres/<int:pk>/', SportsCentreDetailView.as_view(), name='sports-centre-detail'),
    path('facilities/', FacilityListCreateView.as_view(), name='facility-list-create'),
    path('facilities/<int:pk>/', FacilityDetailView.as_view(), name='facility-detail'),
    path('bookings/', BookingListCreateView.as_view(), name='booking-list-create'),
    path('bookings/<int:pk>/decision/', BookingDecisionView.as_view(), name='booking-decision'),
    path('bookings/<int:pk>/cancel/', BookingCancelView.as_view(), name='booking-cancel'),
    path('bookings/<int:pk>/', BookingDetailView.as_view(), name='booking-detail'),
]
