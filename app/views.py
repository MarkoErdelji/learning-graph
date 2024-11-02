# your_app_name/views.py
from rest_framework import generics
from .models import Book, AppUser
from .serializers import BookSerializer, CustomTokenObtainPairSerializer, UserSerializer
from rest_framework.permissions import IsAuthenticated
from .permissions import IsTeacher, IsExpert, IsStudent
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    
class BookList(generics.ListCreateAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsAuthenticated]  

class UserRegistrationView(generics.CreateAPIView):
    queryset = AppUser.objects.all()
    serializer_class = UserSerializer

class TeacherView(APIView):
    permission_classes = [IsTeacher]  

    def get(self, request):
        return Response({'message': 'This view is accessible only to teachers.'})

class ExpertView(APIView):
    permission_classes = [IsExpert]  

    def get(self, request):
        return Response({'message': 'This view is accessible only to experts.'})

class StudentView(APIView):
    permission_classes = [IsStudent]  

    def get(self, request):
        return Response({'message': 'This view is accessible only to students.'})