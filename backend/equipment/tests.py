from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Equipment, EquipmentLoan, User


class EquipmentPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.member = User.objects.create_user(
            username='member',
            email='member@example.com',
            password='SecurePass123!',
        )
        self.other_member = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='SecurePass123!',
        )
        self.manager = User.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='SecurePass123!',
            role=User.Role.MANAGER,
        )
        self.equipment = Equipment.objects.create(name='Ball', category='sports')
        self.loan = EquipmentLoan.objects.create(
            user=self.member,
            equipment=self.equipment,
        )
        EquipmentLoan.objects.create(user=self.other_member, equipment=self.equipment)
        self.client.force_authenticate(user=self.member)

    def test_member_only_sees_own_loans_and_cannot_manage_inventory(self):
        loans_response = self.client.get('/api/equipment-loans/')
        inventory_response = self.client.post(
            '/api/equipment/',
            {'name': 'New ball', 'category': 'sports'},
            format='json',
        )

        self.assertEqual(loans_response.status_code, 200)
        self.assertEqual([item['id'] for item in loans_response.json()], [self.loan.id])
        self.assertEqual(inventory_response.status_code, 403)

    def test_manager_can_review_all_loans_and_manage_inventory(self):
        self.client.force_authenticate(user=self.manager)
        loans_response = self.client.get('/api/equipment-loans/')
        inventory_response = self.client.post(
            '/api/equipment/',
            {'name': 'New ball', 'category': 'sports'},
            format='json',
        )

        self.assertEqual(loans_response.status_code, 200)
        self.assertEqual(len(loans_response.json()), 2)
        self.assertEqual(inventory_response.status_code, 201)

    def test_loan_request_reserves_stock_and_starts_unpaid(self):
        response = self.client.post(
            '/api/equipment-loans/',
            {'equipment': self.equipment.id, 'quantity': 1},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.equipment.refresh_from_db()
        loan = EquipmentLoan.objects.order_by('-id').first()
        self.assertEqual(self.equipment.available_quantity, 0)
        self.assertEqual(loan.user, self.member)
        self.assertEqual(loan.status, EquipmentLoan.Status.PENDING)
        self.assertEqual(loan.deposit_status, EquipmentLoan.DepositStatus.UNPAID)

    def test_loan_request_cannot_exceed_available_stock(self):
        response = self.client.post(
            '/api/equipment-loans/',
            {'equipment': self.equipment.id, 'quantity': 2},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.equipment.refresh_from_db()
        self.assertEqual(self.equipment.available_quantity, 1)

    def test_only_manager_can_return_paid_loan_and_stock_is_restored(self):
        self.equipment.available_quantity = 0
        self.equipment.save(update_fields=['available_quantity'])
        self.loan.status = EquipmentLoan.Status.ACTIVE
        self.loan.deposit_status = EquipmentLoan.DepositStatus.PAID
        self.loan.save(update_fields=['status', 'deposit_status'])

        member_response = self.client.post(
            f'/api/equipment-loans/{self.loan.id}/return/',
            {'deposit_status': EquipmentLoan.DepositStatus.RETURNED},
            format='json',
        )
        self.client.force_authenticate(user=self.manager)
        manager_response = self.client.post(
            f'/api/equipment-loans/{self.loan.id}/return/',
            {'deposit_status': EquipmentLoan.DepositStatus.FORFEITED},
            format='json',
        )

        self.assertEqual(member_response.status_code, 403)
        self.assertEqual(manager_response.status_code, 200)
        self.loan.refresh_from_db()
        self.equipment.refresh_from_db()
        self.assertEqual(self.loan.status, EquipmentLoan.Status.RETURNED)
        self.assertEqual(self.loan.deposit_status, EquipmentLoan.DepositStatus.FORFEITED)
        self.assertIsNotNone(self.loan.return_date)
        self.assertEqual(self.equipment.available_quantity, 1)

    def test_unpaid_loan_cannot_be_returned(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(
            f'/api/equipment-loans/{self.loan.id}/return/',
            {'deposit_status': EquipmentLoan.DepositStatus.RETURNED},
            format='json',
        )

        self.assertEqual(response.status_code, 400)