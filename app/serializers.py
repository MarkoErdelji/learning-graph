# your_app_name/serializers.py
from rest_framework import serializers
from .models import AppUser, KnowledgeGraph, GraphNode, Question
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
    dependent_nodes = serializers.PrimaryKeyRelatedField(queryset=GraphNode.objects.all(), many=True, required=False)
    prerequisite_nodes = serializers.PrimaryKeyRelatedField(queryset=GraphNode.objects.all(), many=True, required=False)
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = GraphNode
        fields = ['id', 'graph', 'title', 'prerequisite_nodes', 'dependent_nodes', 'questions']


class KnowledgeGraphSerializer(serializers.ModelSerializer):
    nodes = GraphNodeSerializer(many=True, read_only=True)

    class Meta:
        model = KnowledgeGraph
        fields = ['id', 'title', 'created_by', 'nodes']
