from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Ride, RideRequest
from .serializers import RideSerializer, RideRequestSerializer
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone

class CreateRideView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if Ride.objects.filter(host=request.user, is_completed=False).exists():
            return Response({"error": "You cannot create a new ride while hosting an active ride."}, status=status.HTTP_400_BAD_REQUEST)
        if Ride.objects.filter(members=request.user, is_completed=False).exists():
            return Response({"error": "You cannot create a ride while you are a member of an active ride."}, status=status.HTTP_400_BAD_REQUEST)
        if request.data.get('is_female_only', False) and request.user.gender != 'Female':
            return Response({"error": "Male users cannot create female-only ride groups."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = RideSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(host=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class JoinRideByIdView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ride_id):
        ride = get_object_or_404(Ride, id=ride_id)

        if ride.is_completed:
            return Response({"error": "This ride is already completed."}, status=status.HTTP_400_BAD_REQUEST)
        if ride.seats_available <= 0:
            return Response({"error": "This ride is full."}, status=status.HTTP_400_BAD_REQUEST)
        if ride.members.filter(id=request.user.id).exists() or ride.host == request.user:
            return Response({"error": "You are already a member of this ride."}, status=status.HTTP_400_BAD_REQUEST)
        if RideRequest.objects.filter(ride=ride, user=request.user).exists():
            return Response({"error": "You have already requested to join this ride."}, status=status.HTTP_400_BAD_REQUEST)

        ride_request = RideRequest(ride=ride, user=request.user)
        ride_request.save()
        ride_request.is_approved = True
        ride_request.save()
        ride.members.add(request.user)
        ride.seats_available -= 1
        ride.save()

        return Response({"message": "Successfully joined the ride.", "ride": RideSerializer(ride).data}, status=status.HTTP_200_OK)

class JoinRideByCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ride_code = request.data.get('ride_code')
        if not ride_code:
            return Response({"error": "Ride code is required."}, status=status.HTTP_400_BAD_REQUEST)

        ride = get_object_or_404(Ride, ride_code=ride_code)

        if ride.is_completed:
            return Response({"error": "This ride is already completed."}, status=status.HTTP_400_BAD_REQUEST)
        if ride.seats_available <= 0:
            return Response({"error": "This ride is full. The code is no longer valid."}, status=status.HTTP_400_BAD_REQUEST)
        if ride.members.filter(id=request.user.id).exists() or ride.host == request.user:
            return Response({"error": "You are already a member of this ride."}, status=status.HTTP_400_BAD_REQUEST)
        if RideRequest.objects.filter(ride=ride, user=request.user).exists():
            return Response({"error": "You have already requested to join this ride."}, status=status.HTTP_400_BAD_REQUEST)

        ride_request = RideRequest(ride=ride, user=request.user)
        ride_request.save()
        ride_request.is_approved = True
        ride_request.save()
        ride.members.add(request.user)
        ride.seats_available -= 1
        ride.save()

        return Response({"message": "Successfully joined the ride.", "ride": RideSerializer(ride).data}, status=status.HTTP_200_OK)

class DeleteRideView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, ride_id):
        ride = get_object_or_404(Ride, id=ride_id)
        if ride.host != request.user:
            return Response({"error": "Only the host can delete this ride."}, status=status.HTTP_403_FORBIDDEN)
        if ride.members.exists():
            return Response({"error": "Cannot delete ride with members."}, status=status.HTTP_400_BAD_REQUEST)
        ride.delete()
        return Response({"message": "Ride deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

class ListRidesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rides = Ride.objects.filter(seats_available__gt=0, is_completed=False)
        if request.user.gender != 'Female':
            rides = rides.exclude(is_female_only=True)
        serializer = RideSerializer(rides, many=True)
        return Response(serializer.data)

class LeaveRideView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ride_id):
        ride = get_object_or_404(Ride, id=ride_id)

        if ride.is_completed:
            return Response({"error": "Cannot leave a completed ride."}, status=status.HTTP_400_BAD_REQUEST)
        if ride.host == request.user:
            return Response({"error": "Host cannot leave their own ride. Delete the ride instead."}, status=status.HTTP_400_BAD_REQUEST)
        if not ride.members.filter(id=request.user.id).exists():
            return Response({"error": "You are not a member of this ride."}, status=status.HTTP_400_BAD_REQUEST)

        ride.members.remove(request.user)
        ride.seats_available += 1
        RideRequest.objects.filter(ride=ride, user=request.user).delete()  # Clean up request
        ride.save()

        # Notify WebSocket group that the user has left
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_ride_{ride_id}",
            {
                "type": "chat_message",
                "message": f"{request.user.first_name} {request.user.last_name} has left the ride.",
                "username": "System",
                "timestamp": str(timezone.now())
            }
        )

        return Response({"message": "Successfully left the ride.", "ride": RideSerializer(ride).data}, status=status.HTTP_200_OK)

class CurrentRidesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rides = Ride.objects.filter(members=request.user, is_completed=False)
        serializer = RideSerializer(rides, many=True)
        return Response(serializer.data)

class RideHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Rides where user was host or member, and are completed
        hosted_rides = Ride.objects.filter(host=request.user, is_completed=True)
        member_rides = Ride.objects.filter(members=request.user, is_completed=True)
        all_rides = (hosted_rides | member_rides).distinct()
        serializer = RideSerializer(all_rides, many=True)
        return Response(serializer.data)