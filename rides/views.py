from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Ride, RideRequest
from .serializers import RideSerializer
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from chat.models import ChatMessage
import logging

logger = logging.getLogger(__name__)


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
            ride = serializer.save(host=request.user)
            
            # Prepare system message for ride creation
            message_data = {
                "message": f"{request.user.first_name} {request.user.last_name} has created this ride from {ride.pickup_name} to {ride.destination_name}.",
                "First Name": "System",
                "Last Name": "",
                "timestamp": str(timezone.now()),
            }

            # Save the system message to the database
            ChatMessage.objects.create(
                ride=ride,
                user=request.user,  # User who triggered the action
                message_json=message_data
            )

            # Notify WebSocket group
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"chat_ride_{ride.id}",
                {
                    "type": "chat_message",
                    "message_data": message_data,
                }
            )

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

        # Prepare system message for ride joining
        message_data = {
            "message": f"{request.user.first_name} {request.user.last_name} has joined this ride",
            "First Name": "System",
            "Last Name": "",
            "timestamp": str(timezone.now()),
        }

        # Save the system message to the database
        ChatMessage.objects.create(
            ride=ride,
            user=request.user,
            message_json=message_data
        )

        # Notify WebSocket group
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_ride_{ride_id}",
            {
                "type": "chat_message",
                "message_data": message_data,
            }
        )

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

        # Prepare system message for ride joining
        message_data = {
            "message": f"{request.user.first_name} {request.user.last_name} has joined this ride",
            "First Name": "System",
            "Last Name": "",
            "timestamp": str(timezone.now()),
        }

        # Save the system message to the database
        ChatMessage.objects.create(
            ride=ride,
            user=request.user,
            message_json=message_data
        )

        # Notify WebSocket group
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_ride_{ride.id}",
            {
                "type": "chat_message",
                "message_data": message_data,
            }
        )

        return Response({"message": "Successfully joined the ride.", "ride": RideSerializer(ride).data}, status=status.HTTP_200_OK)



class DeleteRideView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, ride_id):
        ride = get_object_or_404(Ride, id=ride_id)
        
        # Check if the ride is completed first
        if ride.is_completed:
            return Response({"error": "Cannot delete a completed ride."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Check if the user is the host
        if ride.host != request.user:
            return Response({"error": "Only the host can delete this ride."}, status=status.HTTP_403_FORBIDDEN)
            
        # Check if there are members
        if ride.members.exists():
            return Response({"error": "Cannot delete ride with members."}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Deleting ride {ride_id}")
        ride.delete()
        logger.info(f"Ride {ride_id} deleted successfully")

        return Response({"message": "Ride deleted successfully."}, status=status.HTTP_200_OK)

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

        # Check if user is in the ride
        if not ride.members.filter(id=request.user.id).exists() and ride.host != request.user:
            return Response({"error": "You are not a member of this ride."}, status=status.HTTP_400_BAD_REQUEST)

        # Handle host leaving
        if ride.host == request.user:
            if not ride.members.exists():
                # If no members, delete the ride instead
                ride.delete()
                return Response({"message": "Ride deleted as it had no members."}, status=status.HTTP_200_OK)
            else:
                # Reassign host to the earliest joined member
                earliest_request = RideRequest.objects.filter(
                    ride=ride, 
                    is_approved=True
                ).order_by('requested_at').first()
                
                if earliest_request:
                    new_host = earliest_request.user
                    ride.host = new_host
                    ride.members.remove(new_host)  # Remove new host from members
                    ride.seats_available += 1  # Adjust seats as original host is leaving
                    
                    # Prepare system message for host change
                    message_data = {
                        "message": f"{request.user.first_name} {request.user.last_name} has left the ride. "
                                  f"{new_host.first_name} {new_host.last_name} is now the host.",
                        "First Name": "System",
                        "Last Name": "",
                        "timestamp": str(timezone.now()),
                    }
                else:
                    # This shouldn't happen due to members check, but as a fallback
                    return Response({"error": "Unable to reassign host."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # Regular member leaving
            ride.members.remove(request.user)
            ride.seats_available += 1
            RideRequest.objects.filter(ride=ride, user=request.user).delete()  # Clean up request
            
            # Prepare system message for member leaving
            message_data = {
                "message": f"{request.user.first_name} {request.user.last_name} has left the ride.",
                "First Name": "System",
                "Last Name": "",
                "timestamp": str(timezone.now()),
            }

        # Save changes to ride
        ride.save()

        # Save the system message to the database
        ChatMessage.objects.create(
            ride=ride,
            user=request.user,
            message_json=message_data
        )

        # Notify WebSocket group
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_ride_{ride_id}",
            {
                "type": "chat_message",
                "message_data": message_data,
            }
        )

        return Response({
            "message": "Successfully left the ride.",
            "ride": RideSerializer(ride).data
        }, status=status.HTTP_200_OK)


class RideDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, ride_id):
        """
        Retrieve detailed information about a specific ride by its ID.
        Only accessible to authenticated users who are either the host or a member of the ride,
        or if the ride is still active and has available seats (publicly visible).
        """
        ride = get_object_or_404(Ride, id=ride_id)
        
        # Check visibility permissions
        is_host = ride.host == request.user
        is_member = ride.members.filter(id=request.user.id).exists()
        is_public = not ride.is_completed and ride.seats_available > 0
        
        if not (is_host or is_member or is_public):
            return Response(
                {"error": "You don't have permission to view this ride's details."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # If the ride is female-only, restrict visibility to female users only (unless host/member)
        if ride.is_female_only and request.user.gender != 'Female' and not (is_host or is_member):
            return Response(
                {"error": "This ride is restricted to female users only."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = RideSerializer(ride)
        return Response(serializer.data, status=status.HTTP_200_OK)

class CurrentRidesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rides = Ride.objects.filter(members=request.user, is_completed=False)
        serializer = RideSerializer(rides, many=True)
        return Response(serializer.data)

class RideHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        hosted_rides = Ride.objects.filter(host=request.user, is_completed=True)
        member_rides = Ride.objects.filter(members=request.user, is_completed=True)
        all_rides = (hosted_rides | member_rides).distinct()
        serializer = RideSerializer(all_rides, many=True)
        return Response(serializer.data)
    
    
class CompleteRideView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ride_id):
        ride = get_object_or_404(Ride, id=ride_id)

        # Check if the user is the host
        if ride.host != request.user:
            return Response({"error": "Only the host can complete this ride."}, status=status.HTTP_403_FORBIDDEN)

        # Check if the ride is already completed
        if ride.is_completed:
            return Response({"error": "This ride is already completed."}, status=status.HTTP_400_BAD_REQUEST)

        # Mark the ride as completed
        ride.is_completed = True
        ride.save()

        # Prepare system message for ride completion
        message_data = {
            "message": f"{request.user.first_name} {request.user.last_name} has marked this ride as completed.",
            "First Name": "System",
            "Last Name": "",
            "timestamp": str(timezone.now()),
        }

        # Save the system message to the database
        ChatMessage.objects.create(
            ride=ride,
            user=request.user,
            message_json=message_data
        )

        # Notify WebSocket group
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_ride_{ride_id}",
            {
                "type": "chat_message",
                "message_data": message_data,
            }
        )

        return Response({
            "message": "Ride marked as completed successfully.",
            "ride": RideSerializer(ride).data
        }, status=status.HTTP_200_OK)