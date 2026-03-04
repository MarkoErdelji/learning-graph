from collections import defaultdict, deque
import datetime
import uuid
import json
import random
import pandas as pd
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import action
from learning_spaces.kst import iita
from .permissions import IsTeacher, IsExpert, IsStudent
from .settings import SOTIS_GRAPH, SOTIS_NS, LOM_NS
from .utils import execute_select, execute_update
from .models import AppUser, Question, Test, TestAttempt, TestQuestion, Node, KnowledgeGraph
from .serializers import (
    CustomTokenObtainPairSerializer, TestAttemptDetailSerializer, UserSerializer,
    KnowledgeGraphSerializer, GraphNodeSerializer, QuestionSerializer, TestSerializer, TestAttemptSerializer
)
from .qti_generator import generate_qti
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

class KnowledgeGraphViewSet(viewsets.ViewSet):
    serializer_class = KnowledgeGraphSerializer

    def list_graphs(self, request):
        try:
            graphs = KnowledgeGraph.objects.all()
            serializer = KnowledgeGraphSerializer(graphs, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error listing graphs: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        serializer = KnowledgeGraphSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        graph_id = str(uuid.uuid4())
        graph_uri = f"{SOTIS_NS}kg/{graph_id}"
        instance = serializer.save(id=graph_id, uri=graph_uri, author=request.user)
        user_uri = f"{SOTIS_NS}user/{request.user.username}"
        query = f"""
        PREFIX lom: <{LOM_NS}>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX sotis: <{SOTIS_NS}>
        INSERT DATA {{
            GRAPH <{SOTIS_GRAPH}> {{
                <{graph_uri}> rdf:type sotis:KnowledgeGraph ;
                              lom:identifier "{graph_uri}" ;
                              lom:title "{instance.title}" ;
                              lom:contributor <{user_uri}> ;
                              lom:learningResourceType lom:Graph ;
                              lom:language "{instance.language}" ;
                              lom:description "{instance.description}" ;
                              lom:keyword "{instance.keyword}" ;
                              lom:version "{instance.version}" ;
                              lom:status "{instance.status}" ;
                              lom:date "{datetime.datetime.now().isoformat()}" ;
                              lom:difficulty {instance.difficulty} ;
                              lom:context {instance.context} ;
                              lom:intendedEndUserRole {instance.intended_end_user_role} ;
                              lom:typicalAgeRange "{instance.typical_age_range}" ;
                              lom:typicalLearningTime "{instance.typical_learning_time}" .
            }}
        }}
        """
        try:
            execute_update(query)
            logger.debug(f"Created graph with URI: {graph_uri}")
            return Response(KnowledgeGraphSerializer(instance).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating graph: {str(e)}")
            instance.delete()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, pk=None):
        try:
            instance = get_object_or_404(KnowledgeGraph, id=pk)
            graph_uri = instance.uri
            query = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX sotis: <{SOTIS_NS}>
            DELETE WHERE {{
                GRAPH <{SOTIS_GRAPH}> {{
                    <{graph_uri}> ?p ?o .
                    ?node lom:partOf <{graph_uri}> .
                    ?node ?np ?no .
                    ?question lom:partOf ?node .
                    ?question ?qp ?qo .
                    ?test lom:partOf <{graph_uri}> .
                    ?test ?tp ?to .
                    ?attempt lom:partOf ?test .
                    ?attempt ?ap ?ao .
                }}
            }}
            """
            execute_update(query)
            logger.debug(f"Deleted graph with URI: {graph_uri}")
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"Error deleting graph: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GraphNodeViewSet(viewsets.ViewSet):
    serializer_class = GraphNodeSerializer

    def list(self, request):
        graph_id = request.query_params.get('graph_id')
        try:
            queryset = Node.objects.filter(graph_id=graph_id) if graph_id else Node.objects.all()
            serializer = GraphNodeSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error listing nodes: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        serializer = GraphNodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        graph_id = serializer.validated_data.get('graph')
        title = serializer.validated_data.get('title')
        logger.debug(graph_id)

        if not graph_id or not title:
            return Response({"error": "Graph ID and title are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        logger.debug(graph_id)
        graph = get_object_or_404(KnowledgeGraph, id=graph_id)
        node_id = str(uuid.uuid4())
        node_uri = f"{SOTIS_NS}node/{node_id}"
        instance = serializer.save(id=node_id, uri=node_uri, graph=graph, graph_uri=graph.uri)
        instance.calculate_difficulty()
        query = f"""
        PREFIX lom: <{LOM_NS}>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX sotis: <{SOTIS_NS}>
        INSERT DATA {{
            GRAPH <{SOTIS_GRAPH}> {{
                <{node_uri}> rdf:type sotis:Node ;
                             lom:identifier "{node_uri}" ;
                             lom:title "{title}" ;
                             lom:partOf <{graph.uri}> ;
                             lom:learningResourceType lom:Narrative_Text ;
                             lom:language "{instance.language}" ;
                             lom:description "{instance.description}" ;
                             lom:keyword "{instance.keyword}" ;
                             lom:version "{instance.version}" ;
                             lom:status "{instance.status}" ;
                             lom:contributor <{SOTIS_NS}user/{request.user.username}> ;
                             lom:date "{datetime.datetime.now().isoformat()}" ;
                             lom:difficulty {instance.difficulty} ;
                             lom:context {instance.context} ;
                             lom:intendedEndUserRole {instance.intended_end_user_role} ;
                             lom:typicalAgeRange "{instance.typical_age_range}" ;
                             lom:typicalLearningTime "{instance.typical_learning_time}" .
            }}
        }}
        """
        try:
            execute_update(query)
            logger.debug(f"Created node with URI: {node_uri}")
            return Response(GraphNodeSerializer(instance).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating node: {str(e)}")
            instance.delete()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['patch'])
    def update_node(self, request, pk=None):
        try:
            instance = get_object_or_404(Node, id=pk)
            serializer = GraphNodeSerializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            instance.calculate_difficulty()
            query = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX sotis: <{SOTIS_NS}>
            DELETE WHERE {{ GRAPH <{SOTIS_GRAPH}> {{ <{instance.uri}> ?p ?o }} }};
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                    <{instance.uri}> rdf:type sotis:Node ;
                                     lom:identifier "{instance.uri}" ;
                                     lom:title "{instance.title}" ;
                                     lom:partOf <{instance.graph_uri}> ;
                                     lom:learningResourceType lom:Narrative_Text ;
                                     lom:language "{instance.language}" ;
                                     lom:description "{instance.description}" ;
                                     lom:keyword "{instance.keyword}" ;
                                     lom:version "{instance.version}" ;
                                     lom:status "{instance.status}" ;
                                     lom:contributor <{SOTIS_NS}user/{request.user.username}> ;
                                     lom:date "{datetime.datetime.now().isoformat()}" ;
                                     lom:difficulty {instance.difficulty} ;
                                     lom:context {instance.context} ;
                                     lom:intendedEndUserRole {instance.intended_end_user_role} ;
                                     lom:typicalAgeRange "{instance.typical_age_range}" ;
                                     lom:typicalLearningTime "{instance.typical_learning_time}" .
                }}
            }}
            """
            execute_update(query)
            logger.debug(f"Updated node with URI: {instance.uri}")
            return Response(GraphNodeSerializer(instance).data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error updating node: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['delete'])
    def delete_node(self, request, pk=None):
        try:
            instance = get_object_or_404(Node, id=pk)
            node_uri = instance.uri

            # SPARQL multi-delete query
            query = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX sotis: <{SOTIS_NS}>

            DELETE {{ GRAPH <{SOTIS_GRAPH}> {{ <{node_uri}> ?p ?o }} }}
            WHERE  {{ GRAPH <{SOTIS_GRAPH}> {{ <{node_uri}> ?p ?o }} }};

            DELETE {{ GRAPH <{SOTIS_GRAPH}> {{ ?s lom:requires <{node_uri}> }} }}
            WHERE  {{ GRAPH <{SOTIS_GRAPH}> {{ ?s lom:requires <{node_uri}> }} }};

            DELETE {{ GRAPH <{SOTIS_GRAPH}> {{ ?question lom:partOf <{node_uri}> }} }}
            WHERE  {{ GRAPH <{SOTIS_GRAPH}> {{ ?question lom:partOf <{node_uri}> }} }};

            DELETE {{ GRAPH <{SOTIS_GRAPH}> {{ ?question ?qp ?qo }} }}
            WHERE  {{ GRAPH <{SOTIS_GRAPH}> {{ ?question lom:partOf <{node_uri}> ; ?qp ?qo }} }};
            """

            execute_update(query)
            logger.debug(f"Deleted node and related triples for URI: {node_uri}")

            # Delete from Django DB
            instance.delete()

            return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            logger.error(f"Error deleting node {pk}: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

    @action(detail=True, methods=['patch'])
    def update_with_prerequisites(self, request, pk=None):
        try:
            target_node = get_object_or_404(Node, id=pk)
            target_node_uri = target_node.uri
            prerequisite_node_ids = request.data.get("prerequisite_node_ids", [])
            if not isinstance(prerequisite_node_ids, list):
                return Response({"error": "prerequisite_node_ids must be a list of IDs"}, status=status.HTTP_400_BAD_REQUEST)

            prerequisite_nodes = Node.objects.filter(id__in=prerequisite_node_ids)
            if len(prerequisite_nodes) != len(prerequisite_node_ids):
                return Response({"error": "Some prerequisite nodes not found"}, status=status.HTTP_404_NOT_FOUND)

            delete_query = f"""
            PREFIX lom: <{LOM_NS}>
            DELETE WHERE {{
                GRAPH <{SOTIS_GRAPH}> {{
                    <{target_node_uri}> lom:requires ?prereq .
                }}
            }}
            """
            execute_update(delete_query)
            target_node.prerequisite_nodes.clear()
            insert_parts = []
            for prereq in prerequisite_nodes:
                target_node.prerequisite_nodes.add(prereq)
                insert_parts.append(f"<{target_node_uri}> lom:requires <{prereq.uri}> .")
            if insert_parts:
                insert_query = f"""
                PREFIX lom: <{LOM_NS}>
                INSERT DATA {{
                    GRAPH <{SOTIS_GRAPH}> {{
                        {"".join(insert_parts)}
                    }}
                }}
                """
                execute_update(insert_query)
            title = request.data.get("title")
            if title:
                target_node.title = title
                target_node.save()
                update_title_query = f"""
                PREFIX lom: <{LOM_NS}>
                DELETE {{ GRAPH <{SOTIS_GRAPH}> {{ <{target_node_uri}> lom:title ?old }} }}
                INSERT {{ GRAPH <{SOTIS_GRAPH}> {{ <{target_node_uri}> lom:title "{title}" }} }}
                WHERE {{ GRAPH <{SOTIS_GRAPH}> {{ <{target_node_uri}> lom:title ?old }} }}
                """
                execute_update(update_title_query)
            serializer = GraphNodeSerializer(target_node)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error updating node prerequisites: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class KnowledgeGraphDetailView(APIView):
    def get(self, request, pk):
        graph_uri = f"{SOTIS_NS}kg/{pk}"
        try:
            graph = get_object_or_404(KnowledgeGraph, id=pk)
            nodes = Node.objects.filter(graph_id=pk)
            serializer = KnowledgeGraphSerializer(graph)
            data = serializer.data
            data['nodes'] = GraphNodeSerializer(nodes, many=True).data
            return Response(data)
        except Exception as e:
            logger.error(f"Error fetching graph: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer


    def perform_create(self, serializer):
        instance = serializer.save(node_uri=serializer.validated_data['node'].uri)
        question_data = json.dumps({
            "text": instance.text,
            "correct_answer": instance.correct_answer,
            "other_answers": instance.other_answers
        })
        query = f"""
        PREFIX lom: <{LOM_NS}>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX sotis: <{SOTIS_NS}>
        INSERT DATA {{
            GRAPH <{SOTIS_GRAPH}> {{
                <{instance.uri}> rdf:type sotis:Question ;
                                 lom:identifier "{instance.uri}" ;
                                 lom:title "{instance.text}" ;
                                 lom:description '{question_data}' ;
                                 lom:learningResourceType lom:Questionnaire ;
                                 lom:language "{instance.language}" ;
                                 lom:partOf <{instance.node_uri}> ;
                                 lom:version "{instance.version}" ;
                                 lom:status "{instance.status}" ;
                                 lom:contributor <{SOTIS_NS}user/{self.request.user.username}> ;
                                 lom:date "{datetime.datetime.now().isoformat()}" ;
                                 lom:difficulty {instance.difficulty} ;
                                 lom:context {instance.context} ;
                                 lom:intendedEndUserRole {instance.intended_end_user_role} ;
                                 lom:typicalAgeRange "{instance.typical_age_range}" ;
                                 lom:typicalLearningTime "{instance.typical_learning_time}" .
            }}
        }}
        """
        try:
            execute_update(query)
            logger.debug(f"Created question with URI: {instance.uri}")
        except Exception as e:
            logger.error(f"Error creating question in RDF: {str(e)}")
            instance.delete()
            raise

    def perform_update(self, serializer):
        instance = serializer.save()
        question_data = json.dumps({
            "text": instance.text,
            "correct_answer": instance.correct_answer,
            "other_answers": instance.other_answers
        })
        query = f"""
        PREFIX lom: <{LOM_NS}>
        PREFIX sotis: <{SOTIS_NS}>
        DELETE WHERE {{ GRAPH <{SOTIS_GRAPH}> {{ <{instance.uri}> ?p ?o }} }};
        INSERT DATA {{
            GRAPH <{SOTIS_GRAPH}> {{
                <{instance.uri}> rdf:type sotis:Question ;
                                 lom:identifier "{instance.uri}" ;
                                 lom:title "{instance.text}" ;
                                 lom:description '{question_data}' ;
                                 lom:learningResourceType lom:Questionnaire ;
                                 lom:language "{instance.language}" ;
                                 lom:partOf <{instance.node_uri}> ;
                                 lom:version "{instance.version}" ;
                                 lom:status "{instance.status}" ;
                                 lom:contributor <{SOTIS_NS}user/{self.request.user.username}> ;
                                 lom:date "{datetime.datetime.now().isoformat()}" ;
                                 lom:difficulty {instance.difficulty} ;
                                 lom:context {instance.context} ;
                                 lom:intendedEndUserRole {instance.intended_end_user_role} ;
                                 lom:typicalAgeRange "{instance.typical_age_range}" ;
                                 lom:typicalLearningTime "{instance.typical_learning_time}" .
            }}
        }}
        """
        try:
            execute_update(query)
            logger.debug(f"Updated question with URI: {instance.uri}")
        except Exception as e:
            logger.error(f"Error updating question in RDF: {str(e)}")
            raise

    def perform_destroy(self, instance):
        query = f"""
        PREFIX lom: <{LOM_NS}>
        DELETE WHERE {{ GRAPH <{SOTIS_GRAPH}> {{ <{instance.uri}> ?p ?o }} }}
        """
        try:
            execute_update(query)
            logger.debug(f"Deleted question with URI: {instance.uri}")
            super().perform_destroy(instance)
        except Exception as e:
            logger.error(f"Error deleting question: {str(e)}")
            raise

    @action(detail=True, methods=['patch'], url_path='update')
    def update_question(self, request, pk=None):
        try:
            question = get_object_or_404(Question, pk=pk)
            serializer = QuestionSerializer(question, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            query = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX sotis: <{SOTIS_NS}>
            DELETE WHERE {{ GRAPH <{SOTIS_GRAPH}> {{ <{instance.uri}> ?p ?o }} }};
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                    <{instance.uri}> rdf:type sotis:Question ;
                                     lom:identifier "{instance.uri}" ;
                                     lom:title "{instance.text}" ;
                                     lom:description '{instance.description}' ;
                                     lom:learningResourceType lom:Questionnaire ;
                                     lom:language "{instance.language}" ;
                                     lom:partOf <{instance.node_uri}> ;
                                     lom:version "{instance.version}" ;
                                     lom:status "{instance.status}" ;
                                     lom:contributor <{SOTIS_NS}user/{self.request.user.username}> ;
                                     lom:date "{datetime.datetime.now().isoformat()}" ;
                                     lom:difficulty {instance.difficulty} ;
                                     lom:context {instance.context} ;
                                     lom:intendedEndUserRole {instance.intended_end_user_role} ;
                                     lom:typicalAgeRange "{instance.typical_age_range}" ;
                                     lom:typicalLearningTime "{instance.typical_learning_time}" .
                }}
            }}
            """
            execute_update(query)
            logger.debug(f"Updated question with URI: {instance.uri}")
            return Response(QuestionSerializer(instance).data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error updating question: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['delete'], url_path='delete')
    def delete_question(self, request, pk=None):
        try:
            question = get_object_or_404(Question, pk=pk)
            query = f"""
            PREFIX lom: <{LOM_NS}>
            DELETE WHERE {{ GRAPH <{SOTIS_GRAPH}> {{ <{question.uri}> ?p ?o }} }}
            """
            execute_update(query)
            logger.debug(f"Deleted question with URI: {question.uri}")
            question.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"Error deleting question: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FirstQuestionView(APIView):

    def get(self, request):
        try:
            question = Question.objects.first()
            if not question:
                return Response({'error': 'No questions exist.'}, status=status.HTTP_404_NOT_FOUND)
            serializer = QuestionSerializer(question)
            data = serializer.data
            correct_answer = str(data['correct_answer'])
            other_answers = list(map(str, data['other_answers']))
            all_answers = other_answers + [correct_answer]
            random.shuffle(all_answers)
            data['other_answers'] = all_answers
            data.pop('correct_answer')
            return Response(data)
        except Exception as e:
            logger.error(f"Error fetching first question: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class KnowledgeGraphWithTestResultDetailView(APIView):
    def get(self, request, test_attempt_id):
        try:
            test_attempt = get_object_or_404(TestAttempt, pk=test_attempt_id)
            graph = get_object_or_404(KnowledgeGraph, uri=test_attempt.test.graph_uri)
            nodes = Node.objects.filter(graph_uri=graph.uri)
            d3_data = {
                "id": graph.id,
                "uri": graph.uri,
                "title": graph.title,
                "score": test_attempt.score,
                "student_name": f"{test_attempt.student.first_name} {test_attempt.student.last_name}",
                "nodes": [],
                "links": []
            }
            node_mapping = {}
            answers = test_attempt.answers
            for idx, node in enumerate(nodes):
                node_data = GraphNodeSerializer(node).data
                node_data["answer_correctness"] = []
                for question in Question.objects.filter(node_uri=node.uri):
                    user_answer = answers.get(str(question.id))
                    # Compare user's answer with the correct answer
                    answered_correctly = user_answer == question.correct_answer if user_answer else False
                    node_data["answer_correctness"].append({
                        "question_id": str(question.id),
                        "answered_correctly": answered_correctly
                    })
                d3_data["nodes"].append(node_data)
                node_mapping[node.id] = idx
            for node in nodes:
                for prereq in node.prerequisite_nodes.all():
                    d3_data["links"].append({
                        "source": prereq.id,
                        "target": node.id
                    })
            return Response(d3_data)
        except ValueError:
            logger.error(f"Invalid UUID for test attempt: {test_attempt_id}")
            return Response({"error": "Invalid test attempt ID format, UUID expected"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error fetching test result graph: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TestListView(APIView):

    def get(self, request):
        try:
            tests = Test.objects.all()
            serializer = TestSerializer(tests, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error listing tests: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TestListGraphView(APIView):

    def get(self, request):
        try:
            tests = Test.objects.all()
            serializer = TestSerializer(tests, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error listing tests for graph: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TestCreationView(APIView):
    def post(self, request):
        graph_id = request.data.get('graph_id')
        question_ids = request.data.get('question_ids', [])
        if not graph_id:
            return Response({"error": "Graph ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            graph = get_object_or_404(KnowledgeGraph, id=graph_id)
            questions = Question.objects.filter(id__in=question_ids)
            if not questions.exists():
                return Response({"error": "No valid questions provided"}, status=status.HTTP_400_BAD_REQUEST)

            ancestor_cache = {}
            def get_ancestor_ids(node_uri):
                if node_uri in ancestor_cache:
                    return ancestor_cache[node_uri]
                node = Node.objects.get(uri=node_uri)
                prereqs = node.prerequisite_nodes.all()
                ancestors = set(prereq.uri for prereq in prereqs)
                for p in prereqs:
                    ancestors.update(get_ancestor_ids(p.uri))
                ancestor_cache[node_uri] = ancestors
                return ancestors

            question_ancestors = {q: len(get_ancestor_ids(q.node_uri)) for q in questions}
            sorted_questions = sorted(question_ancestors.items(), key=lambda x: x[1])

            test = Test.objects.create(
                id=str(uuid.uuid4()),
                uri=f"{SOTIS_NS}test/{uuid.uuid4()}",
                graph=graph,
                graph_uri=graph.uri,
                title=f"Test for {graph.title}",
                author=request.user,
                language="lom:en",
                description=f"Test for graph {graph.title}",
                keyword="test, assessment",
                version="1.0",
                status="lom:Final",
                difficulty="lom:Medium",
                context="lom:Higher_Education",
                intended_end_user_role="lom:Student",
                typical_age_range="18-",
                typical_learning_time=f"PT{len(sorted_questions)*5}M"
            )
            insert_parts = []
            for idx, (question, _) in enumerate(sorted_questions):
                TestQuestion.objects.create(test=test, question=question, order=idx)
                insert_parts.append(f"<{test.uri}> lom:partOf <{question.uri}> .")
            user_uri = f"{SOTIS_NS}user/{request.user.username}"
            query_test = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX sotis: <{SOTIS_NS}>
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                    <{test.uri}> rdf:type sotis:Test ;
                                 lom:identifier "{test.uri}" ;
                                 lom:title "{test.title}" ;
                                 lom:contributor <{user_uri}> ;
                                 lom:learningResourceType lom:Exam ;
                                 lom:language "{test.language}" ;
                                 lom:description "{test.description}" ;
                                 lom:keyword "{test.keyword}" ;
                                 lom:version "{test.version}" ;
                                 lom:status "{test.status}" ;
                                 lom:date "{datetime.datetime.now().isoformat()}" ;
                                 lom:difficulty {test.difficulty} ;
                                 lom:context {test.context} ;
                                 lom:intendedEndUserRole {test.intended_end_user_role} ;
                                 lom:typicalAgeRange "{test.typical_age_range}" ;
                                 lom:typicalLearningTime "{test.typical_learning_time}" ;
                                 lom:partOf <{graph.uri}> .
                    {" ".join(insert_parts)}
                }}
            }}
            """
            execute_update(query_test)
            logger.debug(f"Created test with URI: {test.uri}")
            return Response({"test_id": test.id, "graph_id": graph_id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating test: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TestAttemptView(APIView):
    def get(self, request, test_id):
        try:
            test = get_object_or_404(Test, pk=test_id)
            test_questions = test.testquestion_set.select_related('question').order_by('order')
            serialized_questions = []
            for tq in test_questions:
                question = tq.question
                all_answers = (question.other_answers or []) + [question.correct_answer]
                random.shuffle(all_answers)
                serialized_questions.append({
                    "id": str(question.id),
                    "text": question.text,
                    "answers": all_answers,
                    "node_id": question.node_uri.split('/')[-1] if question.node_uri else None
                })
            return Response(serialized_questions)
        except ValueError:
            logger.error(f"Invalid UUID for test: {test_id}")
            return Response({"error": "Invalid test ID format, UUID expected"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error fetching test questions: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, test_id):
        try:
            test = get_object_or_404(Test, pk=test_id)
            submitted_answers = request.data.get("answers", {})
            if not isinstance(submitted_answers, dict):
                return Response(
                    {"error": "Answers must be a dictionary with question IDs as keys and answers as values"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            test_attempt = TestAttempt.objects.create(
                id=str(uuid.uuid4()),
                uri=f"{SOTIS_NS}attempt/{uuid.uuid4()}",
                test=test,
                student=request.user,
                answers=submitted_answers,  # Store raw submitted answers
                completed=True,
                language=test.language,
                description=f"Attempt for test {test.title}",
                version="1.0",
                status="lom:Final"
            )
            test_attempt.calculate_score()
            attempt_data = json.dumps({
                "answers": test_attempt.answers,
                "score": test_attempt.score
            })
            student_uri = f"<http://example.com/sotis#user/{request.user.username}>"

            query_attempt = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX sotis: <{SOTIS_NS}>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                    <{test_attempt.uri}> rdf:type sotis:TestAttempt ;
                                        lom:identifier "{test_attempt.uri}" ;
                                        lom:partOf <{test.uri}> ;
                                        lom:contributor {student_uri} ;
                                        lom:description '{attempt_data}' ;
                                        lom:language "{test_attempt.language}" ;
                                        lom:version "{test_attempt.version}" ;
                                        lom:status "{test_attempt.status}" ;
                                        lom:date "{datetime.datetime.now().isoformat()}"^^xsd:dateTime ;
                                        sotis:score "{test_attempt.score}"^^xsd:float .   # ← THIS WAS MISSING
                }}
            }}
            """
            execute_update(query_attempt)

            # === ADD THIS BLOCK (this is what the seed had) ===
            for qid, answer in submitted_answers.items():
                try:
                    tq = test.testquestion_set.get(question__id=qid)
                    question = tq.question
                    is_correct = "true" if str(answer) == str(question.correct_answer) else "false"
                    query_answer = f"""
                    PREFIX sotis: <{SOTIS_NS}>
                    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                    INSERT DATA {{
                        GRAPH <{SOTIS_GRAPH}> {{
                            <{test_attempt.uri}> sotis:hasAnswer [
                                sotis:question <{question.uri}> ;
                                sotis:answer "{answer}" ;
                                sotis:isCorrect "{is_correct}"^^xsd:boolean
                            ] .
                        }}
                    }}
                    """
                    execute_update(query_answer)
                except:
                    pass
            logger.debug(f"Created test attempt with URI: {test_attempt.uri}")
            correct_answers = {}
            for test_question in test.testquestion_set.select_related('question'):
                question = test_question.question
                user_answer = submitted_answers.get(str(question.id))
                correct_answers[str(question.id)] = int(user_answer == question.correct_answer)
            return Response({
                "message": "Test submitted successfully",
                "attempt_id": str(test_attempt.id),
                "score": test_attempt.score,
                "total_questions": len(correct_answers),
                "correct_answers": sum(correct_answers.values()),
                "answers": correct_answers
            }, status=status.HTTP_201_CREATED)
        except ValueError:
            logger.error(f"Invalid UUID for test: {test_id}")
            return Response({"error": "Invalid test ID format, UUID expected"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating test attempt: {str(e)}")
            if 'test_attempt' in locals():
                test_attempt.delete()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TestAttemptsView(APIView):
    def get(self, request, test_id):
        try:
            test = get_object_or_404(Test, pk=test_id)
            test_questions = test.testquestion_set.select_related('question').order_by('order')
            serialized_questions = []
            for tq in test_questions:
                question = tq.question
                all_answers = (question.other_answers or []) + [question.correct_answer]
                random.shuffle(all_answers)
                serialized_questions.append({
                    "id": str(question.id),
                    "text": question.text,
                    "answers": all_answers,
                    "node_id": question.node_uri.split('/')[-1] if question.node_uri else None
                })
            return Response(serialized_questions)
        except ValueError:
            logger.error(f"Invalid UUID for test: {test_id}")
            return Response({"error": "Invalid test ID format, UUID expected"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error fetching test questions: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, test_id):
        try:
            test = get_object_or_404(Test, pk=test_id)
            submitted_answers = request.data.get("answers", {})
            if not isinstance(submitted_answers, dict):
                return Response(
                    {"error": "Answers must be a dictionary with question IDs as keys and answers as values"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            test_attempt = TestAttempt.objects.create(
                id=str(uuid.uuid4()),
                uri=f"{SOTIS_NS}attempt/{uuid.uuid4()}",
                test=test,
                student=request.user,
                answers=submitted_answers,  # Store raw submitted answers
                completed=True,
                language=test.language,
                description=f"Attempt for test {test.title}",
                version="1.0",
                status="lom:Final"
            )
            test_attempt.calculate_score()
            attempt_data = json.dumps({
                "answers": test_attempt.answers,
                "score": test_attempt.score
            })
            student_uri = f"{SOTIS_NS}user/{request.user.username}"
            query_attempt = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX sotis: <{SOTIS_NS}>
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                    <{test_attempt.uri}> rdf:type sotis:TestAttempt ;
                                         lom:identifier "{test_attempt.uri}" ;
                                         lom:partOf <{test.uri}> ;
                                         lom:contributor <{student_uri}> ;
                                         lom:description '{attempt_data}' ;
                                         lom:language "{test_attempt.language}" ;
                                         lom:version "{test_attempt.version}" ;
                                         lom:status "{test_attempt.status}" ;
                                         lom:date "{datetime.datetime.now().isoformat()}" .
                }}
            }}
            """
            execute_update(query_attempt)
            logger.debug(f"Created test attempt with URI: {test_attempt.uri}")
            correct_answers = {}
            for test_question in test.testquestion_set.select_related('question'):
                question = test_question.question
                user_answer = submitted_answers.get(str(question.id))
                correct_answers[str(question.id)] = int(user_answer == question.correct_answer)
            return Response({
                "message": "Test submitted successfully",
                "attempt_id": str(test_attempt.id),
                "score": test_attempt.score,
                "total_questions": len(correct_answers),
                "correct_answers": sum(correct_answers.values()),
                "answers": correct_answers
            }, status=status.HTTP_201_CREATED)
        except ValueError:
            logger.error(f"Invalid UUID for test: {test_id}")
            return Response({"error": "Invalid test ID format, UUID expected"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating test attempt: {str(e)}")
            if 'test_attempt' in locals():
                test_attempt.delete()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TestResultsView(APIView):
    def get(self, request, test_id):
        try:
            test = get_object_or_404(Test, pk=test_id)
            test_attempts = TestAttempt.objects.filter(test=test).select_related('student')
            serializer = TestAttemptDetailSerializer(test_attempts, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValueError:
            logger.error(f"Invalid UUID for test: {test_id}")
            return Response({"error": "Invalid test ID format, UUID expected"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error fetching test results: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TestAttemptDetailView(generics.ListAPIView):
    queryset = TestAttempt.objects.all()
    serializer_class = TestAttemptDetailSerializer

    def get_queryset(self):
        test_id = self.kwargs.get('test_id')
        return self.queryset.filter(test_id=test_id)

class GenerateGraphFromIITA(APIView):
    def post(self, request, test_id):
        try:
            test = get_object_or_404(Test, pk=test_id)
            original_graph = get_object_or_404(KnowledgeGraph, uri=test.graph_uri)
            nodes = Node.objects.filter(graph_uri=original_graph.uri)
            if not nodes.exists():
                logger.warning(f"No nodes found for graph {original_graph.uri}")
                return Response({"error": "No nodes found for the graph"}, status=status.HTTP_400_BAD_REQUEST)
            index_to_node_uri = {idx: node.uri for idx, node in enumerate(nodes)}
            
            attempts = TestAttempt.objects.filter(test=test)
            data = []
            for attempt in attempts:
                row = []
                for node_index, node_uri in enumerate(index_to_node_uri.values()):
                    node_questions = Question.objects.filter(node_uri=node_uri)
                    answered_correctly = any(
                        attempt.answers.get(str(q.id), 0) == q.correct_answer for q in node_questions
                    )
                    row.append(1 if answered_correctly else 0)
                data.append(row)
            df = pd.DataFrame(data).fillna(0)
            if df.empty or df.isnull().values.any():
                logger.error("Invalid or incomplete data for IITA analysis")
                return Response(
                    {"error": "Invalid or incomplete data provided for IITA analysis"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            response = iita(df, v=1)
            implications = response.get("implications", [])
            
            new_graph_id = str(uuid.uuid4())
            new_graph_uri = f"{SOTIS_NS}kg/{new_graph_id}"
            new_graph = KnowledgeGraph.objects.create(
                id=new_graph_id,
                uri=new_graph_uri,
                title=f"{original_graph.title} (IITA)",
                author=original_graph.author,
                language=original_graph.language,
                description=f"IITA-generated graph from test {test.title}",
                keyword="IITA, knowledge graph",
                version="1.0",
                status="lom:Final",
                difficulty="lom:Medium",
                context="lom:Higher_Education",
                intended_end_user_role="lom:Student",
                typical_age_range="18-",
                typical_learning_time="PT1H"
            )
            user_uri = f"{SOTIS_NS}user/{original_graph.author.id}"
            query_new_graph = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX sotis: <{SOTIS_NS}>
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                    <{new_graph_uri}> rdf:type sotis:KnowledgeGraph ;
                                      lom:identifier "{new_graph_uri}" ;
                                      lom:title "{new_graph.title}" ;
                                      lom:contributor <{user_uri}> ;
                                      lom:learningResourceType lom:Graph ;
                                      lom:language "{new_graph.language}" ;
                                      lom:description "{new_graph.description}" ;
                                      lom:keyword "{new_graph.keyword}" ;
                                      lom:version "{new_graph.version}" ;
                                      lom:status "{new_graph.status}" ;
                                      lom:date "{datetime.datetime.now().isoformat()}" ;
                                      lom:difficulty {new_graph.difficulty} ;
                                      lom:context {new_graph.context} ;
                                      lom:intendedEndUserRole {new_graph.intended_end_user_role} ;
                                      lom:typicalAgeRange "{new_graph.typical_age_range}" ;
                                      lom:typicalLearningTime "{new_graph.typical_learning_time}" .
                }}
            }}
            """
            execute_update(query_new_graph)
            
            node_mapping = {}
            for old_node in nodes:
                new_node_id = str(uuid.uuid4())
                new_node_uri = f"{SOTIS_NS}node/{new_node_id}"
                new_node = Node.objects.create(
                    id=new_node_id,
                    uri=new_node_uri,
                    title=old_node.title,
                    graph=new_graph,
                    graph_uri=new_graph_uri,
                    language=old_node.language,
                    description=f"Node copied from {old_node.uri}",
                    keyword="IITA, node",
                    version="1.0",
                    status="lom:Final",
                    difficulty="lom:Medium",
                    context="lom:Higher_Education",
                    intended_end_user_role="lom:Student",
                    typical_age_range="18-",
                    typical_learning_time="PT30M"
                )
                query_new_node = f"""
                PREFIX lom: <{LOM_NS}>
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX sotis: <{SOTIS_NS}>
                INSERT DATA {{
                    GRAPH <{SOTIS_GRAPH}> {{
                        <{new_node_uri}> rdf:type sotis:Node ;
                                         lom:identifier "{new_node_uri}" ;
                                         lom:title "{new_node.title}" ;
                                         lom:partOf <{new_graph_uri}> ;
                                         lom:learningResourceType lom:Narrative_Text ;
                                         lom:language "{new_node.language}" ;
                                         lom:description "{new_node.description}" ;
                                         lom:keyword "{new_node.keyword}" ;
                                         lom:version "{new_node.version}" ;
                                         lom:status "{new_node.status}" ;
                                         lom:contributor <{user_uri}> ;
                                         lom:date "{datetime.datetime.now().isoformat()}" ;
                                         lom:difficulty {new_node.difficulty} ;
                                         lom:context {new_node.context} ;
                                         lom:intendedEndUserRole {new_node.intended_end_user_role} ;
                                         lom:typicalAgeRange "{new_node.typical_age_range}" ;
                                         lom:typicalLearningTime "{new_node.typical_learning_time}" .
                    }}
                }}
                """
                execute_update(query_new_node)
                node_mapping[old_node.uri] = new_node_uri
                
                # Copy questions from the old node to the new node
                for question in Question.objects.filter(node_uri=old_node.uri):
                    new_question_id = str(uuid.uuid4())
                    new_question_uri = f"{SOTIS_NS}question/{new_question_id}"
                    new_question = Question.objects.create(
                        id=new_question_id,
                        uri=new_question_uri,
                        text=question.text,
                        correct_answer=question.correct_answer,
                        other_answers=question.other_answers,
                        node=new_node,
                        node_uri=new_node_uri,
                        language=question.language,
                        description=f"Question copied from {question.uri}",
                        keyword="IITA, question",
                        version="1.0",
                        status="lom:Final",
                        difficulty="lom:Medium",
                        context="lom:Higher_Education",
                        intended_end_user_role="lom:Student",
                        typical_age_range="18-",
                        typical_learning_time="PT5M"
                    )
                    query_new_question = f"""
                    PREFIX lom: <{LOM_NS}>
                    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                    PREFIX sotis: <{SOTIS_NS}>
                    INSERT DATA {{
                        GRAPH <{SOTIS_GRAPH}> {{
                            <{new_question_uri}> rdf:type sotis:Question ;
                                                 lom:identifier "{new_question_uri}" ;
                                                 lom:title "{new_question.text[:50]}" ;
                                                 lom:partOf <{new_node_uri}> ;
                                                 lom:learningResourceType lom:Question ;
                                                 lom:language "{new_question.language}" ;
                                                 lom:description "{new_question.description}" ;
                                                 lom:keyword "{new_question.keyword}" ;
                                                 lom:version "{new_question.version}" ;
                                                 lom:status "{new_question.status}" ;
                                                 lom:contributor <{user_uri}> ;
                                                 lom:date "{datetime.datetime.now().isoformat()}" ;
                                                 lom:difficulty {new_question.difficulty} ;
                                                 lom:context {new_question.context} ;
                                                 lom:intendedEndUserRole {new_question.intended_end_user_role} ;
                                                 lom:typicalAgeRange "{new_question.typical_age_range}" ;
                                                 lom:typicalLearningTime "{new_question.typical_learning_time}" .
                        }}
                    }}
                    """
                    execute_update(query_new_question)
                    logger.debug(f"Created new question {new_question_uri} for node {new_node_uri}")
            
            added_dependencies = set()
            for prereq_idx, target_idx in implications:
                prereq_uri = index_to_node_uri.get(prereq_idx)
                target_uri = index_to_node_uri.get(target_idx)
                new_prereq_uri = node_mapping.get(prereq_uri)
                new_target_uri = node_mapping.get(target_uri)
                if new_prereq_uri and new_target_uri:
                    reverse_edge = (new_prereq_uri, new_target_uri)
                    forward_edge = (new_target_uri, new_prereq_uri)
                    if reverse_edge in added_dependencies:
                        continue
                    if forward_edge not in added_dependencies:
                        new_prereq = Node.objects.get(uri=new_prereq_uri)
                        new_target = Node.objects.get(uri=new_target_uri)
                        new_target.prerequisite_nodes.add(new_prereq)
                        query_add_rel = f"""
                        PREFIX lom: <{LOM_NS}>
                        INSERT DATA {{
                            GRAPH <{SOTIS_GRAPH}> {{
                                <{new_target_uri}> lom:requires <{new_prereq_uri}> .
                            }}
                        }}
                        """
                        execute_update(query_add_rel)
                        added_dependencies.add(forward_edge)
            
            logger.debug(f"Created IITA graph with URI: {new_graph_uri}")

            return Response({
                "message": "New graph created successfully",
                "graph_id": new_graph_id,
                "uri": new_graph_uri
            }, status=status.HTTP_201_CREATED)
        except ValueError:
            logger.error(f"Invalid UUID for test: {test_id}")
            return Response({"error": "Invalid test ID format, UUID expected"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error generating IITA graph: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TestsForGraphView(APIView):
    def get(self, request, graph_id):
        try:
            graph = get_object_or_404(KnowledgeGraph, id=graph_id)
            tests = Test.objects.filter(graph_uri=graph.uri)
            serializer = TestSerializer(tests, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error fetching tests for graph: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class QuestionsForTestView(APIView):
    def get(self, request, test_id):
        try:
            test = get_object_or_404(Test, pk=test_id)
            test_questions = test.testquestion_set.select_related('question').order_by('order')
            if not test_questions.exists():
                logger.warning(f"No questions found for test: {test_id}")
                return Response({"message": "No questions associated with this test"}, status=status.HTTP_200_OK)
            
            questions_list = [
                {
                    'id': str(tq.question.id),
                    'text': tq.question.text,
                    'node_id': tq.question.node_uri.split('/')[-1] if tq.question.node_uri else None
                }
                for tq in test_questions
            ]
            logger.debug(f"Fetched {len(questions_list)} questions for test {test_id}")
            return Response(questions_list, status=status.HTTP_200_OK)
        except ValueError:
            logger.error(f"Invalid UUID for test: {test_id}")
            return Response({"error": "Invalid test ID format, UUID expected"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error fetching questions for test: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DownloadIQTFormView(APIView):
    def get(self, request, test_id):
        try:
            test = get_object_or_404(Test, pk=test_id)
            tree = generate_qti(test_id)
            response = HttpResponse(content_type='application/xml')
            response['Content-Disposition'] = f'attachment; filename="test_{test_id}_qti.xml"'
            tree.write(response, encoding="utf-8", xml_declaration=True)
            return response
        except ValueError:
            logger.error(f"Invalid UUID for test: {test_id}")
            return Response({"error": "Invalid test ID format, UUID expected"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error generating QTI file: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StudentOverallAverageView(APIView):
    def get(self, request):
        user_uri = f"http://example.com/sotis/user/{request.user.username}"
        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>
        SELECT (AVG(?score) AS ?avgScore) (COUNT(?attempt) AS ?totalAttempts)
        WHERE {{
          GRAPH <http://example.com/sotis/graph> {{
            ?attempt rdf:type sotis:TestAttempt ;
                     lom:contributor <{user_uri}> ;
                     lom:description ?desc .
            BIND(REPLACE(STR(?desc), ".*Score: ([0-9.]+(\\.[0-9]+)?).*", "$1") AS ?rawScore)
            BIND(xsd:float(?rawScore) AS ?score)
          }}
        }}
        """
        results = execute_select(query)
        b = results["results"]["bindings"][0] if results["results"]["bindings"] else {}
        data = {
            "average_score": round(float(b.get("avgScore", {}).get("value", 0)), 1),
            "total_attempts": int(b.get("totalAttempts", {}).get("value", 0))
        }
        return Response(data)


class StudentProgressOverTimeView(APIView):
    def get(self, request):
        user_uri = f"http://example.com/sotis/user/{request.user.username}"
        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>
        SELECT ?testTitle ?date ?desc
        WHERE {{
          GRAPH <http://example.com/sotis/graph> {{
            ?attempt rdf:type sotis:TestAttempt ;
                     lom:contributor <{user_uri}> ;
                     lom:partOf ?test ;
                     lom:description ?desc ;
                     lom:date ?date .
            ?test lom:title ?testTitle .
          }}
        }}
        ORDER BY ?date
        """
        results = execute_select(query)
        data = []
        for b in results["results"]["bindings"]:
            desc = b["desc"]["value"]
            match = re.search(r"Score: (\d+\.?\d*)", desc)
            score = float(match.group(1)) if match else 0
            data.append({
                "test": b["testTitle"]["value"],
                "date": b["date"]["value"][:10],
                "score": score
            })
        return Response(data)


class StudentTopicMasteryView(APIView):
    def get(self, request):
        user_uri = f"http://example.com/sotis/user/{request.user.username}"
        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>
        SELECT ?nodeTitle (AVG(?correctFloat) AS ?avgScore) (COUNT(?q) AS ?questionsAttempted)
        WHERE {{
          GRAPH <http://example.com/sotis/graph> {{
            ?attempt lom:contributor <{user_uri}> ;
                     sotis:hasAnswer ?ans .
            ?ans sotis:question ?q ;
                 sotis:answer ?given .
            ?q lom:partOf ?node ;
               sotis:correctAnswer ?correct .
            ?node lom:title ?nodeTitle .
            BIND(IF(STR(?given) = STR(?correct), 1.0, 0.0) AS ?correctFloat)
          }}
        }}
        GROUP BY ?nodeTitle
        HAVING (COUNT(?q) > 0)
        ORDER BY DESC(?avgScore)
        """
        results = execute_select(query)
        data = []
        for b in results["results"]["bindings"]:
            data.append({
                "topic": b["nodeTitle"]["value"],
                "mastery_percent": round(float(b["avgScore"]["value"]) * 100, 1),
                "questions": int(b["questionsAttempted"]["value"])
            })
        return Response(data)


class StudentFrequentlyWrongView(APIView):
    def get(self, request):
        user_uri = f"http://example.com/sotis/user/{request.user.username}"
        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>
        SELECT ?questionText (COUNT(?wrong) AS ?wrongCount)
        WHERE {{
          GRAPH <http://example.com/sotis/graph> {{
            ?attempt lom:contributor <{user_uri}> ;
                     sotis:hasAnswer ?ans .
            ?ans sotis:question ?q ;
                 sotis:answer ?given .
            ?q lom:title ?questionText ;
               sotis:correctAnswer ?correct .
            FILTER(STR(?given) != STR(?correct))
            BIND(1 AS ?wrong)
          }}
        }}
        GROUP BY ?q ?questionText
        ORDER BY DESC(?wrongCount)
        LIMIT 10
        """
        results = execute_select(query)
        data = [
            {
                "question": b["questionText"]["value"][:80] + "..." if len(b["questionText"]["value"]) > 80 else b["questionText"]["value"],
                "wrong_times": int(b["wrongCount"]["value"])
            }
            for b in results["results"]["bindings"]
        ]
        return Response(data)


class StudentRankingView(APIView):
    def get(self, request):
        user_uri = f"http://example.com/sotis/user/{request.user.username}"
        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>
        SELECT ?studentName (AVG(?score) AS ?avgScore)
        WHERE {{
          GRAPH <http://example.com/sotis/graph> {{
            ?attempt rdf:type sotis:TestAttempt ;
                     lom:contributor ?student ;
                     lom:description ?desc .
            ?student lom:title ?studentName .
            BIND(REPLACE(STR(?desc), ".*Score: ([0-9.]+(\\.[0-9]+)?).*", "$1") AS ?raw)
            BIND(xsd:float(?raw) AS ?score)
          }}
        }}
        GROUP BY ?student ?studentName
        ORDER BY DESC(?avgScore)
        """
        results = execute_select(query)
        ranked = []
        my_rank = None
        my_score = None
        for i, b in enumerate(results["results"]["bindings"], 1):
            name = b["studentName"]["value"]
            score = round(float(b["avgScore"]["value"]), 1)
            ranked.append({"rank": i, "name": name, "score": score})
            if request.user.username in name or str(request.user.username) in name:
                my_rank = i
                my_score = score
        return Response({
            "my_rank": my_rank or "N/A",
            "my_score": my_score or 0,
            "total_students": len(ranked),
            "top_5": ranked[:5]
        })


class StudentRecommendationsView(APIView):
    def get(self, request):
        user_uri = f"http://example.com/sotis/user/{request.user.username}"
        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>
        SELECT ?nodeTitle (AVG(?correct) AS ?mastery)
        WHERE {{
          GRAPH <http://example.com/sotis/graph> {{
            ?attempt lom:contributor <{user_uri}> ;
                     sotis:hasAnswer ?ans .
            ?ans sotis:question ?q ;
                 sotis:answer ?given .
            ?q lom:partOf ?node ;
               sotis:correctAnswer ?correct .
            ?node lom:title ?nodeTitle .
            BIND(IF(STR(?given) = STR(?correct), 1.0, 0.0) AS ?correct)
          }}
        }}
        GROUP BY ?nodeTitle
        HAVING (AVG(?correct) < 0.7)
        ORDER BY ?mastery
        LIMIT 5
        """
        results = execute_select(query)
        data = [
            {
                "topic": b["nodeTitle"]["value"],
                "mastery_percent": round(float(b["mastery"]["value"]) * 100, 1)
            }
            for b in results["results"]["bindings"]
        ]
        return Response(data)


class StudentCompletionRateView(APIView):
    def get(self, request):
        user_uri = f"http://example.com/sotis/user/{request.user.username}"
        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>
        SELECT (COUNT(?completed) AS ?done) (COUNT(?all) AS ?total)
        WHERE {{
          GRAPH <http://example.com/sotis/graph> {{
            ?attempt lom:contributor <{user_uri}> .
            OPTIONAL {{ ?attempt lom:status "lom:Final" . BIND(1 AS ?completed) }}
            BIND(1 AS ?all)
          }}
        }}
        """
        results = execute_select(query)
        b = results["results"]["bindings"][0]
        done = int(b["done"]["value"])
        total = int(b["total"]["value"])
        rate = round(done / total * 100, 1) if total > 0 else 0
        return Response({
            "completed": done,
            "started": total,
            "completion_rate_percent": rate
        })


class StudentRecentTestsView(APIView):
    def get(self, request):
        user_uri = f"http://example.com/sotis/user/{request.user.username}"
        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>
        SELECT ?testTitle ?date ?desc
        WHERE {{
          GRAPH <http://example.com/sotis/graph> {{
            ?attempt lom:contributor <{user_uri}> ;
                     lom:partOf ?test ;
                     lom:description ?desc ;
                     lom:date ?date .
            ?test lom:title ?testTitle .
          }}
        }}
        ORDER BY DESC(?date)
        LIMIT 5
        """
        results = execute_select(query)
        data = []
        for b in results["results"]["bindings"]:
            desc = b["desc"]["value"]
            match = re.search(r"Score: (\d+\.?\d*)", desc)
            score = float(match.group(1)) if match else 0
            data.append({
                "test": b["testTitle"]["value"],
                "date": b["date"]["value"][:10],
                "score": score
            })
        return Response(data)


# ------------------------------------------------------------------
# TEACHER-FACING ANALYTICS (8 views)
# ------------------------------------------------------------------

class ClassAveragePerTestView(APIView):
    def get(self, request):
        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>
        SELECT ?testTitle (AVG(?score) AS ?avgScore) (COUNT(?attempt) AS ?participants)
        WHERE {{
          GRAPH <http://example.com/sotis/graph> {{
            ?attempt lom:partOf ?test ;
                     lom:description ?desc .
            ?test lom:title ?testTitle .
            BIND(REPLACE(STR(?desc), ".*Score: ([0-9.]+(\\.[0-9]+)?).*", "$1") AS ?raw)
            BIND(xsd:float(?raw) AS ?score)
          }}
        }}
        GROUP BY ?test ?testTitle
        ORDER BY DESC(?avgScore)
        """
        results = execute_select(query)
        data = [
            {
                "test": b["testTitle"]["value"],
                "average_score": round(float(b["avgScore"]["value"]), 1),
                "participants": int(b["participants"]["value"])
            }
            for b in results["results"]["bindings"]
        ]
        return Response(data)


class ClassHardestQuestionsView(APIView):
    def get(self, request):
        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>
        SELECT ?questionText (COUNT(?wrong) AS ?wrongCount) (COUNT(?total) AS ?attempted)
        WHERE {{
          GRAPH <http://example.com/sotis/graph> {{
            ?attempt sotis:hasAnswer ?ans .
            ?ans sotis:question ?q ;
                 sotis:answer ?given .
            ?q lom:title ?questionText ;
               sotis:correctAnswer ?correct .
            BIND(IF(STR(?given) != STR(?correct), 1, 0) AS ?wrong)
            BIND(1 AS ?total)
          }}
        }}
        GROUP BY ?q ?questionText
        HAVING (COUNT(?total) > 2)
        ORDER BY DESC(?wrongCount)
        LIMIT 15
        """
        results = execute_select(query)
        data = []
        for b in results["results"]["bindings"]:
            wrong = int(b["wrongCount"]["value"])
            total = int(b["attempted"]["value"])
            data.append({
                "question": b["questionText"]["value"][:70] + "..." if len(b["questionText"]["value"]) > 70 else b["questionText"]["value"],
                "difficulty_percent": round(wrong / total * 100, 1),
                "wrong": wrong,
                "attempted": total
            })
        return Response(data)


class StudentsNeedingHelpView(APIView):
    def get(self, request):
        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>
        SELECT ?studentName (AVG(?score) AS ?avgScore) (COUNT(?attempt) AS ?tests)
        WHERE {{
          GRAPH <http://example.com/sotis/graph> {{
            ?attempt lom:contributor ?student ;
                     lom:description ?desc .
            ?student lom:title ?studentName .
            BIND(REPLACE(STR(?desc), ".*Score: ([0-9.]+(\\.[0-9]+)?).*", "$1") AS ?raw)
            BIND(xsd:float(?raw) AS ?score)
          }}
        }}
        GROUP BY ?student ?studentName
        HAVING (AVG(?score) < 60 && COUNT(?attempt) >= 2)
        ORDER BY ?avgScore
        LIMIT 10
        """
        results = execute_select(query)
        data = [
            {
                "name": b["studentName"]["value"],
                "average_score": round(float(b["avgScore"]["value"]), 1),
                "tests_taken": int(b["tests"]["value"])
            }
            for b in results["results"]["bindings"]
        ]
        return Response(data)


class ClassTopicMasteryView(APIView):
    def get(self, request):
        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>
        SELECT ?nodeTitle (AVG(?correct) AS ?classMastery)
        WHERE {{
          GRAPH <http://example.com/sotis/graph> {{
            ?attempt sotis:hasAnswer ?ans .
            ?ans sotis:question ?q ;
                 sotis:answer ?given .
            ?q lom:partOf ?node ;
               sotis:correctAnswer ?correct .
            ?node lom:title ?nodeTitle .
            BIND(IF(STR(?given) = STR(?correct), 1.0, 0.0) AS ?correct)
          }}
        }}
        GROUP BY ?nodeTitle
        ORDER BY DESC(?classMastery)
        """
        results = execute_select(query)
        data = [
            {
                "topic": b["nodeTitle"]["value"],
                "class_mastery_percent": round(float(b["classMastery"]["value"]) * 100, 1)
            }
            for b in results["results"]["bindings"]
        ]
        return Response(data)


