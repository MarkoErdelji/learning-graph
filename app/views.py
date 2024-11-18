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
import logging
logger = logging.getLogger(__name__)

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
    
    @action(detail=True, methods=['patch'])
    def update_with_prerequisites(self, request, pk=None):
        logger.debug(f"Request data: {request.data}")
        target_node = get_object_or_404(GraphNode, pk=pk)
        logger.debug(f"Target node: {target_node}")

        prerequisite_node_ids = request.data.get("prerequisite_node_ids", [])
        logger.debug(f"Prerequisite IDs: {prerequisite_node_ids}")

        if not isinstance(prerequisite_node_ids, list):
            logger.error("prerequisite_node_ids is not a list")
            return Response(
                {"error": "prerequisite_node_ids must be a list of IDs."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        prerequisite_nodes = GraphNode.objects.filter(id__in=prerequisite_node_ids)
        logger.debug(f"Found prerequisite nodes: {list(prerequisite_nodes)}")

        if prerequisite_nodes.count() != len(prerequisite_node_ids):
            logger.error("Some prerequisite nodes do not exist.")
            return Response(
                {"error": "Some prerequisite nodes do not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Add new prerequisites
        target_node.prerequisite_nodes.add(*prerequisite_nodes)
        logger.debug(f"Prerequisites after adding: {list(target_node.prerequisite_nodes.all())}")

        # Update other fields if provided
        title = request.data.get("title")
        if title:
            target_node.title = title

        target_node.save()

        return Response(
            GraphNodeSerializer(target_node).data,
            status=status.HTTP_200_OK
        )

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

    @action(detail=True, methods=['patch'])
    def update_question(self, request, pk=None):
        """Update a question."""
        question = get_object_or_404(Question, pk=pk)
        text = request.data.get('text', None)
        correct_answer = request.data.get('correct_answer', None)
        other_answers = request.data.get('other_answers', None)

        if text:
            question.text = text
        if correct_answer:
            question.correct_answer = correct_answer
        if other_answers is not None:
            question.other_answers = other_answers

        question.save()

        return Response(QuestionSerializer(question).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'])
    def delete_question(self, request, pk=None):
        """Delete a question."""
        question = get_object_or_404(Question, pk=pk)
        question.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
