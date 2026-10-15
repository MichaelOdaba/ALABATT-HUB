from django.urls import path

from .views import (
    MembershipDetailView,
    MembershipListCreateView,
    MembershipTypeDetailView,
    MembershipTypeListCreateView,
)

urlpatterns = [
    path('membership-types/', MembershipTypeListCreateView.as_view(), name='membership-type-list-create'),
    path('membership-types/<int:pk>/', MembershipTypeDetailView.as_view(), name='membership-type-detail'),
    path('memberships/', MembershipListCreateView.as_view(), name='membership-list-create'),
    path('memberships/<int:pk>/', MembershipDetailView.as_view(), name='membership-detail'),
]
