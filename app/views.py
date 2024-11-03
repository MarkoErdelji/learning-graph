# your_app_name/views.py
import random
from rest_framework import generics,viewsets
from .models import AppUser,KnowledgeGraph, GraphNode, Question
from .serializers import CustomTokenObtainPairSerializer, UserSerializer,KnowledgeGraphSerializer, GraphNodeSerializer, QuestionSerializer
from rest_framework.permissions import IsAuthenticated
from .permissions import IsTeacher, IsExpert, IsStudent
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import action


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


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
    
class KnowledgeGraphViewSet(viewsets.ModelViewSet):
    queryset = KnowledgeGraph.objects.all()
    serializer_class = KnowledgeGraphSerializer

class GraphNodeViewSet(viewsets.ModelViewSet):
    queryset = GraphNode.objects.all()
    serializer_class = GraphNodeSerializer

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

class FirstQuestionView(APIView):
    def get(self, request):
        try:
            question = Question.objects.get(id=1)
            serializer = QuestionSerializer(question)
            data = serializer.data

            correct_answer = str(data['correct_answer'])
            other_answers = list(map(str, data['other_answers']))
            all_answers = other_answers + [correct_answer]
            random.shuffle(all_answers)

            data['other_answers'] = all_answers
            data.pop('correct_answer')
            
            return Response(data)
        
        except Question.DoesNotExist:
            return Response({'error': 'Question with id=1 does not exist.'}, status=404)