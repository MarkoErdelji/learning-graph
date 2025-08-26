# your_app_name/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from ..views import (
    CustomTokenObtainPairView, DownloadIQTFormView, GenerateGraphFromIITA, KnowledgeGraphWithTestResultDetailView, QuestionsForTestView, TestAttemptView, TestAttemptsView, TestListGraphView, TestListView, TestResultsView, TestsForGraphView, UserRegistrationView, TeacherView,
    KnowledgeGraphViewSet, GraphNodeViewSet, QuestionViewSet,
    FirstQuestionView, KnowledgeGraphDetailView,TestCreationView
)

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('graphs/', KnowledgeGraphViewSet.as_view({'get': 'list_graphs', 'post': 'create'}), name='graphs'),
    path('oneQuestion/', FirstQuestionView.as_view(), name='first-question'),
    path('nodes/', GraphNodeViewSet.as_view({'get': 'list', 'post': 'create'}), name='nodes'),
    path('nodes/<uuid:pk>/update/', GraphNodeViewSet.as_view({'patch': 'update_node'}), name='update-node'),
    path('nodes/<uuid:pk>/delete/', GraphNodeViewSet.as_view({'delete': 'delete_node'}), name='delete-node'),
    path('nodes/<uuid:pk>/update_with_prerequisites/', 
         GraphNodeViewSet.as_view({'patch': 'update_with_prerequisites'}),
         name='update-node-with-prerequisites'),
    path('questions/', QuestionViewSet.as_view({'get': 'list', 'post': 'create'}), name='questions'),
    path('questions/<uuid:pk>/update/', QuestionViewSet.as_view({'patch': 'update_question'}), name='update-question'),
    path('questions/<uuid:pk>/delete/', QuestionViewSet.as_view({'delete': 'delete_question'}), name='delete-question'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('teacheronly/', TeacherView.as_view(), name='teacher-only-view'),
    path('knowledge-graph/<uuid:pk>/', KnowledgeGraphDetailView.as_view(), name='knowledge-graph-detail'),
    path('tests/', TestListView.as_view(), name='test-list'),
        path('tests-graph/', TestListGraphView.as_view(), name='test-list-graph'),
    path('tests/<uuid:test_id>/attempt/', TestAttemptView.as_view(), name='test_attempt'),
    path('tests/create_test/', TestCreationView.as_view(), name='create_test'),
    path('tests/<uuid:test_id>/attempts/', TestAttemptsView.as_view(), name='test-attempts'),
    path('tests/<uuid:test_id>/results/', TestResultsView.as_view(), name='test-results'),
    path('generate-graph/<uuid:test_id>/', GenerateGraphFromIITA.as_view(), name='generate_graph'),
    path('test-attempts/<uuid:test_attempt_id>/graph/', KnowledgeGraphWithTestResultDetailView.as_view(), name='test-attempt-graph'),
    path('tests-graph/<uuid:graph_id>/', TestsForGraphView.as_view(), name='tests_for_graph'),
    path('tests/<uuid:test_id>/questions/', QuestionsForTestView.as_view(), name='questions_for_test'),
    path('tests/download_qti/<uuid:test_id>/', DownloadIQTFormView.as_view(), name='download_qti'),


]
