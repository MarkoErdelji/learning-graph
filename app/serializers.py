from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import AppUser, KnowledgeGraph, Node, Question, Test, TestAttempt, TestQuestion

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['user_type'] = user.user_type
        return token

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = AppUser
        fields = ['id', 'username', 'email', 'user_type', 'uri', 'password', 'first_name', 'last_name']
        read_only_fields = ['uri']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = AppUser(**validated_data)
        user.set_password(password)  # <-- important!
        user.save()
        return user

class KnowledgeGraphSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(queryset=AppUser.objects.all(), required=False)
    class Meta:
        model = KnowledgeGraph
        fields = ['id', 'uri', 'title', 'author', 'language', 'description', 'keyword', 'version', 'status',
                  'difficulty', 'context', 'intended_end_user_role', 'typical_age_range', 'typical_learning_time']
        read_only_fields = ['uri']



class QuestionSerializer(serializers.ModelSerializer):
    node = serializers.PrimaryKeyRelatedField(queryset=Node.objects.all())
    class Meta:
        model = Question
        fields = ['id', 'uri', 'text', 'correct_answer', 'other_answers', 'node', 'language', 'description',
                  'keyword', 'version', 'status', 'difficulty', 'context', 'intended_end_user_role',
                  'typical_age_range', 'typical_learning_time']
        read_only_fields = ['uri', 'node_uri']

    def validate(self, data):
        if 'node' in data:
            data['node_uri'] = data['node'].uri
        return data

class GraphNodeSerializer(serializers.ModelSerializer):
    graph = serializers.UUIDField()  
    prerequisite_nodes = serializers.PrimaryKeyRelatedField(many=True, queryset=Node.objects.all(), required=False)
    questions = QuestionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Node
        fields = ['id', 'title', 'graph', 'language', 'description', 'keyword', 'version',
                  'status', 'difficulty', 'context', 'intended_end_user_role',
                  'typical_age_range', 'typical_learning_time', 'prerequisite_nodes', 'questions']

    def validate_graph(self, value):
        # Validate that the graph exists
        try:
            KnowledgeGraph.objects.get(id=value)
        except KnowledgeGraph.DoesNotExist:
            raise serializers.ValidationError("Invalid graph ID: Graph does not exist.")
        return value
    
class TestSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(queryset=AppUser.objects.all())
    graph = serializers.PrimaryKeyRelatedField(queryset=KnowledgeGraph.objects.all())
    questions = serializers.ListField(child=serializers.DictField(), write_only=True, required=False)
    author_name = serializers.SerializerMethodField()
    graph_name = serializers.CharField(source='graph.title', read_only=True)

    class Meta:
        model = Test
        fields = [
            'id', 'uri', 'title', 'author', 'author_name', 'graph', 'graph_name', 'questions',
            'language', 'description', 'keyword', 'version', 'status', 'difficulty',
            'context', 'intended_end_user_role', 'typical_age_range', 'typical_learning_time'
        ]
        read_only_fields = ['uri', 'graph_uri', 'author_name', 'graph_name']

    def get_author_name(self, obj):
        return f"{obj.author}".strip()

    def validate(self, data):
        if 'graph' in data:
            data['graph_uri'] = data['graph'].uri
        return data


class TestAttemptSerializer(serializers.ModelSerializer):
    student = serializers.PrimaryKeyRelatedField(queryset=AppUser.objects.all())
    test = serializers.PrimaryKeyRelatedField(queryset=Test.objects.all())
    class Meta:
        model = TestAttempt
        fields = ['id', 'uri', 'student', 'test', 'answers', 'score', 'completed', 'language', 'description',
                  'version', 'status']
        read_only_fields = ['uri', 'score']

class TestAttemptDetailSerializer(serializers.ModelSerializer):
    student = UserSerializer()
    test = TestSerializer()
    class Meta:
        model = TestAttempt
        fields = ['id', 'uri', 'student', 'test', 'answers', 'score', 'completed', 'language', 'description',
                  'version', 'status']
