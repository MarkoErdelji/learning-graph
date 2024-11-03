from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission

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

class KnowledgeGraph(models.Model):
    title = models.CharField(max_length=255)
    created_by = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name='created_graphs')

    def __str__(self):
        return self.title

class GraphNode(models.Model):
    graph = models.ForeignKey(KnowledgeGraph, on_delete=models.CASCADE, related_name='nodes')
    title = models.CharField(max_length=255)
    prerequisite_nodes = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='dependent_nodes')

    def __str__(self):
        return f"{self.title} (Graph: {self.graph.title})"

class Question(models.Model):
    node = models.ForeignKey(GraphNode, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField(max_length=255)
    correct_answer = models.CharField(max_length=255)
    other_answers = models.JSONField()  # Stores other answers as a list in JSON format

    def __str__(self):
        return f"Question on {self.node.title}: {self.text}"