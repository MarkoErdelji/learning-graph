from django.core.management.base import BaseCommand
import uuid
import datetime
from django.contrib.auth import get_user_model
from app.models import KnowledgeGraph, Node, Question, Test, TestQuestion, TestAttempt
from app.utils import execute_update

SOTIS_GRAPH = 'http://example.com/sotis/graph'
SOTIS_NS = 'http://example.com/sotis#'
LOM_NS = 'http://ltsc.ieee.org/xsd/LOM#'

AppUser = get_user_model()

# Helper functions for URIs
def generate_user_uri(username):
    return f'{SOTIS_NS}user/{username}'

def generate_kg_uri():
    return f'{SOTIS_NS}kg/{uuid.uuid4()}'

def generate_node_uri():
    return f'{SOTIS_NS}node/{uuid.uuid4()}'

def generate_question_uri():
    return f'{SOTIS_NS}question/{uuid.uuid4()}'

def generate_test_uri():
    return f'{SOTIS_NS}test/{uuid.uuid4()}'

def generate_test_attempt_uri():
    return f'{SOTIS_NS}attempt/{uuid.uuid4()}'

class Command(BaseCommand):
    help = 'Seeds the database with extensive sample data for users, graphs, nodes, questions, tests, and attempts'

    def handle(self, *args, **options):
        # Create users
        users_data = [
            {'username': 'teacher1', 'email': 'teacher1@example.com', 'user_type': 'Teacher', 'first_name': 'Teacher', 'last_name': 'One'},
            {'username': 'teacher2', 'email': 'teacher2@example.com', 'user_type': 'Teacher', 'first_name': 'Teacher', 'last_name': 'Two'},
            {'username': 'teacher3', 'email': 'teacher3@example.com', 'user_type': 'Teacher', 'first_name': 'Teacher', 'last_name': 'Three'},
            {'username': 'expert1', 'email': 'expert1@example.com', 'user_type': 'Expert', 'first_name': 'Expert', 'last_name': 'One'},
            {'username': 'expert2', 'email': 'expert2@example.com', 'user_type': 'Expert', 'first_name': 'Expert', 'last_name': 'Two'},
            {'username': 'student1', 'email': 'student1@example.com', 'user_type': 'Student', 'first_name': 'Student', 'last_name': 'One'},
            {'username': 'student2', 'email': 'student2@example.com', 'user_type': 'Student', 'first_name': 'Student', 'last_name': 'Two'},
            {'username': 'student3', 'email': 'student3@example.com', 'user_type': 'Student', 'first_name': 'Student', 'last_name': 'Three'},
            {'username': 'student4', 'email': 'student4@example.com', 'user_type': 'Student', 'first_name': 'Student', 'last_name': 'Four'},
            {'username': 'student5', 'email': 'student5@example.com', 'user_type': 'Student', 'first_name': 'Student', 'last_name': 'Five'},
            {'username': 'student6', 'email': 'student6@example.com', 'user_type': 'Student', 'first_name': 'Student', 'last_name': 'Six'},
            {'username': 'student7', 'email': 'student7@example.com', 'user_type': 'Student', 'first_name': 'Student', 'last_name': 'Seven'},
            {'username': 'student8', 'email': 'student8@example.com', 'user_type': 'Student', 'first_name': 'Student', 'last_name': 'Eight'},
            {'username': 'student9', 'email': 'student9@example.com', 'user_type': 'Student', 'first_name': 'Student', 'last_name': 'Nine'},
            {'username': 'student10', 'email': 'student10@example.com', 'user_type': 'Student', 'first_name': 'Student', 'last_name': 'Ten'},
        ]

        users = {}
        for data in users_data:
            user, created = AppUser.objects.get_or_create(username=data['username'], defaults={
                'email': data['email'],
                'user_type': data['user_type'].replace('lom:', ''),
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'uri': generate_user_uri(data['username']),
            })
            if created:
                user.set_password('123')
                user.save()
            users[data['username']] = user

            user_uri = user.uri
            query_user = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX sotis: <{SOTIS_NS}>
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                    <{user_uri}> rdf:type sotis:User ;
                                 lom:identifier "{user_uri}" ;
                                 lom:title "{user.username}" ;
                                 lom:intendedEndUserRole lom:{data['user_type']} .
                }}
            }}
            """
            execute_update(query_user)

        # Graph 1: Math Basics by teacher1
        graph1_id = uuid.uuid4()
        graph1_uri = generate_kg_uri()
        graph1 = KnowledgeGraph.objects.create(
            id=graph1_id, uri=graph1_uri, title='Math Basics', author=users['teacher1'],
            description='Foundational arithmetic concepts', keyword='math', version='1.0', status='lom:Final',
            difficulty='lom:Easy', context='lom:School', intended_end_user_role='lom:Student',
            typical_age_range='10-15', typical_learning_time='PT2H'
        )
        query_graph1 = f"""
        PREFIX lom: <{LOM_NS}>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX sotis: <{SOTIS_NS}>
        INSERT DATA {{
            GRAPH <{SOTIS_GRAPH}> {{
                <{graph1_uri}> rdf:type sotis:KnowledgeGraph ;
                               lom:identifier "{graph1_uri}" ;
                               lom:title "{graph1.title}" ;
                               lom:contributor <{users['teacher1'].uri}> ;
                               lom:learningResourceType lom:Graph ;
                               lom:language "{graph1.language or 'en'}" ;
                               lom:description "{graph1.description}" ;
                               lom:keyword "{graph1.keyword}" ;
                               lom:version "{graph1.version}" ;
                               lom:status "{graph1.status}" ;
                               lom:date "{datetime.datetime.now().isoformat()}" ;
                               lom:difficulty {graph1.difficulty} ;
                               lom:context {graph1.context} ;
                               lom:intendedEndUserRole {graph1.intended_end_user_role} ;
                               lom:typicalAgeRange "{graph1.typical_age_range}" ;
                               lom:typicalLearningTime "{graph1.typical_learning_time}" .
            }}
        }}
        """
        execute_update(query_graph1)

        # Nodes for Graph 1
        node_data_graph1 = [
            {'title': 'Addition', 'description': 'Adding numbers'},
            {'title': 'Subtraction', 'description': 'Subtracting numbers'},
            {'title': 'Multiplication', 'description': 'Multiplying numbers', 'prereqs': ['Addition', 'Subtraction']},
            {'title': 'Division', 'description': 'Dividing numbers', 'prereqs': ['Addition', 'Subtraction']},
            {'title': 'Fractions', 'description': 'Understanding fractions', 'prereqs': ['Multiplication', 'Division']},
            {'title': 'Decimals', 'description': 'Working with decimals', 'prereqs': ['Fractions']},
        ]

        nodes_graph1 = {}
        for data in node_data_graph1:
            node_id = uuid.uuid4()
            node_uri = generate_node_uri()
            node = Node.objects.create(
                id=node_id, uri=node_uri, title=data['title'], graph=graph1, graph_uri=graph1_uri,
                description=data['description'], keyword='math node', version='1.0', status='lom:Final',
                difficulty='lom:Easy', context='lom:School', intended_end_user_role='lom:Student',
                typical_age_range='10-15', typical_learning_time='PT30M'
            )
            nodes_graph1[data['title']] = node

            query_node = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX sotis: <{SOTIS_NS}>
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                    <{node_uri}> rdf:type sotis:Node ;
                                 lom:identifier "{node_uri}" ;
                                 lom:title "{node.title}" ;
                                 lom:partOf <{graph1_uri}> ;
                                 lom:learningResourceType lom:Narrative_Text ;
                                 lom:language "{node.language or 'en'}" ;
                                 lom:description "{node.description}" ;
                                 lom:keyword "{node.keyword}" ;
                                 lom:version "{node.version}" ;
                                 lom:status "{node.status}" ;
                                 lom:contributor <{users['teacher1'].uri}> ;
                                 lom:date "{datetime.datetime.now().isoformat()}" ;
                                 lom:difficulty {node.difficulty} ;
                                 lom:context {node.context} ;
                                 lom:intendedEndUserRole {node.intended_end_user_role} ;
                                 lom:typicalAgeRange "{node.typical_age_range}" ;
                                 lom:typicalLearningTime "{node.typical_learning_time}" .
                }}
            }}
            """
            execute_update(query_node)

            if 'prereqs' in data:
                for prereq_title in data['prereqs']:
                    prereq_node = nodes_graph1[prereq_title]
                    node.prerequisite_nodes.add(prereq_node)
                    query_rel = f"""
                    PREFIX lom: <{LOM_NS}>
                    INSERT DATA {{
                        GRAPH <{SOTIS_GRAPH}> {{
                            <{node_uri}> lom:requires <{prereq_node.uri}> .
                        }}
                    }}
                    """
                    execute_update(query_rel)

        # Questions for Graph 1 nodes
        questions_data_graph1 = [
            {'node_title': 'Addition', 'text': 'What is 2 + 2?', 'correct': '4', 'others': ['3', '5', '6']},
            {'node_title': 'Addition', 'text': 'What is 7 + 8?', 'correct': '15', 'others': ['14', '16', '17']},
            {'node_title': 'Subtraction', 'text': 'What is 5 - 3?', 'correct': '2', 'others': ['1', '3', '4']},
            {'node_title': 'Subtraction', 'text': 'What is 10 - 4?', 'correct': '6', 'others': ['5', '7', '8']},
            {'node_title': 'Multiplication', 'text': 'What is 3 * 4?', 'correct': '12', 'others': ['7', '10', '15']},
            {'node_title': 'Multiplication', 'text': 'What is 6 * 7?', 'correct': '42', 'others': ['36', '48', '49']},
            {'node_title': 'Division', 'text': 'What is 12 / 3?', 'correct': '4', 'others': ['3', '5', '6']},
            {'node_title': 'Division', 'text': 'What is 15 / 5?', 'correct': '3', 'others': ['2', '4', '5']},
            {'node_title': 'Fractions', 'text': 'What is 1/2 + 1/4?', 'correct': '3/4', 'others': ['1/2', '1/4', '1']},
            {'node_title': 'Fractions', 'text': 'What is 3/4 * 2/3?', 'correct': '1/2', 'others': ['1/3', '2/3', '3/4']},
            {'node_title': 'Decimals', 'text': 'What is 0.5 + 0.3?', 'correct': '0.8', 'others': ['0.7', '0.9', '1.0']},
            {'node_title': 'Decimals', 'text': 'What is 1.2 * 2?', 'correct': '2.4', 'others': ['2.2', '2.6', '2.8']},
        ]

        questions_graph1 = {}
        for data in questions_data_graph1:
            q_id = uuid.uuid4()
            q_uri = generate_question_uri()
            node = nodes_graph1[data['node_title']]
            question = Question.objects.create(
                id=q_id, uri=q_uri, text=data['text'], correct_answer=data['correct'], other_answers=data['others'],
                node=node, node_uri=node.uri, keyword='math question', version='1.0', status='lom:Final',
                difficulty='lom:Easy', context='lom:School', intended_end_user_role='lom:Student',
                typical_age_range='10-15', typical_learning_time='PT5M'
            )
            questions_graph1[data['text']] = question

            query_q = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX sotis: <{SOTIS_NS}>
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                    <{q_uri}> rdf:type sotis:Question ;
                              lom:identifier "{q_uri}" ;
                              lom:title "{question.text[:50]}" ;
                              lom:partOf <{node.uri}> ;
                              lom:learningResourceType lom:Questionnaire ;
                              lom:language "{question.language or 'en'}" ;
                              lom:description "{question.text}" ;
                              lom:keyword "{question.keyword}" ;
                              lom:version "{question.version}" ;
                              lom:status "{question.status}" ;
                              lom:contributor <{users['teacher1'].uri}> ;
                              lom:date "{datetime.datetime.now().isoformat()}" ;
                              lom:difficulty {question.difficulty} ;
                              lom:context {question.context} ;
                              lom:intendedEndUserRole {question.intended_end_user_role} ;
                              lom:typicalAgeRange "{question.typical_age_range}" ;
                              lom:typicalLearningTime "{question.typical_learning_time}" ;
                              sotis:correctAnswer "{question.correct_answer}" ;
                              sotis:otherAnswers "{', '.join(question.other_answers)}" .
                }}
            }}
            """
            execute_update(query_q)

        # Tests for Graph 1
        test1a_id = uuid.uuid4()
        test1a_uri = generate_test_uri()
        test1a = Test.objects.create(
            id=test1a_id, uri=test1a_uri, title='Math Basics Test A', author=users['teacher1'],
            graph=graph1, graph_uri=graph1_uri, description='Test on basic math (part A)',
            keyword='math test', version='1.0', status='lom:Final', difficulty='lom:Easy',
            context='lom:School', intended_end_user_role='lom:Student', typical_age_range='10-15',
            typical_learning_time='PT30M'
        )
        query_test1a = f"""
        PREFIX lom: <{LOM_NS}>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX sotis: <{SOTIS_NS}>
        INSERT DATA {{
            GRAPH <{SOTIS_GRAPH}> {{
                <{test1a_uri}> rdf:type sotis:Test ;
                              lom:identifier "{test1a_uri}" ;
                              lom:title "{test1a.title}" ;
                              lom:contributor <{users['teacher1'].uri}> ;
                              lom:partOf <{graph1_uri}> ;
                              lom:learningResourceType lom:Questionnaire ;
                              lom:language "{test1a.language or 'en'}" ;
                              lom:description "{test1a.description}" ;
                              lom:keyword "{test1a.keyword}" ;
                              lom:version "{test1a.version}" ;
                              lom:status "{test1a.status}" ;
                              lom:date "{datetime.datetime.now().isoformat()}" ;
                              lom:difficulty {test1a.difficulty} ;
                              lom:context {test1a.context} ;
                              lom:intendedEndUserRole {test1a.intended_end_user_role} ;
                              lom:typicalAgeRange "{test1a.typical_age_range}" ;
                              lom:typicalLearningTime "{test1a.typical_learning_time}" .
            }}
        }}
        """
        execute_update(query_test1a)

        test1b_id = uuid.uuid4()
        test1b_uri = generate_test_uri()
        test1b = Test.objects.create(
            id=test1b_id, uri=test1b_uri, title='Math Basics Test B', author=users['teacher1'],
            graph=graph1, graph_uri=graph1_uri, description='Test on basic math (part B)',
            keyword='math test', version='1.0', status='lom:Final', difficulty='lom:Easy',
            context='lom:School', intended_end_user_role='lom:Student', typical_age_range='10-15',
            typical_learning_time='PT30M'
        )
        query_test1b = f"""
        PREFIX lom: <{LOM_NS}>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX sotis: <{SOTIS_NS}>
        INSERT DATA {{
            GRAPH <{SOTIS_GRAPH}> {{
                <{test1b_uri}> rdf:type sotis:Test ;
                              lom:identifier "{test1b_uri}" ;
                              lom:title "{test1b.title}" ;
                              lom:contributor <{users['teacher1'].uri}> ;
                              lom:partOf <{graph1_uri}> ;
                              lom:learningResourceType lom:Questionnaire ;
                              lom:language "{test1b.language or 'en'}" ;
                              lom:description "{test1b.description}" ;
                              lom:keyword "{test1b.keyword}" ;
                              lom:version "{test1b.version}" ;
                              lom:status "{test1b.status}" ;
                              lom:date "{datetime.datetime.now().isoformat()}" ;
                              lom:difficulty {test1b.difficulty} ;
                              lom:context {test1b.context} ;
                              lom:intendedEndUserRole {test1b.intended_end_user_role} ;
                              lom:typicalAgeRange "{test1b.typical_age_range}" ;
                              lom:typicalLearningTime "{test1b.typical_learning_time}" .
            }}
        }}
        """
        execute_update(query_test1b)

        # Add questions to Tests (Test A: first question per node, Test B: second question per node)
        for order, question in enumerate(list(questions_graph1.values())[::2], start=1):
            tq = TestQuestion.objects.create(test=test1a, question=question, order=order)
            query_tq = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX sotis: <{SOTIS_NS}>
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                    <{test1a_uri}> lom:hasQuestion <{question.uri}> .
                }}
            }}
            """
            execute_update(query_tq)
        for order, question in enumerate(list(questions_graph1.values())[1::2], start=1):
            tq = TestQuestion.objects.create(test=test1b, question=question, order=order)
            query_tq = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX sotis: <{SOTIS_NS}>
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                    <{test1b_uri}> lom:hasQuestion <{question.uri}> .
                }}
            }}
            """
            execute_update(query_tq)

        # Test Attempts for Test 1A
        attempts_data_test1a = [
            {'student': 'student1', 'answers': {str(questions_graph1['What is 2 + 2?'].id): '4', str(questions_graph1['What is 5 - 3?'].id): '2', str(questions_graph1['What is 3 * 4?'].id): '12', str(questions_graph1['What is 12 / 3?'].id): '4', str(questions_graph1['What is 1/2 + 1/4?'].id): '3/4', str(questions_graph1['What is 0.5 + 0.3?'].id): '0.8'}},  # 100%
            {'student': 'student2', 'answers': {str(questions_graph1['What is 2 + 2?'].id): '3', str(questions_graph1['What is 5 - 3?'].id): '2', str(questions_graph1['What is 3 * 4?'].id): '10', str(questions_graph1['What is 12 / 3?'].id): '3', str(questions_graph1['What is 1/2 + 1/4?'].id): '1/2', str(questions_graph1['What is 0.5 + 0.3?'].id): '0.7'}},  # ~33%
            {'student': 'student3', 'answers': {str(questions_graph1['What is 2 + 2?'].id): '4', str(questions_graph1['What is 5 - 3?'].id): '1', str(questions_graph1['What is 3 * 4?'].id): '12', str(questions_graph1['What is 12 / 3?'].id): '4', str(questions_graph1['What is 1/2 + 1/4?'].id): '1/4', str(questions_graph1['What is 0.5 + 0.3?'].id): '0.8'}},  # ~67%
            {'student': 'student4', 'answers': {str(questions_graph1['What is 2 + 2?'].id): '4', str(questions_graph1['What is 5 - 3?'].id): '2', str(questions_graph1['What is 3 * 4?'].id): '15', str(questions_graph1['What is 12 / 3?'].id): '4', str(questions_graph1['What is 1/2 + 1/4?'].id): '3/4', str(questions_graph1['What is 0.5 + 0.3?'].id): '0.9'}},  # ~83%
            {'student': 'student5', 'answers': {str(questions_graph1['What is 2 + 2?'].id): '5', str(questions_graph1['What is 5 - 3?'].id): '3', str(questions_graph1['What is 3 * 4?'].id): '10', str(questions_graph1['What is 12 / 3?'].id): '5', str(questions_graph1['What is 1/2 + 1/4?'].id): '1', str(questions_graph1['What is 0.5 + 0.3?'].id): '1.0'}},  # 0%
        ]

        for data in attempts_data_test1a:
            attempt_id = uuid.uuid4()
            attempt_uri = generate_test_attempt_uri()
            attempt = TestAttempt.objects.create(
                id=attempt_id, uri=attempt_uri, student=users[data['student']], test=test1a,
                answers=data['answers'], completed=True, description='Seeded attempt',
                version='1.0', status='lom:Final'
            )
            attempt.calculate_score()

            query_attempt = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX sotis: <{SOTIS_NS}>
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                <{attempt_uri}> rdf:type sotis:TestAttempt ;
                                        lom:identifier "{attempt_uri}" ;
                                        lom:contributor <{users[data['student']].uri}> ;
                                        lom:partOf <{test1a_uri}> ;
                                        lom:description "Seeded attempt" ;
                                        sotis:score "{attempt.score}"^^xsd:float ;
                                        lom:version "{attempt.version}" ;
                                        lom:date "{datetime.datetime.now().isoformat()}" ;
                                        lom:status "{attempt.status}" .
                }}
            }}
            """
            execute_update(query_attempt)

            for qid, answer in data['answers'].items():
                question = TestQuestion.objects.get(test=test1a, question__id=uuid.UUID(qid)).question
                is_correct = "1" if answer == question.correct_answer else "0"  # or True/False as string

                query_answer = f"""
                PREFIX lom: <{LOM_NS}>
                PREFIX sotis: <{SOTIS_NS}>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                INSERT DATA {{
                    GRAPH <{SOTIS_GRAPH}> {{
                        <{attempt_uri}> sotis:hasAnswer [
                            sotis:question <{question.uri}> ;
                            sotis:answer "{answer}" ;
                            sotis:isCorrect "{is_correct}"^^xsd:boolean
                        ] .
                    }}
                }}
                """
                execute_update(query_answer)

        # Test Attempts for Test 1B
        attempts_data_test1b = [
            {'student': 'student6', 'answers': {str(questions_graph1['What is 7 + 8?'].id): '15', str(questions_graph1['What is 10 - 4?'].id): '6', str(questions_graph1['What is 6 * 7?'].id): '42', str(questions_graph1['What is 15 / 5?'].id): '3', str(questions_graph1['What is 3/4 * 2/3?'].id): '1/2', str(questions_graph1['What is 1.2 * 2?'].id): '2.4'}},  # 100%
            {'student': 'student7', 'answers': {str(questions_graph1['What is 7 + 8?'].id): '14', str(questions_graph1['What is 10 - 4?'].id): '6', str(questions_graph1['What is 6 * 7?'].id): '49', str(questions_graph1['What is 15 / 5?'].id): '4', str(questions_graph1['What is 3/4 * 2/3?'].id): '2/3', str(questions_graph1['What is 1.2 * 2?'].id): '2.6'}},  # ~33%
            {'student': 'student8', 'answers': {str(questions_graph1['What is 7 + 8?'].id): '15', str(questions_graph1['What is 10 - 4?'].id): '5', str(questions_graph1['What is 6 * 7?'].id): '42', str(questions_graph1['What is 15 / 5?'].id): '3', str(questions_graph1['What is 3/4 * 2/3?'].id): '1/3', str(questions_graph1['What is 1.2 * 2?'].id): '2.4'}},  # ~67%
            {'student': 'student9', 'answers': {str(questions_graph1['What is 7 + 8?'].id): '15', str(questions_graph1['What is 10 - 4?'].id): '6', str(questions_graph1['What is 6 * 7?'].id): '36', str(questions_graph1['What is 15 / 5?'].id): '3', str(questions_graph1['What is 3/4 * 2/3?'].id): '1/2', str(questions_graph1['What is 1.2 * 2?'].id): '2.8'}},  # ~83%
            {'student': 'student10', 'answers': {str(questions_graph1['What is 7 + 8?'].id): '16', str(questions_graph1['What is 10 - 4?'].id): '7', str(questions_graph1['What is 6 * 7?'].id): '48', str(questions_graph1['What is 15 / 5?'].id): '5', str(questions_graph1['What is 3/4 * 2/3?'].id): '3/4', str(questions_graph1['What is 1.2 * 2?'].id): '2.2'}},  # 0%
        ]

        for data in attempts_data_test1b:
            attempt_id = uuid.uuid4()
            attempt_uri = generate_test_attempt_uri()
            attempt = TestAttempt.objects.create(
                id=attempt_id, uri=attempt_uri, student=users[data['student']], test=test1b,
                answers=data['answers'], completed=True, description='Seeded attempt',
                version='1.0', status='lom:Final'
            )
            attempt.calculate_score()

            query_attempt = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX sotis: <{SOTIS_NS}>
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                <{attempt_uri}> rdf:type sotis:TestAttempt ;
                                        lom:identifier "{attempt_uri}" ;
                                        lom:contributor <{users[data['student']].uri}> ;
                                        lom:partOf <{test1b_uri}> ;
                                        lom:description "Seeded attempt" ;
                                        sotis:score "{attempt.score}"^^xsd:float ;
                                        lom:version "{attempt.version}" ;
                                        lom:date "{datetime.datetime.now().isoformat()}" ;
                                        lom:status "{attempt.status}" .
                }}
            }}
            """
            execute_update(query_attempt)

            for qid, answer in data['answers'].items():
                question = TestQuestion.objects.get(test=test1b, question__id=uuid.UUID(qid)).question
                is_correct = "1" if answer == question.correct_answer else "0"  # or True/False as string

                query_answer = f"""
                PREFIX lom: <{LOM_NS}>
                PREFIX sotis: <{SOTIS_NS}>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                INSERT DATA {{
                    GRAPH <{SOTIS_GRAPH}> {{
                        <{attempt_uri}> sotis:hasAnswer [
                            sotis:question <{question.uri}> ;
                            sotis:answer "{answer}" ;
                            sotis:isCorrect "{is_correct}"^^xsd:boolean
                        ] .
                    }}
                }}
                """
                execute_update(query_answer)


        # Graph 2: Biology Basics by teacher2
        graph2_id = uuid.uuid4()
        graph2_uri = generate_kg_uri()
        graph2 = KnowledgeGraph.objects.create(
            id=graph2_id, uri=graph2_uri, title='Biology Basics', author=users['teacher2'],
            description='Foundational biology concepts', keyword='biology', version='1.0', status='lom:Final',
            difficulty='lom:Medium', context='lom:Higher_Education', intended_end_user_role='lom:Student',
            typical_age_range='18-', typical_learning_time='PT3H'
        )
        query_graph2 = f"""
        PREFIX lom: <{LOM_NS}>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX sotis: <{SOTIS_NS}>
        INSERT DATA {{
            GRAPH <{SOTIS_GRAPH}> {{
                <{graph2_uri}> rdf:type sotis:KnowledgeGraph ;
                               lom:identifier "{graph2_uri}" ;
                               lom:title "{graph2.title}" ;
                               lom:contributor <{users['teacher2'].uri}> ;
                               lom:learningResourceType lom:Graph ;
                               lom:language "{graph2.language or 'en'}" ;
                               lom:description "{graph2.description}" ;
                               lom:keyword "{graph2.keyword}" ;
                               lom:version "{graph2.version}" ;
                               lom:status "{graph2.status}" ;
                               lom:date "{datetime.datetime.now().isoformat()}" ;
                               lom:difficulty {graph2.difficulty} ;
                               lom:context {graph2.context} ;
                               lom:intendedEndUserRole {graph2.intended_end_user_role} ;
                               lom:typicalAgeRange "{graph2.typical_age_range}" ;
                               lom:typicalLearningTime "{graph2.typical_learning_time}" .
            }}
        }}
        """
        execute_update(query_graph2)

        # Nodes for Graph 2
        node_data_graph2 = [
            {'title': 'Cells', 'description': 'Basic unit of life'},
            {'title': 'DNA', 'description': 'Genetic material', 'prereqs': ['Cells']},
            {'title': 'Protein Synthesis', 'description': 'Transcription and translation', 'prereqs': ['DNA']},
            {'title': 'Evolution', 'description': 'Natural selection', 'prereqs': ['DNA']},
            {'title': 'Ecology', 'description': 'Ecosystems and interactions', 'prereqs': ['Cells', 'Evolution']},
        ]

        nodes_graph2 = {}
        for data in node_data_graph2:
            node_id = uuid.uuid4()
            node_uri = generate_node_uri()
            node = Node.objects.create(
                id=node_id, uri=node_uri, title=data['title'], graph=graph2, graph_uri=graph2_uri,
                description=data['description'], keyword='biology node', version='1.0', status='lom:Final',
                difficulty='lom:Medium', context='lom:Higher_Education', intended_end_user_role='lom:Student',
                typical_age_range='18-', typical_learning_time='PT45M'
            )
            nodes_graph2[data['title']] = node

            query_node = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX sotis: <{SOTIS_NS}>
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                    <{node_uri}> rdf:type sotis:Node ;
                                 lom:identifier "{node_uri}" ;
                                 lom:title "{node.title}" ;
                                 lom:partOf <{graph2_uri}> ;
                                 lom:learningResourceType lom:Narrative_Text ;
                                 lom:language "{node.language or 'en'}" ;
                                 lom:description "{node.description}" ;
                                 lom:keyword "{node.keyword}" ;
                                 lom:version "{node.version}" ;
                                 lom:status "{node.status}" ;
                                 lom:contributor <{users['teacher2'].uri}> ;
                                 lom:date "{datetime.datetime.now().isoformat()}" ;
                                 lom:difficulty {node.difficulty} ;
                                 lom:context {node.context} ;
                                 lom:intendedEndUserRole {node.intended_end_user_role} ;
                                 lom:typicalAgeRange "{node.typical_age_range}" ;
                                 lom:typicalLearningTime "{node.typical_learning_time}" .
                }}
            }}
            """
            execute_update(query_node)

            if 'prereqs' in data:
                for prereq_title in data['prereqs']:
                    prereq_node = nodes_graph2[prereq_title]
                    node.prerequisite_nodes.add(prereq_node)
                    query_rel = f"""
                    PREFIX lom: <{LOM_NS}>
                    INSERT DATA {{
                        GRAPH <{SOTIS_GRAPH}> {{
                            <{node_uri}> lom:requires <{prereq_node.uri}> .
                        }}
                    }}
                    """
                    execute_update(query_rel)

        # Questions for Graph 2 nodes
        questions_data_graph2 = [
            {'node_title': 'Cells', 'text': 'What is the basic unit of life?', 'correct': 'Cell', 'others': ['Atom', 'Molecule', 'Organ']},
            {'node_title': 'Cells', 'text': 'What organelle is the powerhouse of the cell?', 'correct': 'Mitochondrion', 'others': ['Nucleus', 'Ribosome', 'Golgi']},
            {'node_title': 'DNA', 'text': 'What does DNA stand for?', 'correct': 'Deoxyribonucleic Acid', 'others': ['Deoxyribose Nucleic Acid', 'Ribonucleic Acid', 'Genetic Code']},
            {'node_title': 'DNA', 'text': 'What are the base pairs in DNA?', 'correct': 'AT, CG', 'others': ['AU, CG', 'AT, GU', 'AC, TG']},
            {'node_title': 'Protein Synthesis', 'text': 'What is the first step of protein synthesis?', 'correct': 'Transcription', 'others': ['Translation', 'Replication', 'Splicing']},
            {'node_title': 'Protein Synthesis', 'text': 'Where does translation occur?', 'correct': 'Ribosome', 'others': ['Nucleus', 'Mitochondrion', 'Endoplasmic Reticulum']},
            {'node_title': 'Evolution', 'text': 'Who proposed natural selection?', 'correct': 'Charles Darwin', 'others': ['Gregor Mendel', 'Albert Einstein', 'Isaac Newton']},
            {'node_title': 'Evolution', 'text': 'What is a key mechanism of evolution?', 'correct': 'Natural Selection', 'others': ['Genetic Drift', 'Mutation', 'All of the above']},
            {'node_title': 'Ecology', 'text': 'What is an ecosystem?', 'correct': 'Community of organisms and environment', 'others': ['Single species', 'Only plants', 'Only animals']},
            {'node_title': 'Ecology', 'text': 'What is a food web?', 'correct': 'Network of food chains', 'others': ['Single food chain', 'Plant cycle', 'Water cycle']},
        ]

        questions_graph2 = {}
        for data in questions_data_graph2:
            q_id = uuid.uuid4()
            q_uri = generate_question_uri()
            node = nodes_graph2[data['node_title']]
            question = Question.objects.create(
                id=q_id, uri=q_uri, text=data['text'], correct_answer=data['correct'], other_answers=data['others'],
                node=node, node_uri=node.uri, keyword='biology question', version='1.0', status='lom:Final',
                difficulty='lom:Medium', context='lom:Higher_Education', intended_end_user_role='lom:Student',
                typical_age_range='18-', typical_learning_time='PT10M'
            )
            questions_graph2[data['text']] = question

            query_q = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX sotis: <{SOTIS_NS}>
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                    <{q_uri}> rdf:type sotis:Question ;
                              lom:identifier "{q_uri}" ;
                              lom:title "{question.text[:50]}" ;
                              lom:partOf <{node.uri}> ;
                              lom:learningResourceType lom:Questionnaire ;
                              lom:language "{question.language or 'en'}" ;
                              lom:description "{question.text}" ;
                              lom:keyword "{question.keyword}" ;
                              lom:version "{question.version}" ;
                              lom:status "{question.status}" ;
                              lom:contributor <{users['teacher2'].uri}> ;
                              lom:date "{datetime.datetime.now().isoformat()}" ;
                              lom:difficulty {question.difficulty} ;
                              lom:context {question.context} ;
                              lom:intendedEndUserRole {question.intended_end_user_role} ;
                              lom:typicalAgeRange "{question.typical_age_range}" ;
                              lom:typicalLearningTime "{question.typical_learning_time}" ;
                              sotis:correctAnswer "{question.correct_answer}" ;
                              sotis:otherAnswers "{', '.join(question.other_answers)}" .
                }}
            }}
            """
            execute_update(query_q)

        # Tests for Graph 2
        test2a_id = uuid.uuid4()
        test2a_uri = generate_test_uri()
        test2a = Test.objects.create(
            id=test2a_id, uri=test2a_uri, title='Biology Basics Test A', author=users['teacher2'],
            graph=graph2, graph_uri=graph2_uri, description='Test on basic biology (part A)',
            keyword='biology test', version='1.0', status='lom:Final', difficulty='lom:Medium',
            context='lom:Higher_Education', intended_end_user_role='lom:Student', typical_age_range='18-',
            typical_learning_time='PT45M'
        )
        query_test2a = f"""
        PREFIX lom: <{LOM_NS}>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX sotis: <{SOTIS_NS}>
        INSERT DATA {{
            GRAPH <{SOTIS_GRAPH}> {{
                <{test2a_uri}> rdf:type sotis:Test ;
                              lom:identifier "{test2a_uri}" ;
                              lom:title "{test2a.title}" ;
                              lom:contributor <{users['teacher2'].uri}> ;
                              lom:partOf <{graph2_uri}> ;
                              lom:learningResourceType lom:Questionnaire ;
                              lom:language "{test2a.language or 'en'}" ;
                              lom:description "{test2a.description}" ;
                              lom:keyword "{test2a.keyword}" ;
                              lom:version "{test2a.version}" ;
                              lom:status "{test2a.status}" ;
                              lom:date "{datetime.datetime.now().isoformat()}" ;
                              lom:difficulty {test2a.difficulty} ;
                              lom:context {test2a.context} ;
                              lom:intendedEndUserRole {test2a.intended_end_user_role} ;
                              lom:typicalAgeRange "{test2a.typical_age_range}" ;
                              lom:typicalLearningTime "{test2a.typical_learning_time}" .
            }}
        }}
        """
        execute_update(query_test2a)

        test2b_id = uuid.uuid4()
        test2b_uri = generate_test_uri()
        test2b = Test.objects.create(
            id=test2b_id, uri=test2b_uri, title='Biology Basics Test B', author=users['teacher2'],
            graph=graph2, graph_uri=graph2_uri, description='Test on basic biology (part B)',
            keyword='biology test', version='1.0', status='lom:Final', difficulty='lom:Medium',
            context='lom:Higher_Education', intended_end_user_role='lom:Student', typical_age_range='18-',
            typical_learning_time='PT45M'
        )
        query_test2b = f"""
        PREFIX lom: <{LOM_NS}>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX sotis: <{SOTIS_NS}>
        INSERT DATA {{
            GRAPH <{SOTIS_GRAPH}> {{
                <{test2b_uri}> rdf:type sotis:Test ;
                              lom:identifier "{test2b_uri}" ;
                              lom:title "{test2b.title}" ;
                              lom:contributor <{users['teacher2'].uri}> ;
                              lom:partOf <{graph2_uri}> ;
                              lom:learningResourceType lom:Questionnaire ;
                              lom:language "{test2b.language or 'en'}" ;
                              lom:description "{test2b.description}" ;
                              lom:keyword "{test2b.keyword}" ;
                              lom:version "{test2b.version}" ;
                              lom:status "{test2b.status}" ;
                              lom:date "{datetime.datetime.now().isoformat()}" ;
                              lom:difficulty {test2b.difficulty} ;
                              lom:context {test2b.context} ;
                              lom:intendedEndUserRole {test2b.intended_end_user_role} ;
                              lom:typicalAgeRange "{test2b.typical_age_range}" ;
                              lom:typicalLearningTime "{test2b.typical_learning_time}" .
            }}
        }}
        """
        execute_update(query_test2b)

        # Add questions to Tests
        for order, question in enumerate(list(questions_graph2.values())[::2], start=1):
            tq = TestQuestion.objects.create(test=test2a, question=question, order=order)
            query_tq = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX sotis: <{SOTIS_NS}>
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                    <{test2a_uri}> lom:hasQuestion <{question.uri}> .
                }}
            }}
            """
            execute_update(query_tq)
        for order, question in enumerate(list(questions_graph2.values())[1::2], start=1):
            tq = TestQuestion.objects.create(test=test2b, question=question, order=order)
            query_tq = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX sotis: <{SOTIS_NS}>
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                    <{test2b_uri}> lom:hasQuestion <{question.uri}> .
                }}
            }}
            """
            execute_update(query_tq)

        # Test Attempts for Test 2A
        attempts_data_test2a = [
            {'student': 'student1', 'answers': {str(questions_graph2['What is the basic unit of life?'].id): 'Cell', str(questions_graph2['What does DNA stand for?'].id): 'Deoxyribonucleic Acid', str(questions_graph2['What is the first step of protein synthesis?'].id): 'Transcription', str(questions_graph2['Who proposed natural selection?'].id): 'Charles Darwin', str(questions_graph2['What is an ecosystem?'].id): 'Community of organisms and environment'}},  # 100%
            {'student': 'student2', 'answers': {str(questions_graph2['What is the basic unit of life?'].id): 'Atom', str(questions_graph2['What does DNA stand for?'].id): 'Deoxyribonucleic Acid', str(questions_graph2['What is the first step of protein synthesis?'].id): 'Translation', str(questions_graph2['Who proposed natural selection?'].id): 'Gregor Mendel', str(questions_graph2['What is an ecosystem?'].id): 'Single species'}},  # ~20%
            {'student': 'student3', 'answers': {str(questions_graph2['What is the basic unit of life?'].id): 'Cell', str(questions_graph2['What does DNA stand for?'].id): 'Ribonucleic Acid', str(questions_graph2['What is the first step of protein synthesis?'].id): 'Transcription', str(questions_graph2['Who proposed natural selection?'].id): 'Charles Darwin', str(questions_graph2['What is an ecosystem?'].id): 'Only plants'}},  # ~60%
            {'student': 'student4', 'answers': {str(questions_graph2['What is the basic unit of life?'].id): 'Cell', str(questions_graph2['What does DNA stand for?'].id): 'Deoxyribonucleic Acid', str(questions_graph2['What is the first step of protein synthesis?'].id): 'Replication', str(questions_graph2['Who proposed natural selection?'].id): 'Charles Darwin', str(questions_graph2['What is an ecosystem?'].id): 'Community of organisms and environment'}},  # ~80%
        ]

        for data in attempts_data_test2a:
            attempt_id = uuid.uuid4()
            attempt_uri = generate_test_attempt_uri()
            attempt = TestAttempt.objects.create(
                id=attempt_id, uri=attempt_uri, student=users[data['student']], test=test2a,
                answers=data['answers'], completed=True, description='Seeded attempt',
                version='1.0', status='lom:Final'
            )
            attempt.calculate_score()

            query_attempt = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX sotis: <{SOTIS_NS}>
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                <{attempt_uri}> rdf:type sotis:TestAttempt ;
                                        lom:identifier "{attempt_uri}" ;
                                        lom:contributor <{users[data['student']].uri}> ;
                                        lom:partOf <{test2a_uri}> ;
                                        lom:description "Seeded attempt" ;
                                        sotis:score "{attempt.score}"^^xsd:float ;
                                        lom:version "{attempt.version}" ;
                                        lom:date "{datetime.datetime.now().isoformat()}" ;
                                        lom:status "{attempt.status}" .
                }}
            }}
            """
            execute_update(query_attempt)

            for qid, answer in data['answers'].items():
                question = TestQuestion.objects.get(test=test2a, question__id=uuid.UUID(qid)).question
                is_correct = "1" if answer == question.correct_answer else "0"  # or True/False as string

                query_answer = f"""
                PREFIX lom: <{LOM_NS}>
                PREFIX sotis: <{SOTIS_NS}>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                INSERT DATA {{
                    GRAPH <{SOTIS_GRAPH}> {{
                        <{attempt_uri}> sotis:hasAnswer [
                            sotis:question <{question.uri}> ;
                            sotis:answer "{answer}" ;
                            sotis:isCorrect "{is_correct}"^^xsd:boolean
                        ] .
                    }}
                }}
                """
                execute_update(query_answer)


        # Test Attempts for Test 2B
        attempts_data_test2b = [
            {'student': 'student5', 'answers': {str(questions_graph2['What organelle is the powerhouse of the cell?'].id): 'Mitochondrion', str(questions_graph2['What are the base pairs in DNA?'].id): 'AT, CG', str(questions_graph2['Where does translation occur?'].id): 'Ribosome', str(questions_graph2['What is a key mechanism of evolution?'].id): 'All of the above', str(questions_graph2['What is a food web?'].id): 'Network of food chains'}},  # 100%
            {'student': 'student6', 'answers': {str(questions_graph2['What organelle is the powerhouse of the cell?'].id): 'Nucleus', str(questions_graph2['What are the base pairs in DNA?'].id): 'AU, CG', str(questions_graph2['Where does translation occur?'].id): 'Nucleus', str(questions_graph2['What is a key mechanism of evolution?'].id): 'Mutation', str(questions_graph2['What is a food web?'].id): 'Single food chain'}},  # ~20%
            {'student': 'student7', 'answers': {str(questions_graph2['What organelle is the powerhouse of the cell?'].id): 'Mitochondrion', str(questions_graph2['What are the base pairs in DNA?'].id): 'AT, GU', str(questions_graph2['Where does translation occur?'].id): 'Ribosome', str(questions_graph2['What is a key mechanism of evolution?'].id): 'Genetic Drift', str(questions_graph2['What is a food web?'].id): 'Network of food chains'}},  # ~60%
            {'student': 'student8', 'answers': {str(questions_graph2['What organelle is the powerhouse of the cell?'].id): 'Mitochondrion', str(questions_graph2['What are the base pairs in DNA?'].id): 'AT, CG', str(questions_graph2['Where does translation occur?'].id): 'Endoplasmic Reticulum', str(questions_graph2['What is a key mechanism of evolution?'].id): 'All of the above', str(questions_graph2['What is a food web?'].id): 'Network of food chains'}},  # ~80%
        ]

        for data in attempts_data_test2b:
            attempt_id = uuid.uuid4()
            attempt_uri = generate_test_attempt_uri()
            attempt = TestAttempt.objects.create(
                id=attempt_id, uri=attempt_uri, student=users[data['student']], test=test2b,
                answers=data['answers'], completed=True, description='Seeded attempt',
                version='1.0', status='lom:Final'
            )
            attempt.calculate_score()

            query_attempt = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX sotis: <{SOTIS_NS}>
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                <{attempt_uri}> rdf:type sotis:TestAttempt ;
                                        lom:identifier "{attempt_uri}" ;
                                        lom:contributor <{users[data['student']].uri}> ;
                                        lom:partOf <{test2b_uri}> ;
                                        lom:description "Seeded attempt" ;
                                        sotis:score "{attempt.score}"^^xsd:float ;
                                        lom:version "{attempt.version}" ;
                                        lom:date "{datetime.datetime.now().isoformat()}" ;
                                        lom:status "{attempt.status}" .
                }}
            }}
            """
            execute_update(query_attempt)

            for qid, answer in data['answers'].items():
                question = TestQuestion.objects.get(test=test2b, question__id=uuid.UUID(qid)).question
                is_correct = "1" if answer == question.correct_answer else "0"  # or True/False as string

                query_answer = f"""
                PREFIX lom: <{LOM_NS}>
                PREFIX sotis: <{SOTIS_NS}>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                INSERT DATA {{
                    GRAPH <{SOTIS_GRAPH}> {{
                        <{attempt_uri}> sotis:hasAnswer [
                            sotis:question <{question.uri}> ;
                            sotis:answer "{answer}" ;
                            sotis:isCorrect "{is_correct}"^^xsd:boolean
                        ] .
                    }}
                }}
                """
                execute_update(query_answer)


        # Graph 3: Physics Fundamentals by teacher3
        graph3_id = uuid.uuid4()
        graph3_uri = generate_kg_uri()
        graph3 = KnowledgeGraph.objects.create(
            id=graph3_id, uri=graph3_uri, title='Physics Fundamentals', author=users['teacher3'],
            description='Core physics concepts', keyword='physics', version='1.0', status='lom:Final',
            difficulty='lom:Medium', context='lom:Higher_Education', intended_end_user_role='lom:Student',
            typical_age_range='16-20', typical_learning_time='PT3H'
        )
        query_graph3 = f"""
        PREFIX lom: <{LOM_NS}>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX sotis: <{SOTIS_NS}>
        INSERT DATA {{
            GRAPH <{SOTIS_GRAPH}> {{
                <{graph3_uri}> rdf:type sotis:KnowledgeGraph ;
                               lom:identifier "{graph3_uri}" ;
                               lom:title "{graph3.title}" ;
                               lom:contributor <{users['teacher3'].uri}> ;
                               lom:learningResourceType lom:Graph ;
                               lom:language "{graph3.language or 'en'}" ;
                               lom:description "{graph3.description}" ;
                               lom:keyword "{graph3.keyword}" ;
                               lom:version "{graph3.version}" ;
                               lom:status "{graph3.status}" ;
                               lom:date "{datetime.datetime.now().isoformat()}" ;
                               lom:difficulty {graph3.difficulty} ;
                               lom:context {graph3.context} ;
                               lom:intendedEndUserRole {graph3.intended_end_user_role} ;
                               lom:typicalAgeRange "{graph3.typical_age_range}" ;
                               lom:typicalLearningTime "{graph3.typical_learning_time}" .
            }}
        }}
        """
        execute_update(query_graph3)

        # Nodes for Graph 3
        node_data_graph3 = [
            {'title': 'Kinematics', 'description': 'Motion and its description'},
            {'title': 'Dynamics', 'description': 'Forces and Newton’s laws', 'prereqs': ['Kinematics']},
            {'title': 'Energy', 'description': 'Work and energy conservation', 'prereqs': ['Kinematics', 'Dynamics']},
            {'title': 'Momentum', 'description': 'Momentum and collisions', 'prereqs': ['Kinematics', 'Dynamics']},
            {'title': 'Thermodynamics', 'description': 'Heat and energy transfer', 'prereqs': ['Energy']},
            {'title': 'Waves', 'description': 'Wave properties and behavior', 'prereqs': ['Kinematics']},
        ]

        nodes_graph3 = {}
        for data in node_data_graph3:
            node_id = uuid.uuid4()
            node_uri = generate_node_uri()
            node = Node.objects.create(
                id=node_id, uri=node_uri, title=data['title'], graph=graph3, graph_uri=graph3_uri,
                description=data['description'], keyword='physics node', version='1.0', status='lom:Final',
                difficulty='lom:Medium', context='lom:Higher_Education', intended_end_user_role='lom:Student',
                typical_age_range='16-20', typical_learning_time='PT45M'
            )
            nodes_graph3[data['title']] = node

            query_node = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX sotis: <{SOTIS_NS}>
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                    <{node_uri}> rdf:type sotis:Node ;
                                 lom:identifier "{node_uri}" ;
                                 lom:title "{node.title}" ;
                                 lom:partOf <{graph3_uri}> ;
                                 lom:learningResourceType lom:Narrative_Text ;
                                 lom:language "{node.language or 'en'}" ;
                                 lom:description "{node.description}" ;
                                 lom:keyword "{node.keyword}" ;
                                 lom:version "{node.version}" ;
                                 lom:status "{node.status}" ;
                                 lom:contributor <{users['teacher3'].uri}> ;
                                 lom:date "{datetime.datetime.now().isoformat()}" ;
                                 lom:difficulty {node.difficulty} ;
                                 lom:context {node.context} ;
                                 lom:intendedEndUserRole {node.intended_end_user_role} ;
                                 lom:typicalAgeRange "{node.typical_age_range}" ;
                                 lom:typicalLearningTime "{node.typical_learning_time}" .
                }}
            }}
            """
            execute_update(query_node)

            if 'prereqs' in data:
                for prereq_title in data['prereqs']:
                    prereq_node = nodes_graph3[prereq_title]
                    node.prerequisite_nodes.add(prereq_node)
                    query_rel = f"""
                    PREFIX lom: <{LOM_NS}>
                    INSERT DATA {{
                        GRAPH <{SOTIS_GRAPH}> {{
                            <{node_uri}> lom:requires <{prereq_node.uri}> .
                        }}
                    }}
                    """
                    execute_update(query_rel)

        # Questions for Graph 3 nodes
        questions_data_graph3 = [
            {'node_title': 'Kinematics', 'text': 'What is the formula for velocity?', 'correct': 'v = d/t', 'others': ['v = d*t', 'v = a/t', 'v = m/d']},
            {'node_title': 'Kinematics', 'text': 'What is acceleration?', 'correct': 'Rate of change of velocity', 'others': ['Speed', 'Distance', 'Force']},
            {'node_title': 'Dynamics', 'text': 'What is Newton’s First Law?', 'correct': 'Object at rest stays at rest', 'others': ['F=ma', 'Action-reaction', 'Momentum conservation']},
            {'node_title': 'Dynamics', 'text': 'What is the unit of force?', 'correct': 'Newton', 'others': ['Joule', 'Watt', 'Pascal']},
            {'node_title': 'Energy', 'text': 'What is kinetic energy?', 'correct': '1/2 mv^2', 'others': ['mgh', 'F*d', 'mv']},
            {'node_title': 'Energy', 'text': 'What is potential energy?', 'correct': 'mgh', 'others': ['1/2 mv^2', 'F*d', 'mv']},
            {'node_title': 'Momentum', 'text': 'What is momentum?', 'correct': 'mv', 'others': ['1/2 mv^2', 'mgh', 'F*d']},
            {'node_title': 'Momentum', 'text': 'What is conserved in an elastic collision?', 'correct': 'Momentum and kinetic energy', 'others': ['Only momentum', 'Only kinetic energy', 'Mass']},
            {'node_title': 'Thermodynamics', 'text': 'What is the First Law of Thermodynamics?', 'correct': 'Energy conservation', 'others': ['Entropy increase', 'Heat flow', 'Work done']},
            {'node_title': 'Thermodynamics', 'text': 'What is absolute zero?', 'correct': '0 K', 'others': ['0 C', '-273 C', '273 K']},
            {'node_title': 'Waves', 'text': 'What is the speed of a wave?', 'correct': 'v = fλ', 'others': ['v = f/λ', 'v = λ/f', 'v = f*λ^2']},
            {'node_title': 'Waves', 'text': 'What is a transverse wave?', 'correct': 'Oscillations perpendicular to direction', 'others': ['Oscillations parallel to direction', 'No oscillations', 'Circular motion']},
        ]

        questions_graph3 = {}
        for data in questions_data_graph3:
            q_id = uuid.uuid4()
            q_uri = generate_question_uri()
            node = nodes_graph3[data['node_title']]
            question = Question.objects.create(
                id=q_id, uri=q_uri, text=data['text'], correct_answer=data['correct'], other_answers=data['others'],
                node=node, node_uri=node.uri, keyword='physics question', version='1.0', status='lom:Final',
                difficulty='lom:Medium', context='lom:Higher_Education', intended_end_user_role='lom:Student',
                typical_age_range='16-20', typical_learning_time='PT10M'
            )
            questions_graph3[data['text']] = question

            query_q = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX sotis: <{SOTIS_NS}>
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                    <{q_uri}> rdf:type sotis:Question ;
                              lom:identifier "{q_uri}" ;
                              lom:title "{question.text[:50]}" ;
                              lom:partOf <{node.uri}> ;
                              lom:learningResourceType lom:Questionnaire ;
                              lom:language "{question.language or 'en'}" ;
                              lom:description "{question.text}" ;
                              lom:keyword "{question.keyword}" ;
                              lom:version "{question.version}" ;
                              lom:status "{question.status}" ;
                              lom:contributor <{users['teacher3'].uri}> ;
                              lom:date "{datetime.datetime.now().isoformat()}" ;
                              lom:difficulty {question.difficulty} ;
                              lom:context {question.context} ;
                              lom:intendedEndUserRole {question.intended_end_user_role} ;
                              lom:typicalAgeRange "{question.typical_age_range}" ;
                              lom:typicalLearningTime "{question.typical_learning_time}" ;
                              sotis:correctAnswer "{question.correct_answer}" ;
                              sotis:otherAnswers "{', '.join(question.other_answers)}" .
                }}
            }}
            """
            execute_update(query_q)

        # Tests for Graph 3
        test3a_id = uuid.uuid4()
        test3a_uri = generate_test_uri()
        test3a = Test.objects.create(
            id=test3a_id, uri=test3a_uri, title='Physics Fundamentals Test A', author=users['teacher3'],
            graph=graph3, graph_uri=graph3_uri, description='Test on physics fundamentals (part A)',
            keyword='physics test', version='1.0', status='lom:Final', difficulty='lom:Medium',
            context='lom:Higher_Education', intended_end_user_role='lom:Student', typical_age_range='16-20',
            typical_learning_time='PT45M'
        )
        query_test3a = f"""
        PREFIX lom: <{LOM_NS}>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX sotis: <{SOTIS_NS}>
        INSERT DATA {{
            GRAPH <{SOTIS_GRAPH}> {{
                <{test3a_uri}> rdf:type sotis:Test ;
                              lom:identifier "{test3a_uri}" ;
                              lom:title "{test3a.title}" ;
                              lom:contributor <{users['teacher3'].uri}> ;
                              lom:partOf <{graph3_uri}> ;
                              lom:learningResourceType lom:Questionnaire ;
                              lom:language "{test3a.language or 'en'}" ;
                              lom:description "{test3a.description}" ;
                              lom:keyword "{test3a.keyword}" ;
                              lom:version "{test3a.version}" ;
                              lom:status "{test3a.status}" ;
                              lom:date "{datetime.datetime.now().isoformat()}" ;
                              lom:difficulty {test3a.difficulty} ;
                              lom:context {test3a.context} ;
                              lom:intendedEndUserRole {test3a.intended_end_user_role} ;
                              lom:typicalAgeRange "{test3a.typical_age_range}" ;
                              lom:typicalLearningTime "{test3a.typical_learning_time}" .
            }}
        }}
        """
        execute_update(query_test3a)

        test3b_id = uuid.uuid4()
        test3b_uri = generate_test_uri()
        test3b = Test.objects.create(
            id=test3b_id, uri=test3b_uri, title='Physics Fundamentals Test B', author=users['teacher3'],
            graph=graph3, graph_uri=graph3_uri, description='Test on physics fundamentals (part B)',
            keyword='physics test', version='1.0', status='lom:Final', difficulty='lom:Medium',
            context='lom:Higher_Education', intended_end_user_role='lom:Student', typical_age_range='16-20',
            typical_learning_time='PT45M'
        )
        query_test3b = f"""
        PREFIX lom: <{LOM_NS}>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX sotis: <{SOTIS_NS}>
        INSERT DATA {{
            GRAPH <{SOTIS_GRAPH}> {{
                <{test3b_uri}> rdf:type sotis:Test ;
                              lom:identifier "{test3b_uri}" ;
                              lom:title "{test3b.title}" ;
                              lom:contributor <{users['teacher3'].uri}> ;
                              lom:partOf <{graph3_uri}> ;
                              lom:learningResourceType lom:Questionnaire ;
                              lom:language "{test3b.language or 'en'}" ;
                              lom:description "{test3b.description}" ;
                              lom:keyword "{test3b.keyword}" ;
                              lom:version "{test3b.version}" ;
                              lom:status "{test3b.status}" ;
                              lom:date "{datetime.datetime.now().isoformat()}" ;
                              lom:difficulty {test3b.difficulty} ;
                              lom:context {test3b.context} ;
                              lom:intendedEndUserRole {test3b.intended_end_user_role} ;
                              lom:typicalAgeRange "{test3b.typical_age_range}" ;
                              lom:typicalLearningTime "{test3b.typical_learning_time}" .
            }}
        }}
        """
        execute_update(query_test3b)

        # Add questions to Tests
        for order, question in enumerate(list(questions_graph3.values())[::2], start=1):
            tq = TestQuestion.objects.create(test=test3a, question=question, order=order)
            query_tq = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX sotis: <{SOTIS_NS}>
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                    <{test3a_uri}> lom:hasQuestion <{question.uri}> .
                }}
            }}
            """
            execute_update(query_tq)
        for order, question in enumerate(list(questions_graph3.values())[1::2], start=1):
            tq = TestQuestion.objects.create(test=test3b, question=question, order=order)
            query_tq = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX sotis: <{SOTIS_NS}>
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                    <{test3b_uri}> lom:hasQuestion <{question.uri}> .
                }}
            }}
            """
            execute_update(query_tq)

        # Test Attempts for Test 3A
        attempts_data_test3a = [
            {'student': 'student1', 'answers': {str(questions_graph3['What is the formula for velocity?'].id): 'v = d/t', str(questions_graph3['What is Newton’s First Law?'].id): 'Object at rest stays at rest', str(questions_graph3['What is kinetic energy?'].id): '1/2 mv^2', str(questions_graph3['What is momentum?'].id): 'mv', str(questions_graph3['What is the First Law of Thermodynamics?'].id): 'Energy conservation', str(questions_graph3['What is the speed of a wave?'].id): 'v = fλ'}},  # 100%
            {'student': 'student2', 'answers': {str(questions_graph3['What is the formula for velocity?'].id): 'v = d*t', str(questions_graph3['What is Newton’s First Law?'].id): 'F=ma', str(questions_graph3['What is kinetic energy?'].id): 'mgh', str(questions_graph3['What is momentum?'].id): '1/2 mv^2', str(questions_graph3['What is the First Law of Thermodynamics?'].id): 'Entropy increase', str(questions_graph3['What is the speed of a wave?'].id): 'v = λ/f'}},  # ~17%
            {'student': 'student3', 'answers': {str(questions_graph3['What is the formula for velocity?'].id): 'v = d/t', str(questions_graph3['What is Newton’s First Law?'].id): 'Object at rest stays at rest', str(questions_graph3['What is kinetic energy?'].id): '1/2 mv^2', str(questions_graph3['What is momentum?'].id): 'mv', str(questions_graph3['What is the First Law of Thermodynamics?'].id): 'Energy conservation', str(questions_graph3['What is the speed of a wave?'].id): 'v = fλ'}},  # ~67%
            {'student': 'student4', 'answers': {str(questions_graph3['What is the formula for velocity?'].id): 'v = d/t', str(questions_graph3['What is Newton’s First Law?'].id): 'Object at rest stays at rest', str(questions_graph3['What is kinetic energy?'].id): 'F*d', str(questions_graph3['What is momentum?'].id): 'mv', str(questions_graph3['What is the First Law of Thermodynamics?'].id): 'Heat flow', str(questions_graph3['What is the speed of a wave?'].id): 'v = f/λ'}},  # ~83%
            {'student': 'student5', 'answers': {str(questions_graph3['What is the formula for velocity?'].id): 'v = a/t', str(questions_graph3['What is Newton’s First Law?'].id): 'Action-reaction', str(questions_graph3['What is kinetic energy?'].id): 'mv', str(questions_graph3['What is momentum?'].id): 'mgh', str(questions_graph3['What is the First Law of Thermodynamics?'].id): 'Work done', str(questions_graph3['What is the speed of a wave?'].id): 'v = f*λ^2'}},  # ~0%
        ]

        for data in attempts_data_test3a:
            attempt_id = uuid.uuid4()
            attempt_uri = generate_test_attempt_uri()
            attempt = TestAttempt.objects.create(
                id=attempt_id, uri=attempt_uri, student=users[data['student']], test=test3a,
                answers=data['answers'], completed=True, description='Seeded attempt',
                version='1.0', status='lom:Final'
            )
            attempt.calculate_score()

            query_attempt = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX sotis: <{SOTIS_NS}>
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                <{attempt_uri}> rdf:type sotis:TestAttempt ;
                                        lom:identifier "{attempt_uri}" ;
                                        lom:contributor <{users[data['student']].uri}> ;
                                        lom:partOf <{test3b_uri}> ;
                                        lom:description "Seeded attempt" ;
                                        sotis:score "{attempt.score}"^^xsd:float ;
                                        lom:version "{attempt.version}" ;
                                        lom:date "{datetime.datetime.now().isoformat()}" ;
                                        lom:status "{attempt.status}" .
                }}
            }}
            """
            execute_update(query_attempt)

            for qid, answer in data['answers'].items():
                question = TestQuestion.objects.get(test=test3a, question__id=uuid.UUID(qid)).question
                is_correct = "1" if answer == question.correct_answer else "0"  # or True/False as string

                query_answer = f"""
                PREFIX lom: <{LOM_NS}>
                PREFIX sotis: <{SOTIS_NS}>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                INSERT DATA {{
                    GRAPH <{SOTIS_GRAPH}> {{
                        <{attempt_uri}> sotis:hasAnswer [
                            sotis:question <{question.uri}> ;
                            sotis:answer "{answer}" ;
                            sotis:isCorrect "{is_correct}"^^xsd:boolean
                        ] .
                    }}
                }}
                """
                execute_update(query_answer)


        # --- ADD THIS BLOCK FOR PREREQUISITE VIOLATIONS TO APPEAR ---
        # Let some students take both Test A and Test B so they answer questions from prereq and advanced nodes
        overlap_attempts = [
            # student2 (originally low on Test A) retakes Test B
            {
                'student': 'student2',
                'test': test1b,
                'answers': {
                    str(questions_graph1['What is 7 + 8?'].id): '15',
                    str(questions_graph1['What is 10 - 4?'].id): '6',
                    str(questions_graph1['What is 6 * 7?'].id): '42',
                    str(questions_graph1['What is 15 / 5?'].id): '3',
                    str(questions_graph1['What is 3/4 * 2/3?'].id): '1/3',  # wrong
                    str(questions_graph1['What is 1.2 * 2?'].id): '2.8'     # wrong
                }  # ~67% on retake
            },
            # student4 (good on Test A) retakes Test B
            {
                'student': 'student4',
                'test': test1b,
                'answers': {
                    str(questions_graph1['What is 7 + 8?'].id): '15',
                    str(questions_graph1['What is 10 - 4?'].id): '6',
                    str(questions_graph1['What is 6 * 7?'].id): '42',
                    str(questions_graph1['What is 15 / 5?'].id): '3',
                    str(questions_graph1['What is 3/4 * 2/3?'].id): '1/2',
                    str(questions_graph1['What is 1.2 * 2?'].id): '2.4'
                }  # 100% on retake
            },
            # student7 (low on Test B) retakes Test A
            {
                'student': 'student7',
                'test': test1a,
                'answers': {
                    str(questions_graph1['What is 2 + 2?'].id): '4',
                    str(questions_graph1['What is 5 - 3?'].id): '2',
                    str(questions_graph1['What is 3 * 4?'].id): '12',
                    str(questions_graph1['What is 12 / 3?'].id): '4',
                    str(questions_graph1['What is 1/2 + 1/4?'].id): '1/2',  # wrong
                    str(questions_graph1['What is 0.5 + 0.3?'].id): '0.8'
                }  # ~83% on retake
            },
            # student9 (good on Test B) retakes Test A
            {
                'student': 'student9',
                'test': test1a,
                'answers': {
                    str(questions_graph1['What is 2 + 2?'].id): '4',
                    str(questions_graph1['What is 5 - 3?'].id): '2',
                    str(questions_graph1['What is 3 * 4?'].id): '12',
                    str(questions_graph1['What is 12 / 3?'].id): '4',
                    str(questions_graph1['What is 1/2 + 1/4?'].id): '3/4',
                    str(questions_graph1['What is 0.5 + 0.3?'].id): '0.8'
                }  # 100% on retake
            },
        ]

        for data in overlap_attempts:
            attempt_id = uuid.uuid4()
            attempt_uri = generate_test_attempt_uri()
            attempt = TestAttempt.objects.create(
                id=attempt_id,
                uri=attempt_uri,
                student=users[data['student']],
                test=data['test'],
                answers=data['answers'],
                completed=True,
                description='Overlap retake for prerequisite analysis',
                version='1.0',
                status='lom:Final'
            )
            attempt.calculate_score()
            attempt.save()

            query_attempt = f"""
            PREFIX lom: <{LOM_NS}>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX sotis: <{SOTIS_NS}>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            INSERT DATA {{
                GRAPH <{SOTIS_GRAPH}> {{
                    <{attempt_uri}> rdf:type sotis:TestAttempt ;
                                    lom:contributor <{users[data['student']].uri}> ;
                                    lom:partOf <{data['test'].uri}> ;
                                    lom:description "Overlap retake for prerequisite analysis" ;
                                    sotis:score "{attempt.score}"^^xsd:float ;
                                    lom:date "{datetime.datetime.now().isoformat()}"^^xsd:dateTime ;
                                    lom:status "{attempt.status}" .
                }}
            }}
            """
            execute_update(query_attempt)

            for qid, answer in data['answers'].items():
                question = TestQuestion.objects.get(test=data['test'], question__id=uuid.UUID(qid)).question
                is_correct = "1" if answer == question.correct_answer else "0"
                query_answer = f"""
                PREFIX lom: <{LOM_NS}>
                PREFIX sotis: <{SOTIS_NS}>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                INSERT DATA {{
                    GRAPH <{SOTIS_GRAPH}> {{
                        <{attempt_uri}> sotis:hasAnswer [
                            sotis:question <{question.uri}> ;
                            sotis:answer "{answer}" ;
                            sotis:isCorrect "{is_correct}"^^xsd:boolean
                        ] .
                    }}
                }}
                """
                execute_update(query_answer)
            # These students retake the other test to create multiple attempts and real improvement
            improvement_retakes = [
                # student2 (originally ~33% on Test A) retakes Test B and gets perfect
                {
                    'student': 'student2',
                    'test': test1b,
                    'answers': {
                        str(questions_graph1['What is 7 + 8?'].id): '15',
                        str(questions_graph1['What is 10 - 4?'].id): '6',
                        str(questions_graph1['What is 6 * 7?'].id): '42',
                        str(questions_graph1['What is 15 / 5?'].id): '3',
                        str(questions_graph1['What is 3/4 * 2/3?'].id): '1/2',
                        str(questions_graph1['What is 1.2 * 2?'].id): '2.4'
                    }  # 100%
                },
                # student5 (originally 0% on Test A) retakes Test B and improves
                {
                    'student': 'student5',
                    'test': test1b,
                    'answers': {
                        str(questions_graph1['What is 7 + 8?'].id): '15',
                        str(questions_graph1['What is 10 - 4?'].id): '6',
                        str(questions_graph1['What is 6 * 7?'].id): '42',
                        str(questions_graph1['What is 15 / 5?'].id): '3',
                        str(questions_graph1['What is 3/4 * 2/3?'].id): '1/3',  # wrong
                        str(questions_graph1['What is 1.2 * 2?'].id): '2.4'
                    }  # ~83%
                },
                # student7 (originally ~33% on Test B) retakes Test A and improves
                {
                    'student': 'student7',
                    'test': test1a,
                    'answers': {
                        str(questions_graph1['What is 2 + 2?'].id): '4',
                        str(questions_graph1['What is 5 - 3?'].id): '2',
                        str(questions_graph1['What is 3 * 4?'].id): '12',
                        str(questions_graph1['What is 12 / 3?'].id): '4',
                        str(questions_graph1['What is 1/2 + 1/4?'].id): '3/4',
                        str(questions_graph1['What is 0.5 + 0.3?'].id): '0.8'
                    }  # 100%
                },
            ]
            base_date = datetime.datetime.now()

            for idx,data in enumerate(improvement_retakes):
                attempt_id = uuid.uuid4()
                attempt_uri = generate_test_attempt_uri()
                attempt = TestAttempt.objects.create(
                    id=attempt_id,
                    uri=attempt_uri,
                    student=users[data['student']],
                    test=data['test'],
                    answers=data['answers'],
                    completed=True,
                    description='Retake for MostImprovedStudentsView demo',
                    version='1.0',
                    status='lom:Final'
                )
                attempt.calculate_score()
                attempt.save()

                attempt_date = base_date - datetime.timedelta(days=idx + 1)
                query_attempt = f"""
                PREFIX lom: <{LOM_NS}>
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX sotis: <{SOTIS_NS}>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                INSERT DATA {{
                    GRAPH <{SOTIS_GRAPH}> {{
                        <{attempt_uri}> rdf:type sotis:TestAttempt ;
                                        lom:contributor <{users[data['student']].uri}> ;
                                        lom:partOf <{data['test'].uri}> ;
                                        lom:description "Retake for MostImprovedStudentsView demo" ;
                                        sotis:score "{attempt.score}"^^xsd:float ;
                                        lom:date "{attempt_date.isoformat()}"^^xsd:dateTime ;
                                        lom:status "{attempt.status}" .
                    }}
                }}
                """
                execute_update(query_attempt)

                for qid, answer in data['answers'].items():
                    question = TestQuestion.objects.get(test=data['test'], question__id=uuid.UUID(qid)).question
                    is_correct = "1" if answer == question.correct_answer else "0"
                    query_answer = f"""
                    PREFIX lom: <{LOM_NS}>
                    PREFIX sotis: <{SOTIS_NS}>
                    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                    INSERT DATA {{
                        GRAPH <{SOTIS_GRAPH}> {{
                            <{attempt_uri}> sotis:hasAnswer [
                                sotis:question <{question.uri}> ;
                                sotis:answer "{answer}" ;
                                sotis:isCorrect "{is_correct}"^^xsd:boolean
                            ] .
                        }}
                    }}
                    """
                execute_update(query_answer)

        # --- END OF ADDITION ---
            self.stdout.write(self.style.SUCCESS('Seeding completed successfully!'))