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
        user_uri = f"{SOTIS_NS}user/{request.user.id}"
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
                             lom:contributor <{SOTIS_NS}user/{request.user.id}> ;
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
                                     lom:contributor <{SOTIS_NS}user/{request.user.id}> ;
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
                                 lom:contributor <{SOTIS_NS}user/{self.request.user.id}> ;
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
                                 lom:contributor <{SOTIS_NS}user/{self.request.user.id}> ;
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
                                     lom:contributor <{SOTIS_NS}user/{self.request.user.id}> ;
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
            user_uri = f"{SOTIS_NS}user/{request.user.id}"
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
            student_uri = f"{SOTIS_NS}user/{request.user.id}"
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
            student_uri = f"{SOTIS_NS}user/{request.user.id}"
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
