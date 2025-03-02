from rest_framework import serializers
from .models import User

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'gender', 'student_id', 'phone_number', 'profile_photo', 'password']

    def validate_email(self, value):
        if not value.endswith('@northsouth.edu'):
            raise serializers.ValidationError("Email must be an NSU email (@northsouth.edu)")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            gender=validated_data['gender'],
            student_id=validated_data['student_id'],
            phone_number=validated_data.get('phone_number', ''),
            password=validated_data['password']
        )
        if 'profile_photo' in validated_data:
            user.profile_photo = validated_data['profile_photo']
            user.save()
        return user

class UserLoginSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password']

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'gender', 'student_id', 'phone_number', 'profile_photo']
        read_only_fields = ['email', 'student_id']