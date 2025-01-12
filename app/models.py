from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.auth import get_user_model


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
    dependent_nodes = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='prerequisite_nodes')

    def __str__(self):
        return f"{self.title} (Graph: {self.graph.title})"

class Question(models.Model):
    node = models.ForeignKey(GraphNode, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField(max_length=255)
    correct_answer = models.CharField(max_length=255)
    other_answers = models.JSONField()  # Stores other answers as a list in JSON format

    def __str__(self):
        return f"Question on {self.node.title}: {self.text}"
    
User = get_user_model()


class Test(models.Model):
    graph = models.ForeignKey(KnowledgeGraph, on_delete=models.CASCADE, related_name='tests')
    title = models.CharField(max_length=255)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tests')
    questions = models.ManyToManyField(
        Question,
        through='TestQuestion',
        related_name='tests',
        blank=True
    )

    def __str__(self):
        return self.title

class TestQuestion(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']
        unique_together = ('test', 'question')

class TestAttempt(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_attempts')
    answers = models.JSONField()  # Format: {"question_id": 0/1}
    completed = models.BooleanField(default=False)
    score = models.FloatField(null=True, blank=True)  # Calculated after submission

    def calculate_score(self):
        correct_answers = sum(value for value in self.answers.values())
        total_questions = len(self.answers)
        self.score = (correct_answers / total_questions) * 100
        self.save()