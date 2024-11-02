# your_app_name/serializers.py
from rest_framework import serializers
from .models import Book,AppUser
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppUser
        fields = ['username', 'password', 'email', 'first_name', 'last_name', 'user_type'] 
        extra_kwargs = {
            'password': {'write_only': True}  # Ensure password is write-only
        }

    def create(self, validated_data):
        user = AppUser(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user
    
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Ensure that the user is an instance of AppUser
        if isinstance(user, AppUser):
            token['user_type'] = user.user_type  # Access user_type from AppUser
        else:
            token['user_type'] = 'admin'
        return token
