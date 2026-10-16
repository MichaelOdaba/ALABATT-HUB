from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from accounts.models import Membership, MembershipType


class MembershipTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MembershipType
        fields = '__all__'


class MembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = '__all__'
        read_only_fields = [
            'id',
            'user',
            'end_date',
            'status',
            'payment_status',
            'created_at',
            'updated_at',
        ]

    def to_internal_value(self, data):
        if self.instance is not None and (
            'status' in data or 'payment_status' in data
        ):
            raise serializers.ValidationError(
                {
                    'status': (
                        'Membership status is updated only after Paystack confirms payment.'
                    )
                }
            )
        return super().to_internal_value(data)

    def validate(self, attrs):
        membership_type = attrs.get(
            'membership_type', getattr(self.instance, 'membership_type', None)
        )
        start_date = attrs.get('start_date', getattr(self.instance, 'start_date', None))

        if membership_type.duration_days < 1:
            raise serializers.ValidationError(
                {'membership_type': 'The membership plan must have a positive duration.'}
            )

        if self.instance is None:
            if not membership_type.is_active:
                raise serializers.ValidationError(
                    {'membership_type': 'This membership plan is not available.'}
                )

            today = timezone.localdate()
            existing_memberships = Membership.objects.filter(
                user=self.context['request'].user,
                status__in=[Membership.Status.ACTIVE, Membership.Status.PENDING],
            ).filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
            if existing_memberships.exists():
                raise serializers.ValidationError(
                    'You already have an active or pending membership.'
                )

        if (
            self.instance is None
            or 'start_date' in attrs
            or 'membership_type' in attrs
        ):
            attrs['end_date'] = start_date + timedelta(days=membership_type.duration_days)

        return attrs
