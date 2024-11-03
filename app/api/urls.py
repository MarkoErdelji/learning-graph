from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from ..views import CustomTokenObtainPairView,UserRegistrationView,TeacherView,KnowledgeGraphViewSet, GraphNodeViewSet, QuestionViewSet,FirstQuestionView

urlpatterns = [
     path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('graphs/', KnowledgeGraphViewSet.as_view({'get': 'list', 'post': 'create'}), name='graph'),
    path('oneQuestion/', FirstQuestionView.as_view(), name='graph'),
    path('nodes/', GraphNodeViewSet.as_view({'get': 'list', 'post': 'create'}), name='node'),
    path('questions/', QuestionViewSet.as_view({'get': 'list', 'post': 'create'}), name='question'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('teacheronly',TeacherView.as_view(),name='teacher-only-view')
]