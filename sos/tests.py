from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import SOSAlert, EmergencyContact
from .serializers import SOSAlertSerializer
from users.models import User
from django.utils import timezone
from unittest.mock import patch

User = get_user_model()

class SOSBackendTests(APITestCase):
    def setUp(self):
        # Set up the API client
        self.client = APIClient()

        # Create test users
        self.user1 = User.objects.create_user(
            email='user1@northsouth.edu',
            first_name='John',
            last_name='Doe',
            phone_number='+1234567890',
            gender='M',
            student_id='123456',
            latitude=40.7128,  # New York coordinates
            longitude=-74.0060,
            expo_push_token='ExponentPushToken[abc123]',
            password='password123'
        )
        self.user2 = User.objects.create_user(
            email='user2@northsouth.edu',
            first_name='Jane',
            last_name='Smith',
            phone_number='+1234567891',
            gender='F',
            student_id='123457',
            latitude=40.7129,  # Nearby user
            longitude=-74.0061,
            expo_push_token='ExponentPushToken[def456]',
            password='password123'
        )
        self.user3 = User.objects.create_user(
            email='user3@northsouth.edu',
            first_name='Alice',
            last_name='Johnson',
            phone_number='+1234567892',
            gender='F',
            student_id='123458',
            latitude=34.0522,  # Far away user (Los Angeles)
            longitude=-118.2437,
            expo_push_token='ExponentPushToken[ghi789]',
            password='password123'
        )

        # Authenticate user1
        self.client.force_authenticate(user=self.user1)

    # Mock the get_nearby_users method to simulate nearby users
    def mock_get_nearby_users(self, latitude, longitude, radius_km=5):
        # Simulate that user2 is nearby and user3 is not
        nearby_users = User.objects.filter(id=self.user2.id)  # Only user2 is nearby
        return nearby_users

    # Test SOS Alert Creation
    @patch('sos.serializers.SOSAlertSerializer.get_nearby_users')
    @patch('requests.post')  # Mock Expo notifications
    def test_create_sos_alert_success(self, mock_post, mock_get_nearby_users):
        # Mock the get_nearby_users method
        mock_get_nearby_users.side_effect = self.mock_get_nearby_users
        # Mock the Expo notification response
        mock_post.return_value.status_code = 200

        url = reverse('create-sos')
        data = {
            'latitude': 40.7128,
            'longitude': -74.0060,
            'is_community_alert': False
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SOSAlert.objects.count(), 1)
        sos_alert = SOSAlert.objects.first()
        self.assertEqual(sos_alert.user, self.user1)
        self.assertEqual(sos_alert.latitude, 40.7128)
        self.assertEqual(sos_alert.longitude, -74.0060)
        # Check that user2 (mocked as nearby) is notified, but user3 (far away) is not
        self.assertIn(self.user2, sos_alert.notified_users.all())
        self.assertNotIn(self.user3, sos_alert.notified_users.all())

    def test_create_sos_alert_missing_location(self):
        url = reverse('create-sos')
        data = {
            'latitude': None,
            'longitude': None,
            'is_community_alert': False
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Latitude and longitude are required.', str(response.data))

    # Test Emergency Contact Management
    def test_list_emergency_contacts(self):
        # Add user2 as an emergency contact for user1
        EmergencyContact.objects.create(user=self.user1, contact=self.user2)
        url = reverse('emergency-contacts')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['contact']['email'], 'user2@northsouth.edu')

    def test_add_emergency_contact_success(self):
        url = reverse('emergency-contacts')
        data = {
            'contact_id': self.user2.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(EmergencyContact.objects.count(), 1)
        contact = EmergencyContact.objects.first()
        self.assertEqual(contact.user, self.user1)
        self.assertEqual(contact.contact, self.user2)

    def test_add_emergency_contact_duplicate(self):
        # Add user2 as an emergency contact for user1
        EmergencyContact.objects.create(user=self.user1, contact=self.user2)
        url = reverse('emergency-contacts')
        data = {
            'contact_id': self.user2.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('This user is already an emergency contact.', str(response.data))

    def test_add_emergency_contact_self(self):
        url = reverse('emergency-contacts')
        data = {
            'contact_id': self.user1.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('You cannot add yourself as an emergency contact.', str(response.data))

    # Test User Search
    def test_search_users(self):
        url = reverse('user-list') + '?search=jane'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['email'], 'user2@northsouth.edu')

    def test_search_users_exclude_self(self):
        url = reverse('user-list') + '?search=john'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)  # user1 (John) should be excluded

    # Test SOS Alert with Emergency Contacts
    @patch('sos.serializers.SOSAlertSerializer.get_nearby_users')
    @patch('requests.post')  # Mock Expo notifications
    def test_sos_alert_notifies_emergency_contacts(self, mock_post, mock_get_nearby_users):
        # Mock the get_nearby_users method
        mock_get_nearby_users.side_effect = self.mock_get_nearby_users
        # Mock the Expo notification response
        mock_post.return_value.status_code = 200

        # Add user2 as an emergency contact for user1
        EmergencyContact.objects.create(user=self.user1, contact=self.user2)
        url = reverse('create-sos')
        data = {
            'latitude': 40.7128,
            'longitude': -74.0060,
            'is_community_alert': False
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        sos_alert = SOSAlert.objects.first()
        # user2 should be notified because they are an emergency contact
        self.assertIn(self.user2, sos_alert.notified_users.all())
        # user3 should not be notified (mocked as not nearby)
        self.assertNotIn(self.user3, sos_alert.notified_users.all())