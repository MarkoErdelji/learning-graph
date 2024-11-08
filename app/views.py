# your_app_name/views.py
import random
from django.shortcuts import get_object_or_404
from rest_framework import generics, viewsets, status
from .models import AppUser, KnowledgeGraph, GraphNode, Question
from .serializers import (
    CustomTokenObtainPairSerializer, UserSerializer,
    KnowledgeGraphSerializer, GraphNodeSerializer, QuestionSerializer
)
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

    @action(detail=False, methods=['get'])
    def list_graphs(self, request):
        """Lists all knowledge graphs."""
        graphs = KnowledgeGraph.objects.all()
        serializer = self.get_serializer(graphs, many=True)
        return Response(serializer.data)


class GraphNodeViewSet(viewsets.ModelViewSet):
    serializer_class = GraphNodeSerializer
    queryset = GraphNode.objects.all()

    def create(self, request, *args, **kwargs):
        """Create a new node."""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            node = serializer.save()
            return Response(GraphNodeSerializer(node).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'])
    def update_node(self, request, pk=None):
        """Update the title of a node."""
        node = get_object_or_404(GraphNode, pk=pk)
        new_title = request.data.get("title")
        if new_title:
            node.title = new_title
            node.save()
            return Response(GraphNodeSerializer(node).data, status=status.HTTP_200_OK)
        return Response({"error": "No title provided"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'])
    def delete_node(self, request, pk=None):
        """Delete a node."""
        try:
            node = GraphNode.objects.get(pk=pk)
            node.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except GraphNode.DoesNotExist:
            return Response({"error": "Node not found"}, status=status.HTTP_404_NOT_FOUND)


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


class KnowledgeGraphDetailView(APIView):
    def get(self, request, pk):
        """Retrieve a specific knowledge graph with D3.js structure."""
        graph = get_object_or_404(KnowledgeGraph, pk=pk)
        serializer = KnowledgeGraphSerializer(graph)

        # Structure data for D3.js
        d3_data = {
            "nodes": [],
            "links": []
        }

        node_mapping = {}

        # Add nodes to d3_data
        for idx, node_data in enumerate(serializer.data['nodes']):
            node = {
                "id": node_data['id'],
                "title": node_data['title'],
                "questions": node_data['questions']
            }
            d3_data["nodes"].append(node)
            node_mapping[node_data['id']] = idx

        # Add links based on prerequisites
        for node_data in serializer.data['nodes']:
            source_id = node_data['id']  # This will be the actual node id
            for prerequisite_id in node_data['prerequisite_nodes']:
                target_id = prerequisite_id  # This is the id of the prerequisite node
                link = {
                    "source": source_id,  # Use node ids, not indices
                    "target": target_id
                }
                d3_data["links"].append(link)

        return Response(d3_data)
