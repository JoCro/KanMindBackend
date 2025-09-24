from rest_framework import serializers
from kanmind_app.models import Board, Task, TaskComment
from django.contrib.auth.models import User
from rest_framework.exceptions import NotFound, PermissionDenied
from collections import OrderedDict


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


class UserMinimalSerializer(serializers.ModelSerializer):

    """
    Serializer for minimal User representation, including full name.
    """
    fullname = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'fullname']

    """
    retrieves the full name of the user, falling back to username if not available.
    """

    def get_fullname(self, obj):
        full = f"{(obj.first_name or '').strip()} {(obj.last_name or '').strip()}".strip()
        return full or obj.username


class TaskDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for detailed Task representation, including assignee, reviewer, and comment count.
    """
    assignee = UserMinimalSerializer(read_only=True)
    reviewer = UserMinimalSerializer(read_only=True)
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'status', 'priority',
                  'assignee', 'reviewer', 'due_date', 'comments_count']

    """
    retrieves the count of comments for the task.
    """

    def get_comments_count(self, obj):
        return getattr(obj, 'comments_count', None) or obj.comments.count()


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


class EmailCheckQuerySerializer(serializers.Serializer):
    """
    serializer for validating email input.
    """
    email = serializers.EmailField(required=True)


class TaskCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating Tasks. Includes validation for board, assignee, and reviewer.
    """

    board = serializers.IntegerField(
        write_only=True)
    assignee_id = serializers.IntegerField(
        required=False, allow_null=True, write_only=True)
    reviewer_id = serializers.IntegerField(
        required=False, allow_null=True, write_only=True)

    assignee = UserMinimalSerializer(read_only=True)
    reviewer = UserMinimalSerializer(read_only=True)
    comments_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "board",
            "title",
            "description",
            "status",
            "priority",
            "assignee_id",
            "reviewer_id",
            "assignee",
            "reviewer",
            "due_date",
            "comments_count",
        ]

    """
    Validates the input data for creating a Task, ensuring the board exists and the user has permission to add tasks to it. Also validates assignee and reviewer if provided.
    """

    def validate(self, attrs):

        board_id = attrs.pop("board")
        board = Board.objects.filter(pk=board_id).first()
        if not board:
            raise NotFound("Board nicht gefunden.")
        attrs["board"] = board

        user = self.context["request"].user
        if board.owner_id != user.id and not board.members.filter(id=user.id).exists():
            raise PermissionDenied(
                "Du musst Mitglied des Boards sein, um eine Task zu erstellen.")

        for key_in, key_out in (("assignee_id", "assignee"), ("reviewer_id", "reviewer")):
            uid = attrs.pop(key_in, None)
            if uid is None:
                attrs[key_out] = None
                continue
            user = User.objects.filter(pk=uid).first()
            if not user:
                raise serializers.ValidationError(
                    {key_in: "Ungültige Benutzer-ID."})
            if not board.members.filter(id=user.id).exists():
                raise serializers.ValidationError(
                    {key_in: "Benutzer ist kein Mitglied dieses Boards."})
            attrs[key_out] = user

        status = attrs.get("status")
        priority = attrs.get("priority")
        valid_status = {c[0] for c in Task.Status.choices}
        valid_priority = {c[0] for c in Task.Priority.choices}
        if status not in valid_status:
            raise serializers.ValidationError(
                {"status": f"Ungültiger Status. Erlaubt: {sorted(valid_status)}"})
        if priority not in valid_priority:
            raise serializers.ValidationError(
                {"priority": f"Ungültige Priority. Erlaubt: {sorted(valid_priority)}"})

        return attrs

    def to_representation(self, instance):
        """Custom representation to include board ID instead of nested object."""
        data = super().to_representation(instance)
        data['board'] = instance.board_id

        order = ['id', 'board', 'title', 'description', 'status', 'priority',
                 'assignee', 'reviewer', 'due_date', 'comments_count']
        return OrderedDict((k, data.get(k)) for k in order if k in data)

    """
    retrieves the count of comments for the task.
    """

    def get_comments_count(self, obj):
        return getattr(obj, 'comments_count', None) or obj.comments.count()


