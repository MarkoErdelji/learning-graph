from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission

class Book(models.Model):
    title = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    published_date = models.DateField()

    def __str__(self):
        return self.title



class AppUser(AbstractUser):

    USER_TYPE_CHOICES = [
        ('teacher', 'Teacher'),
        ('expert', 'Expert'),
        ('student', 'Student'),
    ]

    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='admin')

    class Meta:
        permissions = [
            ("is_teacher", "Can perform teacher actions"),
            ("is_expert", "Can perform expert actions"),
            ("is_student", "Can perform student actions"),
        ]
        
    groups = models.ManyToManyField(
        Group,
        related_name='appuser_set',  # Change this name as needed
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        verbose_name='groups'
    )

    user_permissions = models.ManyToManyField(
        Permission,
        related_name='appuser_set',  # Change this name as needed
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )