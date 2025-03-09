from django.shortcuts import render, get_object_or_404
from rides.models import Ride
from .models import ChatMessage
from django.contrib.auth.decorators import login_required

@login_required
def chat_room(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id)
    if request.user != ride.host and request.user not in ride.members.all():
        return render(request, 'chat/error.html', {'message': 'You are not part of this ride.'})

    messages = ChatMessage.objects.filter(ride=ride).order_by('timestamp')
    return render(request, 'chat/room.html', {
        'ride': ride,
        'messages': messages,
    })