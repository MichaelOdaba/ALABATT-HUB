from rest_framework import generics

from accounts.models import Equipment, EquipmentLoan
from .serializers import EquipmentLoanSerializer, EquipmentSerializer


class EquipmentListCreateView(generics.ListCreateAPIView):
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer


class EquipmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer


class EquipmentLoanListCreateView(generics.ListCreateAPIView):
    queryset = EquipmentLoan.objects.all()
    serializer_class = EquipmentLoanSerializer


class EquipmentLoanDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = EquipmentLoan.objects.all()
    serializer_class = EquipmentLoanSerializer
