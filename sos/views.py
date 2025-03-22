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
            
            # If no notified_users are provided, use the user's emergency contacts
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
        queryset = User.objects.all().exclude(id=self.request.user.id)  # Exclude the current user
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
        # List all emergency contacts for the current user
        contacts = EmergencyContact.objects.filter(user=request.user)
        serializer = EmergencyContactSerializer(contacts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        # Add a new emergency contact
        serializer = EmergencyContactSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            contact_user = serializer.validated_data['contact']
            # Check if the user is trying to add themselves
            if contact_user == request.user:
                return Response(
                    {"error": "You cannot add yourself as an emergency contact."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Check if the contact is already added
            if EmergencyContact.objects.filter(user=request.user, contact=contact_user).exists():
                return Response(
                    {"error": "This user is already an emergency contact."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
