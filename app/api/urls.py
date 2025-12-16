# your_app_name/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from app.queryviews import ClassAveragePerTestView, ClassHardestQuestionsView, ClassPrerequisiteViolationsView, ClassTopicMasteryView, MostImprovedStudentsView, StudentFrequentlyWrongView, StudentOverallAverageView, StudentRankingView, StudentRecentTestsView, StudentRecommendationsView, StudentTopicMasteryView, StudentsNeedingHelpView, TestParticipationView



from ..views import (
    CustomTokenObtainPairView,
    DownloadIQTFormView,
    GenerateGraphFromIITA,
    KnowledgeGraphWithTestResultDetailView,
    QuestionsForTestView,
    TestAttemptView,
    TestAttemptsView,
    TestListGraphView,
    TestListView,
    TestResultsView,
    TestsForGraphView,
    UserRegistrationView,
    TeacherView,
    KnowledgeGraphViewSet,
    GraphNodeViewSet,
    QuestionViewSet,
    FirstQuestionView,
    KnowledgeGraphDetailView,
    TestCreationView,
)

urlpatterns = [
    # Authentication
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Teacher-only protected endpoint
    path('teacheronly/', TeacherView.as_view(), name='teacher-only-view'),

    # Knowledge Graphs
    path('graphs/', KnowledgeGraphViewSet.as_view({'get': 'list_graphs', 'post': 'create'}), name='graphs'),
    path('knowledge-graph/<uuid:pk>/', KnowledgeGraphDetailView.as_view(), name='knowledge-graph-detail'),

    # Nodes
    path('nodes/', GraphNodeViewSet.as_view({'get': 'list', 'post': 'create'}), name='nodes'),
    path('nodes/<uuid:pk>/update/', GraphNodeViewSet.as_view({'patch': 'update_node'}), name='update-node'),
    path('nodes/<uuid:pk>/delete/', GraphNodeViewSet.as_view({'delete': 'delete_node'}), name='delete-node'),
    path('nodes/<uuid:pk>/update_with_prerequisites/', 
         GraphNodeViewSet.as_view({'patch': 'update_with_prerequisites'}),
         name='update-node-with-prerequisites'),

    # Questions
    path('questions/', QuestionViewSet.as_view({'get': 'list', 'post': 'create'}), name='questions'),
    path('questions/<uuid:pk>/update/', QuestionViewSet.as_view({'patch': 'update_question'}), name='update-question'),
    path('questions/<uuid:pk>/delete/', QuestionViewSet.as_view({'delete': 'delete_question'}), name='delete-question'),

    # First question endpoint
    path('oneQuestion/', FirstQuestionView.as_view(), name='first-question'),

    # Tests
    path('tests/', TestListView.as_view(), name='test-list'),
    path('tests-graph/', TestListGraphView.as_view(), name='test-list-graph'),
    path('tests/create_test/', TestCreationView.as_view(), name='create_test'),
    path('tests-graph/<uuid:graph_id>/', TestsForGraphView.as_view(), name='tests_for_graph'),

    # Test Attempts & Results
    path('tests/<uuid:test_id>/attempt/', TestAttemptView.as_view(), name='test_attempt'),
    path('tests/<uuid:test_id>/attempts/', TestAttemptsView.as_view(), name='test-attempts'),
    path('tests/<uuid:test_id>/results/', TestResultsView.as_view(), name='test-results'),
    path('tests/<uuid:test_id>/questions/', QuestionsForTestView.as_view(), name='questions_for_test'),

    # Graph Generation & Export
    path('generate-graph/<uuid:test_id>/', GenerateGraphFromIITA.as_view(), name='generate_graph'),
    path('test-attempts/<uuid:test_attempt_id>/graph/', KnowledgeGraphWithTestResultDetailView.as_view(), name='test-attempt-graph'),
    path('tests/download_qti/<uuid:test_id>/', DownloadIQTFormView.as_view(), name='download_qti'),



    path('student/analytics/overall/', StudentOverallAverageView.as_view(), name='student-overall-average'),
    path('student/analytics/recent-tests/', StudentRecentTestsView.as_view(), name='student-recent-tests'),
    path('student/analytics/topic-mastery/', StudentTopicMasteryView.as_view(), name='student-topic-mastery'),
    path('student/analytics/frequently-wrong/', StudentFrequentlyWrongView.as_view(), name='student-frequently-wrong'),
    path('student/analytics/ranking/', StudentRankingView.as_view(), name='student-ranking'),
    path('student/analytics/recommendations/', StudentRecommendationsView.as_view(), name='student-recommendations'),

    path('teacher/analytics/class-average-per-test/', ClassAveragePerTestView.as_view(), name='class-average-per-test'),
    path('teacher/analytics/hardest-questions/', ClassHardestQuestionsView.as_view(), name='class-hardest-questions'),
    path('teacher/analytics/students-needing-help/', StudentsNeedingHelpView.as_view(), name='students-needing-help'),
    path('teacher/analytics/class-topic-mastery/', ClassTopicMasteryView.as_view(), name='class-topic-mastery'),
    path('teacher/analytics/test-participation/', TestParticipationView.as_view(), name='test-participation'),
    path('teacher/analytics/most-improved/', MostImprovedStudentsView.as_view(), name='most-improved-students'),
    path('teacher/analytics/prerequisite-violations/', ClassPrerequisiteViolationsView.as_view(), name='class-prerequisite-violations'),
]