class TaskReadSerializer(serializers.ModelSerializer):
    """
    Serializer for reading Task details, including board ID, assignee, reviewer, and comment count.
    """
    board = serializers.IntegerField(source='board.id', read_only=True)
    assignee = UserMinimalSerializer(read_only=True)
    reviewer = UserMinimalSerializer(read_only=True)
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "board",
            "title",
            "description",
            "status",
            "priority",
            "assignee",
            "reviewer",
            "due_date",
            "comments_count",
        ]
    """
    retrieves the count of comments for the task. 
    """

    def get_comments_count(self, obj):
        try:
            return obj.comments.count()
        except AttributeError:
            return 0


class TaskUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating Task details, including assignee and reviewer validation.
    """
    assignee_id = serializers.IntegerField(
        required=False, allow_null=True, write_only=True)
    reviewer_id = serializers.IntegerField(
        required=False, allow_null=True, write_only=True)

    assignee = UserMinimalSerializer(read_only=True)
    reviewer = UserMinimalSerializer(read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "status",
            "priority",
            "assignee_id",
            "reviewer_id",
            "assignee",
            "reviewer",
            "due_date",

        ]

    """
    Validates the input data for updating a Task, ensuring assignee and reviewer are valid users and members of the board. Also validates status and priority if provided.
    """

    def validate(self, attrs):

        board = self.instance.board

        """Helper function to resolve user IDs to User instances and validate membership. if the user ID is None, sets the corresponding field to None. If the user ID is invalid or the user is not a member of the board, raises a ValidationError."""
        def resolve_user(field_in, field_out):
            if field_in in attrs:
                uid = attrs.pop(field_in)
                if uid is None:
                    attrs[field_out] = None
                else:
                    user = User.objects.filter(pk=uid).first()
                    if not user:
                        raise serializers.ValidationError(
                            {field_in: "Ungültige Benutzer-ID."})
                    if not (board.owner_id == user.id or board.members.filter(id=user.id).exists()):
                        raise serializers.ValidationError(
                            {field_in: "Benutzer ist kein Mitglied dieses Boards."})
                    attrs[field_out] = user

        resolve_user("assignee_id", "assignee")
        resolve_user("reviewer_id", "reviewer")

        valid_status = {c[0] for c in Task.Status.choices}
        valid_priority = {c[0] for c in Task.Priority.choices}
        if "status" in attrs and attrs["status"] not in valid_status:
            raise serializers.ValidationError(
                {"status": f"Ungültiger Status. Erlaubt: {sorted(valid_status)}"})
        if "priority" in attrs and attrs["priority"] not in valid_priority:
            raise serializers.ValidationError(
                {"priority": f"Ungültige Priority. Erlaubt: {sorted(valid_priority)}"})
        return attrs

    """updates the Task instance with provided fields. Only fields present in the validated data are updated."""

    def update(self, instance, validated_data):
        for f in ('title', 'description', 'status', 'priority', 'due_date', 'assignee', 'reviewer'):
            if f in validated_data:
                setattr(instance, f, validated_data[f])
        instance.save()
        return instance


class TaskCommentSerializer(serializers.ModelSerializer):
    """Serializer for TaskComment, including author details and content validation."""
    author = serializers.SerializerMethodField()

    class Meta:
        model = TaskComment
        fields = ['id', 'created_at', 'author', 'content']
        read_only_fields = ['id', 'created_at', 'author']

    """retrieves the author's full name or username for the comment."""

    def get_author(self, obj):
        full = f"{(obj.author.first_name or '').strip()} {(obj.author.last_name or '').strip()}".strip()
        return full or obj.author.username

    """validates that the comment content is not empty or just whitespace."""

    def validate_content(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError(
                "Der Kommentarinhalt darf nicht leer sein.")
        return value
