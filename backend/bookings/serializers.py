from decimal import Decimal

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
        read_only_fields = [
            'id',
            'user',
            'total_cost',
            'status',
            'approved_by',
            'created_at',
            'updated_at',
        ]

    def validate(self, attrs):
        facility = attrs.get('facility', getattr(self.instance, 'facility', None))
        start_time = attrs.get('start_time', getattr(self.instance, 'start_time', None))
        end_time = attrs.get('end_time', getattr(self.instance, 'end_time', None))
        is_event = attrs.get('is_event', getattr(self.instance, 'is_event', False))

        request = self.context.get('request')
        if (
            is_event
            and request
            and request.user.role not in {'coach', 'manager'}
        ):
            raise serializers.ValidationError(
                {'is_event': 'Only coaches or managers can create event bookings.'}
            )

        if end_time <= start_time:
            raise serializers.ValidationError(
                {'end_time': 'The end time must be later than the start time.'}
            )

        if facility.availability_status != Facility.Availability.AVAILABLE:
            raise serializers.ValidationError(
                {'facility': 'This facility is not currently available for booking.'}
            )

        overlapping_bookings = Booking.objects.filter(
            facility=facility,
            status__in=[Booking.Status.PENDING, Booking.Status.APPROVED],
            start_time__lt=end_time,
            end_time__gt=start_time,
        )
        if self.instance:
            overlapping_bookings = overlapping_bookings.exclude(pk=self.instance.pk)
        if overlapping_bookings.exists():
            raise serializers.ValidationError(
                'This facility already has a booking during that time.'
            )

        duration_hours = Decimal(str((end_time - start_time).total_seconds())) / Decimal('3600')
        event_fee = facility.event_fee if is_event else Decimal('0.00')
        attrs['total_cost'] = (
            facility.hourly_rate * duration_hours + event_fee
        ).quantize(Decimal('0.01'))
        return attrs
