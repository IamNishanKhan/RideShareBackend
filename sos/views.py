# sos/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, generics
from .models import SOSAlert
from .serializers import SOSAlertSerializer, UserSerializer
from users.models import User
from django.contrib.auth import get_user_model

User = get_user_model()

class CreateSOSAlertView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SOSAlertSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            sos_alert = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ActiveSOSAlertsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        active_alerts = SOSAlert.objects.filter(status='active').exclude(user=request.user)
        serializer = SOSAlertSerializer(active_alerts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class UserListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = User.objects.all()
    serializer_class = UserSerializer