from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Review, Badge
from .serializers import ReviewSerializer, BadgeSerializer, SimplifiedUserSerializer
from django.shortcuts import get_object_or_404
from users.models import User
from rides.models import Ride

class CreateReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            ride_id = request.data.get('ride_id')
            reviewed_user_id = request.data.get('reviewed_user_id')
            rating = request.data.get('rating')
            comment = request.data.get('comment', '')

            if not all([ride_id, reviewed_user_id, rating]):
                return Response({"error": "ride_id, reviewed_user_id, and rating are required."}, status=status.HTTP_400_BAD_REQUEST)

            ride = get_object_or_404(Ride, id=ride_id)
            reviewed_user = get_object_or_404(User, id=reviewed_user_id)

            if not ride.is_completed:
                return Response({"error": "You cannot review yet because the ride is not completed."}, status=status.HTTP_400_BAD_REQUEST)

            review_data = {
                'reviewer': request.user,
                'reviewed_user': reviewed_user,
                'ride': ride,
                'rating': rating,
                'comment': comment
            }

            serializer = ReviewSerializer(data=review_data)
            if serializer.is_valid():
                review = serializer.save(reviewer=request.user, ride=ride, reviewed_user=reviewed_user)
                
                badge, created = Badge.objects.get_or_create(user=reviewed_user)
                badge.update_badge()

                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserReviewsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            user = get_object_or_404(User, id=user_id)
            reviews = Review.objects.filter(reviewed_user=user)
            review_serializer = ReviewSerializer(reviews, many=True)
            badge = Badge.objects.filter(user=user).first()
            badge_data = BadgeSerializer(badge).data if badge else {"level": "None", "average_rating": 0}
            user_serializer = SimplifiedUserSerializer(user)

            return Response({
                "user": user_serializer.data,
                "reviews": review_serializer.data,
                "badge": badge_data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Failed to retrieve reviews: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)