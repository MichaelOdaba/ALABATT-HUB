from rest_framework import generics

from accounts.models import Booking, Facility, SportsCentre
from .serializers import BookingSerializer, FacilitySerializer, SportsCentreSerializer


class SportsCentreListCreateView(generics.ListCreateAPIView):
    queryset = SportsCentre.objects.all()
    serializer_class = SportsCentreSerializer


class SportsCentreDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SportsCentre.objects.all()
    serializer_class = SportsCentreSerializer


class FacilityListCreateView(generics.ListCreateAPIView):
    queryset = Facility.objects.all()
    serializer_class = FacilitySerializer


class FacilityDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Facility.objects.all()
    serializer_class = FacilitySerializer


class BookingListCreateView(generics.ListCreateAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer


class BookingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