class TestParticipationView(APIView):
    def get(self, request):
        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>
        SELECT ?testTitle (COUNT(?attempt) AS ?participants)
        WHERE {{
          GRAPH <http://example.com/sotis/graph> {{
            ?attempt lom:partOf ?test .
            ?test lom:title ?testTitle .
          }}
        }}
        GROUP BY ?testTitle
        ORDER BY DESC(?participants)
        """
        results = execute_select(query)
        data = [
            {
                "test": b["testTitle"]["value"],
                "participants": int(b["participants"]["value"])
            }
            for b in results["results"]["bindings"]
        ]
        return Response(data)

class MostImprovedStudentsView(APIView):
    permission_classes = [IsTeacher]

    def get(self, request):
        teacher_uri = f"<http://example.com/sotis#user/{request.user.username}>"

        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        SELECT ?student ?studentName ?latestDate ?latestScore ?prevDate ?prevScore
        WHERE {{
            {{
                SELECT ?student ?date ?score
                WHERE {{
                    GRAPH <http://example.com/sotis/graph> {{
                        ?test lom:contributor {teacher_uri} .
                        ?attempt a sotis:TestAttempt ;
                                 lom:contributor ?student ;
                                 lom:partOf ?test ;
                                 sotis:score ?score ;
                                 lom:date ?date .
                    }}
                }}
                ORDER BY DESC(?date)
                LIMIT 2
            }}

            BIND(?date AS ?latestDate)
            BIND(?score AS ?latestScore)

            {{
                SELECT ?student ?date ?score
                WHERE {{
                    GRAPH <http://example.com/sotis/graph> {{
                        ?test lom:contributor {teacher_uri} .
                        ?attempt a sotis:TestAttempt ;
                                 lom:contributor ?student ;
                                 lom:partOf ?test ;
                                 sotis:score ?score ;
                                 lom:date ?date .
                    }}
                }}
                ORDER BY DESC(?date)
                OFFSET 1
                LIMIT 1
            }}
            BIND(?date AS ?prevDate)
            BIND(?score AS ?prevScore)

            GRAPH <http://example.com/sotis/graph> {{
                ?student lom:title ?studentName .
            }}

            FILTER(BOUND(?latestScore) && BOUND(?prevScore))
            FILTER(?latestScore > ?prevScore)
        }}
        ORDER BY DESC(?latestScore - ?prevScore)
        LIMIT 10
        """

        results = execute_select(query)

        data = []
        for b in results["results"]["bindings"]:
            latest_dt = datetime.datetime.fromisoformat(b["latestDate"]["value"])
            prev_dt   = datetime.datetime.fromisoformat(b["prevDate"]["value"])

            improvement = float(b["latestScore"]["value"]) - float(b["prevScore"]["value"])

            data.append({
                "student": b["studentName"]["value"],
                "previous_attempt_date": prev_dt.strftime("%Y-%m-%d"),
                "latest_attempt_date": latest_dt.strftime("%Y-%m-%d"),
                "previous_score": round(float(b["prevScore"]["value"]), 1),
                "latest_score": round(float(b["latestScore"]["value"]), 1),
                "improvement": round(improvement, 1),
                "days_between_attempts": (latest_dt - prev_dt).days
            })

        return Response(data)


