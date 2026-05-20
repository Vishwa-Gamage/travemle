from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Destination, TripPlan, UserProfile


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password2 = serializers.CharField(write_only=True, label='Confirm Password')

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2']

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        if User.objects.filter(email=data.get('email', '')).exists():
            raise serializers.ValidationError({'email': 'Email already in use.'})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
        )
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['default_budget', 'default_travel_mode', 'interests_csv',
                  'food_preferences', 'accommodation_preferences', 'activity_preferences']


# QUAL-02: Dedicated serializer for PUT /api/auth/me/ with proper field
# validation. Previously MeView.put did bare manual extraction which caused
# unhandled server exceptions on invalid input (e.g. budget="abc").
class ProfileUpdateSerializer(serializers.Serializer):
    default_budget = serializers.IntegerField(
        min_value=0,
        max_value=10_000_000,
        error_messages={
            'min_value': 'Budget cannot be negative.',
            'max_value': 'Budget value is unrealistically large.',
            'invalid':   'Budget must be a whole number.',
        },
    )
    default_travel_mode = serializers.ChoiceField(
        choices=['Car', 'Bus', 'Train'],
        error_messages={'invalid_choice': 'Travel mode must be Car, Bus, or Train.'},
    )
    interests_csv = serializers.CharField(
        max_length=500,
        allow_blank=True,
        required=False,
        default='',
    )
    food_preferences = serializers.CharField(
        max_length=500,
        allow_blank=True,
        required=False,
        default='',
    )
    accommodation_preferences = serializers.CharField(
        max_length=500,
        allow_blank=True,
        required=False,
        default='',
    )
    activity_preferences = serializers.CharField(
        max_length=500,
        allow_blank=True,
        required=False,
        default='',
    )


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'profile']


class DestinationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Destination
        fields = ['id', 'name', 'country', 'description', 'image_url',
                  'category', 'lat', 'lon', 'is_featured']


class TripPlanSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    duration_days = serializers.SerializerMethodField()

    class Meta:
        model = TripPlan
        fields = [
            'id', 'user', 'origin', 'destination_city', 'destination_country',
            'start_date', 'end_date', 'interests',
            'food_preferences', 'accommodation_preferences', 'activity_preferences',
            'budget', 'travel_mode',
            'plan_json', 'weather_summary', 'map_url', 'created_at', 'duration_days'
        ]
        read_only_fields = ['user', 'created_at']

    def get_duration_days(self, obj):
        return (obj.end_date - obj.start_date).days + 1
