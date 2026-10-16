from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Notification, User


class NotificationPermissionTests(TestCase):
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
        self.notification = Notification.objects.create(
            user=self.member,
            title='Booking update',
            message='Your booking is pending.',
        )
        Notification.objects.create(
            user=self.other_member,
            title='Private update',
            message='Another member notification.',
        )
        self.client.force_authenticate(user=self.member)

    def test_member_sees_own_notifications_and_can_only_mark_read(self):
        list_response = self.client.get('/api/notifications/')
        update_response = self.client.patch(
            f'/api/notifications/{self.notification.id}/',
            {'is_read': True, 'message': 'Changed by member'},
            format='json',
        )
        create_response = self.client.post(
            '/api/notifications/',
            {
                'user': self.other_member.id,
                'title': 'Spoofed',
                'message': 'Member-created message',
            },
            format='json',
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual([item['id'] for item in list_response.json()], [self.notification.id])
        self.assertEqual(update_response.status_code, 200)
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)
        self.assertEqual(self.notification.message, 'Your booking is pending.')
        self.assertEqual(create_response.status_code, 403)