from rest_framework import serializers

from accounts.models import Equipment, EquipmentLoan


class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = '__all__'
        read_only_fields = ['id', 'available_quantity', 'created_at']

    def validate(self, attrs):
        if self.instance and 'quantity' in attrs:
            loaned_quantity = self.instance.quantity - self.instance.available_quantity
            if attrs['quantity'] < loaned_quantity:
                raise serializers.ValidationError(
                    {'quantity': 'Total quantity cannot be less than units currently loaned.'}
                )
        return attrs

    def update(self, instance, validated_data):
        new_quantity = validated_data.get('quantity', instance.quantity)
        instance.available_quantity += new_quantity - instance.quantity
        return super().update(instance, validated_data)


class EquipmentLoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentLoan
        fields = '__all__'
        read_only_fields = [
            'id',
            'user',
            'loan_date',
            'return_date',
            'deposit_status',
        ]

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if request is None or request.user.role != 'manager':
            fields['status'].read_only = True
        if self.instance:
            fields['equipment'].read_only = True
            fields['quantity'].read_only = True
        return fields
