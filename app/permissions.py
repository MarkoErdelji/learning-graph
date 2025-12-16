from rest_framework import permissions

class IsTeacher(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'Teacher'


class IsExpert(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'Expert'


class IsStudent(permissions.BasePermission):

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'Student'