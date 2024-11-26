# your_app_name/serializers.py
from rest_framework import serializers
from .models import AppUser, KnowledgeGraph, GraphNode, Question, Test , TestAttempt
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppUser
        fields = ['username', 'password', 'email', 'first_name', 'last_name', 'user_type']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        user = AppUser(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        if isinstance(user, AppUser):
            token['user_type'] = user.user_type
        else:
            token['user_type'] = 'admin'
        return token


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'text', 'correct_answer', 'other_answers', 'node']  

    node = serializers.PrimaryKeyRelatedField(queryset=GraphNode.objects.all()) 


class GraphNodeSerializer(serializers.ModelSerializer):
    prerequisite_nodes = serializers.PrimaryKeyRelatedField(queryset=GraphNode.objects.all(), many=True, required=False)
    dependent_nodes = serializers.PrimaryKeyRelatedField(queryset=GraphNode.objects.all(), many=True, required=False)
    
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = GraphNode
        fields = ['id', 'graph', 'title', 'prerequisite_nodes', 'dependent_nodes', 'questions']

    def update(self, instance, validated_data):
        prerequisite_nodes_data = validated_data.pop('prerequisite_nodes', None)
        dependent_nodes_data = validated_data.pop('dependent_nodes', None)

        instance.title = validated_data.get('title', instance.title)
        instance.save()

        if prerequisite_nodes_data is not None:
            instance.prerequisite_nodes.set(prerequisite_nodes_data)

        if dependent_nodes_data is not None:
            instance.dependent_nodes.set(dependent_nodes_data)

        return instance


class KnowledgeGraphSerializer(serializers.ModelSerializer):
    nodes = GraphNodeSerializer(many=True, read_only=True)

    class Meta:
        model = KnowledgeGraph
        fields = ['id', 'title', 'created_by', 'nodes']



class TestSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    graph_name = serializers.CharField(source='graph.title', read_only=True)
    questions = QuestionSerializer(many=True, read_only=True)
    class Meta:
        model = Test
        fields = ['id', 'title', 'author_name', 'graph_name', 'questions']

class TestAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestAttempt
        fields = ['id', 'test', 'student', 'answers', 'completed', 'score']