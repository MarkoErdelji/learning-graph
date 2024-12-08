# your_app_name/views.py
from collections import deque
import random
from django.shortcuts import get_object_or_404
from rest_framework import generics, viewsets, status, permissions
from .models import AppUser, KnowledgeGraph, GraphNode, Question, Test, TestAttempt
from .serializers import (
    CustomTokenObtainPairSerializer, UserSerializer,
    KnowledgeGraphSerializer, GraphNodeSerializer, QuestionSerializer,TestSerializer, TestAttemptSerializer
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

        for prerequisite_node in prerequisite_nodes:
            prerequisite_node.prerequisite_nodes.add(target_node)
            logger.debug(f"Added {target_node} as prerequisite to {prerequisite_node}")

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
                    "source": target_id,  # Use node ids, not indices
                    "target": source_id
                }   
                d3_data["links"].append(link)

        return Response(d3_data)


class TestListView(APIView):

    def get(self, request):
        tests = Test.objects.all()
        serializer = TestSerializer(tests, many=True)
        return Response(serializer.data)


class TestCreationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        graph_id = request.data.get('graph_id')
        question_ids = request.data.get('question_ids', [])
        graph_id = int(graph_id)  
        graph = get_object_or_404(KnowledgeGraph, pk=graph_id)

        questions = Question.objects.filter(id__in=question_ids)
        
        node_depths = {}
        
        def calculate_node_depth(node, node_depths):
            if node.id in node_depths:
                return node_depths[node.id]

            logger.debug(f"Calculating depth for node: {node.title} (ID: {node.id})")
            logger.debug(f"Prerequisites: {[prereq.title for prereq in node.prerequisite_nodes.all()]}")

            if node.prerequisite_nodes.count() == 0:
                node_depths[node.id] = 0
                logger.debug(f"Node {node.title} has no prerequisites. Depth = 0.")
                return 0

            # Initialize max_depth to a small value
            max_depth = -1  # or you can use 0, depending on your requirement

            for prerequisite in node.prerequisite_nodes.all():
                prerequisite_depth = calculate_node_depth(prerequisite, node_depths)
                logger.debug(f"Prerequisite {prerequisite.title} (ID: {prerequisite.id}) has depth {prerequisite_depth}.")
                max_depth = max(max_depth, prerequisite_depth + 1)

            node_depths[node.id] = max_depth
            logger.debug(f"Node {node.title} has calculated depth {max_depth}.")
            return max_depth

        question_depths = {}
        node_depths = {} 
        for question in questions:
            node = question.node
            depth = calculate_node_depth(node, node_depths)
            logger.debug(f"Node {node.title} (ID: {node.id}) has depth {depth}.")
            question_depths[question] = depth

        sorted_questions = sorted(question_depths.items(), key=lambda x: x[1])

        test = Test.objects.create(
            graph=graph,
            title=f"Test for {graph.title}",
            author=request.user
        )

        for question, _ in sorted_questions:
            test.questions.add(question)

        return Response({"test_id": test.id}, status=status.HTTP_201_CREATED)

    def calculate_graph_depth(self, graph):
        # This function calculates the depth for all nodes in the graph using BFS (starting from leaf nodes)
        node_depths = {}

        # Initialize a queue for BFS
        queue = deque()

        # Step 1: Identify leaf nodes (nodes without prerequisites) and start the BFS from them
        for node in graph.nodes.all():
            if node.prerequisite_nodes.count() == 0:
                node_depths[node.id] = 0  # Leaf node has depth 0
                queue.append(node)

        # Step 2: Perform BFS to calculate depth for all nodes
        while queue:
            current_node = queue.popleft()
            current_depth = node_depths[current_node.id]

            # Traverse through the dependent nodes (reverse direction of prerequisites)
            for dependent in current_node.dependent_nodes.all():
                if dependent.id not in node_depths:  # If the dependent hasn't been visited
                    node_depths[dependent.id] = current_depth + 1
                    queue.append(dependent)

        logger.debug(node_depths)
        return node_depths
    
class TestAttemptView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request, test_id):
        test = get_object_or_404(Test, pk=test_id)
        questions = test.questions.all()
        serialized_questions = []

        for question in questions:
            all_answers = question.other_answers + [question.correct_answer]
            random.shuffle(all_answers)

            serialized_questions.append({
                "id": question.id,
                "text": question.text,
                "answers": all_answers,  
            })

        return Response(serialized_questions)

    def post(self, request, test_id):

        test = get_object_or_404(Test, pk=test_id)

        submitted_answers = request.data.get("answers", {})
        if not isinstance(submitted_answers, dict):
            return Response(
                {"error": "Answers must be a dictionary with question IDs as keys and answers as values."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        correct_answers = {}
        for question in test.questions.all():
            user_answer = submitted_answers.get(str(question.id))
            correct_answers[str(question.id)] = int(user_answer == question.correct_answer)

        test_attempt = TestAttempt.objects.create(
            test=test,
            student=request.user,
            answers=correct_answers,
            completed=True
        )
        test_attempt.calculate_score()

        return Response({
            "message": "Test submitted successfully.",
            "score": test_attempt.score,
            "total_questions": len(correct_answers),
            "correct_answers": sum(correct_answers.values()),
            "answers": correct_answers
        }, status=status.HTTP_201_CREATED)
    


class TestAttemptsView(APIView):

    def get(self, request, test_id):
        test = get_object_or_404(Test, pk=test_id)
        
        graph = test.graph
        
        attempts = TestAttempt.objects.filter(test=test)
        
        result = []
        
        for attempt in attempts:
            attempt_result = []
            
            for question_id, answer in attempt.answers.items():
                question = get_object_or_404(Question, pk=question_id)
                
                node = question.node
                
                attempt_result.append({
                    'node': node.id,  
                    'answer': answer
                })
            
            result.append(attempt_result)
        
        response_data = {
            'graph': {
                'id': graph.id,
                'title': graph.title
            },
            'attempts': result
        }
        
        return Response(response_data)