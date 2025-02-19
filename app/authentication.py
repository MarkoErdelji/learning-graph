from django.contrib.auth.backends import ModelBackend
from .models import AppUser

class AppUserBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = AppUser.objects.get(username=username)
        except AppUser.DoesNotExist:
            return None
        
        if user.check_password(password):
            return user
        return None