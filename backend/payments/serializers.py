from rest_framework import serializers

from accounts.models import Payment, Refund


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = [field.name for field in Payment._meta.fields]


class PaymentInitiationSerializer(serializers.Serializer):
    class TargetType:
        MEMBERSHIP = 'membership'
        BOOKING = 'booking'
        EQUIPMENT_LOAN = 'equipment_loan'

    target_type = serializers.ChoiceField(
        choices=[TargetType.MEMBERSHIP, TargetType.BOOKING, TargetType.EQUIPMENT_LOAN]
    )
    target_id = serializers.IntegerField(min_value=1)


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = '__all__'
