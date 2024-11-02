from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from ..views import BookList, CustomTokenObtainPairView,UserRegistrationView,TeacherView

urlpatterns = [
    path('books/', BookList.as_view(), name='book-list'),
     path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('teacheronly',TeacherView.as_view(),name='teacher-only-view')
]