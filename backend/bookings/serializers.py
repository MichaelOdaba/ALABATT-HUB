from rest_framework import serializers

from accounts.models import Booking, Facility, SportsCentre


class SportsCentreSerializer(serializers.ModelSerializer):
    class Meta:
        model = SportsCentre
        fields = '__all__'


class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = '__all__'


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = '__all__'
