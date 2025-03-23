# sos/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, generics
from .models import SOSAlert, EmergencyContact
from .serializers import SOSAlertSerializer, UserSerializer, EmergencyContactSerializer
from users.models import User
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

class CreateSOSAlertView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SOSAlertSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            sos_alert = serializer.save()
            
            if not sos_alert.notified_users.exists() and not sos_alert.is_community_alert:
                emergency_contacts = EmergencyContact.objects.filter(user=request.user)
                if emergency_contacts.exists():
                    notified_users = [ec.contact for ec in emergency_contacts]
                    sos_alert.notified_users.set(notified_users)
                    sos_alert.save()
                else:
                    return Response(
                        {"error": "No emergency contacts found to notify."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            response_data = serializer.data
            response_data['notification_status'] = f"Notifications sent to {sos_alert.notified_users.count()} users"
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ActiveSOSAlertsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        active_alerts = SOSAlert.objects.filter(status='active').exclude(user=request.user)
        serializer = SOSAlertSerializer(active_alerts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class UserListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_queryset(self):
        queryset = User.objects.all().exclude(id=self.request.user.id)
        search_query = self.request.query_params.get('search', None)
        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        return queryset

class EmergencyContactView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        contacts = EmergencyContact.objects.filter(user=request.user)
        serializer = EmergencyContactSerializer(contacts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = EmergencyContactSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            contact_user = serializer.validated_data['contact']
            if contact_user == request.user:
                return Response(
                    {"error": "You cannot add yourself as an emergency contact."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if EmergencyContact.objects.filter(user=request.user, contact=contact_user).exists():
                return Response(
                    {"error": "This user is already an emergency contact."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        contact_id = request.data.get('contact_id')
        if not contact_id:
            return Response(
                {"error": "Contact ID is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            emergency_contact = EmergencyContact.objects.get(user=request.user, id=contact_id)
            emergency_contact.delete()
            return Response({"message": "Emergency contact removed successfully."}, status=status.HTTP_200_OK)
        except EmergencyContact.DoesNotExist:
            return Response(
                {"error": "Emergency contact not found."},
                status=status.HTTP_404_NOT_FOUND
            )

class UserSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        data = request.data

        user.sound_enabled = data.get('sound_enabled', user.sound_enabled)
        user.location_enabled = data.get('location_enabled', user.location_enabled)
        user.notifications_enabled = data.get('notifications_enabled', user.notifications_enabled)
        user.vibration_enabled = data.get('vibration_enabled', user.vibration_enabled)
        user.emergency_message = data.get('emergency_message', user.emergency_message)
        user.save()

        return Response({"message": "Settings updated successfully"}, status=status.HTTP_200_OK)