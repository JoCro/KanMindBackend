from rest_framework import serializers
from django.db.models import Count, Q
from django.contrib.auth import get_user_model

from kanmind_app.models import Board, Task
from .tasks import UserMinimalSerializer, TaskReadSerializer, TaskDetailSerializer
from django.contrib.auth.models import User
from rest_framework.exceptions import NotFound, PermissionDenied
from collections import OrderedDict

User = get_user_model()


class BoardListSerializer(serializers.ModelSerializer):
    """
Serializer for listing Boards. Includes methods to count members and tasks.
"""
    member_count = serializers.SerializerMethodField()
    owner_id = serializers.IntegerField(source="owner.id", read_only=True)
    ticket_count = serializers.SerializerMethodField()
    tasks_to_do_count = serializers.SerializerMethodField()
    tasks_high_prio_count = serializers.SerializerMethodField()

    class Meta:
        model = Board
        fields = ["id", "title", "member_count", "owner_id",
                  'ticket_count', 'tasks_to_do_count', 'tasks_high_prio_count']

    """
    Retrieves the count of tickets for the board.
    """

    def get_ticket_count(self, obj):
        return obj.tasks.count()

    """
    retrieves the count of members for the board.
    """

    def get_member_count(self, obj):
        return obj.members.count()

    """
    retrieves the count of tasks with status TODO for the board.
    """

    def get_tasks_to_do_count(self, obj):
        return obj.tasks.filter(status=Task.Status.TODO).count()

    """
    retrieves the count of tasks with high priority for the board.
    """

    def get_tasks_high_prio_count(self, obj):
        return obj.tasks.filter(priority=Task.Priority.HIGH).count()


class BoardCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for Board creation. Includes validation for member IDs and methods to count members and tasks.
    """

    members = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        write_only=True,
        required=False,
        allow_empty=True,
    )

    owner_id = serializers.IntegerField(source="owner.id", read_only=True)
    member_count = serializers.SerializerMethodField(read_only=True)
    ticket_count = serializers.SerializerMethodField(read_only=True)
    tasks_to_do_count = serializers.SerializerMethodField(read_only=True)
    tasks_high_prio_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Board
        fields = [
            "id", "title", "members",
            "member_count", "ticket_count",
            "tasks_to_do_count", "tasks_high_prio_count",
            "owner_id",
        ]

    """
    Validates the list of member IDs to ensure they exist in the User model.
    """

    def validate_members(self, member_ids):
        if not member_ids:
            return []

        ids = list(dict.fromkeys(int(i) for i in member_ids))
        found = set(User.objects.filter(
            id__in=ids).values_list("id", flat=True))
        missing = sorted(set(ids) - found)
        if missing:

            raise serializers.ValidationError(
                f"Die folgenden Benutzer-IDs existieren nicht: {missing}."
            )
        return ids

    """
    Creates a Board instance and assigns members if provided.
    """

    def create(self, validated_data):
        member_ids = validated_data.pop("members", [])

        board = Board.objects.create(
            owner=self.context["request"].user, **validated_data)
        if member_ids:
            board.members.set(User.objects.filter(id__in=member_ids))
        return board

    """
    Retrieves the count of members for the board.
    """

    def get_member_count(self, obj):
        return getattr(obj, "member_count", None) or obj.members.count()

    """
    Retrieves the count of tickets for the board.
    """

    def get_ticket_count(self, obj):
        return getattr(obj, "ticket_count", None) or obj.tasks.count()

    """
    Retrieves the count of tasks with status TODO for the board.
    """

    def get_tasks_to_do_count(self, obj):
        return getattr(obj, "tasks_to_do_count", None) or obj.tasks.filter(status=Task.Status.TODO).count()

    """
    Retrieves the count of tasks with high priority for the board.
    """

    def get_tasks_high_prio_count(self, obj):
        return getattr(obj, "tasks_high_prio_count", None) or obj.tasks.filter(priority=Task.Priority.HIGH).count()


class BoardDetailSerializer(serializers.ModelSerializer):
    """
    serializer for detailed Board representation, including owner, members, and tasks.
    """
    owner_id = serializers.IntegerField(source="owner.id", read_only=True)
    members = UserMinimalSerializer(many=True, read_only=True)
    tasks = TaskDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Board
        fields = ["id", "title", "owner_id", "members", "tasks"]


class BoardPatchSerializer(serializers.ModelSerializer):
    """
    serializer for updating Board details, including title and members.
    """
    members = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), many=True, required=False, write_only=True)

    owner_data = UserMinimalSerializer(source='owner', read_only=True)
    members_data = UserMinimalSerializer(
        source='members', many=True, read_only=True)

    class Meta:
        model = Board
        fields = ['id', 'title', 'members', 'owner_data', 'members_data']

    """
    updates the Board instance with new title and members if provided. when updating members, it replaces the existing members with the new list. if no members are provided, the existing members remain unchanged.
    """

    def update(self, instance, validated_data):
        if 'title' in validated_data:
            instance.title = validated_data['title']
            instance.save()

        if 'members' in validated_data:
            members = validated_data['members']
            instance.members.set(members)
        return instance
