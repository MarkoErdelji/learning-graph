# your_app_name/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from ..views import (
    CustomTokenObtainPairView, UserRegistrationView, TeacherView,
    KnowledgeGraphViewSet, GraphNodeViewSet, QuestionViewSet,
    FirstQuestionView, KnowledgeGraphDetailView
)

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('graphs/', KnowledgeGraphViewSet.as_view({'get': 'list_graphs', 'post': 'create'}), name='graphs'),
    path('oneQuestion/', FirstQuestionView.as_view(), name='first-question'),
    path('nodes/', GraphNodeViewSet.as_view({'get': 'list', 'post': 'create'}), name='nodes'),
    path('nodes/<int:pk>/update/', GraphNodeViewSet.as_view({'patch': 'update_node'}), name='update-node'),
    path('nodes/<int:pk>/delete/', GraphNodeViewSet.as_view({'delete': 'delete_node'}), name='delete-node'),
    path('nodes/<int:pk>/update_with_prerequisites/', 
         GraphNodeViewSet.as_view({'patch': 'update_with_prerequisites'}),
         name='update-node-with-prerequisites'),
    path('questions/', QuestionViewSet.as_view({'get': 'list', 'post': 'create'}), name='questions'),
    path('questions/<int:pk>/update/', QuestionViewSet.as_view({'patch': 'update_question'}), name='update-question'),
    path('questions/<int:pk>/delete/', QuestionViewSet.as_view({'delete': 'delete_question'}), name='delete-question'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('teacheronly/', TeacherView.as_view(), name='teacher-only-view'),
    path('knowledge-graph/<int:pk>/', KnowledgeGraphDetailView.as_view(), name='knowledge-graph-detail'),
]
