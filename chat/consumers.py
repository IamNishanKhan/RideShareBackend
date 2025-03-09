import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatMessage
from rides.models import Ride
from django.core.exceptions import ObjectDoesNotExist
import logging
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)

class RideChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.ride_id = self.scope['url_route']['kwargs']['ride_id']
        self.room_group_name = f"chat_ride_{self.ride_id}"

        logger.info(f"Attempting connection to ride {self.ride_id}")
        user = await self.get_user_from_token()
        self.scope['user'] = user
        logger.info(f"Authenticated user: {user} (Anonymous: {isinstance(user, AnonymousUser)})")

        if isinstance(user, AnonymousUser) or not await self.is_user_in_ride(user, self.ride_id):
            logger.warning(f"Access denied for user {user} to ride {self.ride_id}")
            await self.close(code=4403)
            return

        logger.info(f"User {user} connected to {self.room_group_name}")
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Send all previous messages to the user upon connection
        previous_messages = await self.get_previous_messages()
        for message in previous_messages:
            await self.send(text_data=json.dumps(message))

    async def disconnect(self, close_code):
        logger.info(f"Disconnecting from {self.room_group_name} with code {close_code}")
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        logger.info(f"Received raw data: '{text_data}'")
        user = self.scope['user']

        # Revalidate membership before processing the message
        if not await self.is_user_in_ride(user, self.ride_id):
            logger.warning(f"User {user} is no longer in ride {self.ride_id}, closing connection")
            await self.close(code=4403)
            return

        try:
            text_data_json = json.loads(text_data)
            message = text_data_json['message']

            # Prepare the full message JSON
            message_data = {
                'message': message,
                'First Name': user.first_name,
                'Last Name': user.last_name,
                'timestamp': str(await self.get_current_time()),
            }

            # Save the full message JSON to the database
            await self.save_message(user, self.ride_id, message_data)

            # Broadcast the message to the group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_data': message_data,
                }
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {str(e)}")
            message = text_data if text_data else ""
            if not message:
                await self.send(text_data=json.dumps({"error": "Empty message received"}))
                return
            message_data = {
                'message': message,
                'First Name': user.first_name,
                'Last Name': user.last_name,
                'timestamp': str(await self.get_current_time()),
            }
            await self.save_message(user, self.ride_id, message_data)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_data': message_data,
                }
            )

    async def chat_message(self, event):
        # Handle the message payload safely
        message_data = event.get('message_data', {})
        if not message_data or 'message' not in message_data:
            logger.error(f"Invalid message_data in event: {event}")
            await self.send(text_data=json.dumps({
                "message": "System error: Invalid message format received.",
                "First Name": "System",
                "Last Name": "",
                "timestamp": str(await self.get_current_time())
            }))
            return
        await self.send(text_data=json.dumps(message_data))

    async def user_leave(self, event):
        # This handler is kept for future use if we implement channel-specific disconnects
        logger.info(f"User leave event received for ride {self.ride_id}, but no action taken due to scope issue")
        # Note: This won't be triggered directly from the view anymore

    @database_sync_to_async
    def get_user_from_token(self):
        try:
            auth = JWTAuthentication()
            headers = {key.decode(): value.decode() for key, value in self.scope['headers']}
            token = headers.get('authorization', '').replace('Bearer ', '')
            validated_token = auth.get_validated_token(token)
            return auth.get_user(validated_token)
        except Exception as e:
            logger.error(f"Token authentication failed: {str(e)}")
            return AnonymousUser()

    @database_sync_to_async
    def is_user_in_ride(self, user, ride_id):
        try:
            ride = Ride.objects.get(id=ride_id)
            is_member = user == ride.host or user in ride.members.all()
            logger.info(f"Checking if {user} is in ride {ride_id}: {is_member}")
            return is_member
        except ObjectDoesNotExist:
            logger.error(f"Ride {ride_id} does not exist")
            return False

    @database_sync_to_async
    def save_message(self, user, ride_id, message_data):
        ride = Ride.objects.get(id=ride_id)
        ChatMessage.objects.create(ride=ride, user=user, message_json=message_data)

    @database_sync_to_async
    def get_previous_messages(self):
        try:
            ride = Ride.objects.get(id=self.ride_id)
            messages = ChatMessage.objects.filter(ride=ride).order_by('timestamp')
            return [msg.message_json for msg in messages]
        except ObjectDoesNotExist:
            logger.error(f"Ride {self.ride_id} does not exist")
            return []

    @database_sync_to_async
    def get_current_time(self):
        from django.utils import timezone
        return timezone.now()