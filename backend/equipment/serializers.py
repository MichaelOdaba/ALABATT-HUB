from rest_framework import serializers

from accounts.models import Equipment, EquipmentLoan


class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = '__all__'


class EquipmentLoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentLoan
        fields = '__all__'
