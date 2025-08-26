from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


def generate_user_uri():
    return f'http://example.com/sotis/user/{uuid.uuid4()}'

def generate_kg_uri():
    return f'http://example.com/sotis/kg/{uuid.uuid4()}'

def generate_node_uri():
    return f'http://example.com/sotis/node/{uuid.uuid4()}'

def generate_question_uri():
    return f'http://example.com/sotis/question/{uuid.uuid4()}'

def generate_test_uri():
    return f'http://example.com/sotis/test/{uuid.uuid4()}'

def generate_test_attempt_uri():
    return f'http://example.com/sotis/attempt/{uuid.uuid4()}'

class AppUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('teacher', 'Teacher'),
        ('expert', 'Expert'),
        ('student', 'Student'),
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='student')
    uri = models.CharField(max_length=255, unique=True, default=generate_user_uri)

    def __str__(self):
        return self.username

class KnowledgeGraph(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uri = models.CharField(max_length=255, unique=True, default=generate_kg_uri)
    title = models.CharField(max_length=255)
    author = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name='graphs')
    language = models.CharField(max_length=10, default='en')
    description = models.TextField(blank=True)
    keyword = models.CharField(max_length=255, blank=True)
    version = models.CharField(max_length=50, default='1.0')
    status = models.CharField(max_length=50, default='Final')
    difficulty = models.CharField(max_length=50, default='lom:Medium')
    context = models.CharField(max_length=50, default='lom:Higher_Education')
    intended_end_user_role = models.CharField(max_length=50, default='lom:Student')
    typical_age_range = models.CharField(max_length=50, default='18-')
    typical_learning_time = models.CharField(max_length=50, default='PT1H')

    def __str__(self):
        return self.title

class Node(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uri = models.CharField(max_length=255, unique=True, default=generate_node_uri)
    title = models.CharField(max_length=255)
    graph = models.ForeignKey(KnowledgeGraph, on_delete=models.CASCADE, related_name='nodes')
    graph_uri = models.CharField(max_length=255)
    prerequisite_nodes = models.ManyToManyField('self', symmetrical=False, blank=True)
    language = models.CharField(max_length=10, default='en')
    description = models.TextField(blank=True)
    keyword = models.CharField(max_length=255, blank=True)
    version = models.CharField(max_length=50, default='1.0')
    status = models.CharField(max_length=50, default='Final')
    difficulty = models.CharField(max_length=50, default='lom:Medium')
    context = models.CharField(max_length=50, default='lom:Higher_Education')
    intended_end_user_role = models.CharField(max_length=50, default='lom:Student')
    typical_age_range = models.CharField(max_length=50, default='18-')
    typical_learning_time = models.CharField(max_length=50, default='PT30M')

    def __str__(self):
        return self.title

    def calculate_difficulty(self):
        prereq_count = self.prerequisite_nodes.count()
        if prereq_count == 0:
            self.difficulty = 'lom:Easy'
        elif prereq_count <= 2:
            self.difficulty = 'lom:Medium'
        else:
            self.difficulty = 'lom:Difficult'
        self.save()

class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uri = models.CharField(max_length=255, unique=True, default=generate_question_uri)
    text = models.TextField()
    correct_answer = models.CharField(max_length=255)
    other_answers = models.JSONField(default=list)
    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='questions')
    node_uri = models.CharField(max_length=255)
    language = models.CharField(max_length=10, default='en')
    description = models.TextField(blank=True)
    keyword = models.CharField(max_length=255, blank=True)
    version = models.CharField(max_length=50, default='1.0')
    status = models.CharField(max_length=50, default='Final')
    difficulty = models.CharField(max_length=50, default='lom:Medium')
    context = models.CharField(max_length=50, default='lom:Higher_Education')
    intended_end_user_role = models.CharField(max_length=50, default='lom:Student')
    typical_age_range = models.CharField(max_length=50, default='18-')
    typical_learning_time = models.CharField(max_length=50, default='PT5M')

    def __str__(self):
        return self.text[:50]

class Test(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uri = models.CharField(max_length=255, unique=True, default=generate_test_uri)
    title = models.CharField(max_length=255)
    author = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name='tests')
    graph = models.ForeignKey(KnowledgeGraph, on_delete=models.CASCADE, related_name='tests')
    graph_uri = models.CharField(max_length=255)
    language = models.CharField(max_length=10, default='en')
    description = models.TextField(blank=True)
    keyword = models.CharField(max_length=255, blank=True)
    version = models.CharField(max_length=50, default='1.0')
    status = models.CharField(max_length=50, default='Final')
    difficulty = models.CharField(max_length=50, default='lom:Medium')
    context = models.CharField(max_length=50, default='lom:Higher_Education')
    intended_end_user_role = models.CharField(max_length=50, default='lom:Student')
    typical_age_range = models.CharField(max_length=50, default='18-')
    typical_learning_time = models.CharField(max_length=50, default='PT30M')

    def __str__(self):
        return self.title

class TestQuestion(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()

    class Meta:
        unique_together = ('test', 'question')
        ordering = ['order']

class TestAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uri = models.CharField(max_length=255, unique=True, default=generate_test_attempt_uri)
    student = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name='attempts')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='attempts')
    answers = models.JSONField(default=dict)
    score = models.FloatField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    language = models.CharField(max_length=10, default='en')
    description = models.TextField(blank=True)
    version = models.CharField(max_length=50, default='1.0')
    status = models.CharField(max_length=50, default='Final')

    def __str__(self):
        return f"Attempt by {self.student} on {self.test}"

    def calculate_score(self):
        if not self.completed:
            return
        score = 0
        total = 0
        for tq in self.test.testquestion_set.all():
            question = tq.question
            answer = self.answers.get(str(question.id))
            if answer and answer == question.correct_answer:
                score += 1
            total += 1
        self.score = (score / total) * 100 if total > 0 else 0
        self.save()