class DiscriminatingQuestionsView(APIView):

    def get(self, request):
        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>
        SELECT ?questionText (AVG(?correct) AS ?pValue)
        WHERE {{
          GRAPH <http://example.com/sotis/graph> {{
            ?attempt sotis:hasAnswer ?ans .
            ?ans sotis:question ?q ;
                 sotis:answer ?given .
            ?q lom:title ?questionText ;
               sotis:correctAnswer ?correct .
            BIND(IF(STR(?given) = STR(?correct), 1.0, 0.0) AS ?correct)
          }}
        }}
        GROUP BY ?q ?questionText
        HAVING (COUNT(*) > 5)
        ORDER BY ABS(0.5 - AVG(?correct)) DESC
        LIMIT 10
        """
        results = execute_select(query)
        data = [
            {
                "question": b["questionText"]["value"][:70] + "..." if len(b["questionText"]["value"]) > 70 else b["questionText"]["value"],
                "difficulty_percent": round(float(b["pValue"]["value"]) * 100, 1)
            }
            for b in results["results"]["bindings"]
        ]
        return Response(data)


class ClassScoreDistributionView(APIView):

    def get(self, request):
        query = f"""
        PREFIX lom: <http://ltsc.ieee.org/xsd/LOM#>
        PREFIX sotis: <http://example.com/sotis#>
        SELECT ?desc
        WHERE {{
          GRAPH <http://example.com/sotis/graph> {{
            ?attempt lom:description ?desc .
          }}
        }}
        """
        results = execute_select(query)
        scores = []
        for b in results["results"]["bindings"]:
            match = re.search(r"Score: (\d+\.?\d*)", b["desc"]["value"])
            if match:
                scores.append(float(match.group(1)))

        bins = [0, 50, 60, 70, 80, 90, 100]
        labels = ["0-49", "50-59", "60-69", "70-79", "80-89", "90-100"]
        hist, _ = np.histogram(scores, bins=bins)
        data = [{"range": l, "count": int(c)} for l, c in zip(labels, hist)]
        return Response(data)