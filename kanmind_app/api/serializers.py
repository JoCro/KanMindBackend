from rest_framework import serializers
from kanmind_app.models import Board, Task, TaskComment
from django.contrib.auth.models import User
from rest_framework.exceptions import NotFound


class BoardListSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    owner_id = serializers.IntegerField(source="owner.id", read_only=True)
    ticket_count = serializers.SerializerMethodField()
    tasks_to_do_count = serializers.SerializerMethodField()
    tasks_high_prio_count = serializers.SerializerMethodField()

    class Meta:
        model = Board
        fields = ["id", "title", "member_count", "owner_id",
                  'ticket_count', 'tasks_to_do_count', 'tasks_high_prio_count']

    def get_ticket_count(self, obj):
        return obj.tasks.count()

    def get_member_count(self, obj):
        return obj.members.count()

    def get_tasks_to_do_count(self, obj):
        return obj.tasks.filter(status=Task.Status.TODO).count()

    def get_tasks_high_prio_count(self, obj):
        return obj.tasks.filter(priority=Task.Priority.HIGH).count()


class BoardCreateSerializer(serializers.ModelSerializer):

    members = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), many=True, write_only=True, required=False
    )

    owner_id = serializers.IntegerField(source="owner.id", read_only=True)
    member_count = serializers.SerializerMethodField(read_only=True)
    ticket_count = serializers.SerializerMethodField(read_only=True)
    tasks_to_do_count = serializers.SerializerMethodField(read_only=True)
    tasks_high_prio_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Board

        fields = [
            "id",
            "title",
            "members",
            "member_count",
            "ticket_count",
            "tasks_to_do_count",
            "tasks_high_prio_count",
            "owner_id",
        ]

    def create(self, validated_data):

        members = validated_data.pop("members", [])
        validated_data.pop("owner", None)

        board = Board.objects.create(
            owner=self.context["request"].user, **validated_data)

        if members:
            board.members.set(members)
        return board

    def get_member_count(self, obj):
        return getattr(obj, 'member_count', None) or obj.members.count()

    def get_ticket_count(self, obj):
        return getattr(obj, 'ticket_count', None) or obj.tasks.count()

    def get_tasks_to_do_count(self, obj):
        return getattr(obj, 'tasks_to_do_count', None) or obj.tasks.filter(status=Task.Status.TODO).count()

    def get_tasks_high_prio_count(self, obj):
        return getattr(obj, 'tasks_high_prio_count', None) or obj.tasks.filter(priority=Task.Priority.HIGH).count()


class UserMinimalSerializer(serializers.ModelSerializer):

    fullname = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'fullname']

    def get_fullname(self, obj):
        full = f"{(obj.first_name or '').strip()} {(obj.last_name or '').strip()}".strip()
        return full or obj.username


class TaskDetailSerializer(serializers.ModelSerializer):
    assignee = UserMinimalSerializer(read_only=True)
    reviewer = UserMinimalSerializer(read_only=True)
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'status', 'priority',
                  'assignee', 'reviewer', 'due_date', 'comments_count']

    def get_comments_count(self, obj):
        return getattr(obj, 'comments_count', None) or obj.comments.count()


class BoardDetailSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(source="owner.id", read_only=True)
    members = UserMinimalSerializer(many=True, read_only=True)
    tasks = TaskDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Board
        fields = ["id", "title", "owner_id", "members", "tasks"]


class BoardPatchSerializer(serializers.ModelSerializer):
    members = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), many=True, required=False, write_only=True)

    owner_data = UserMinimalSerializer(source='owner', read_only=True)
    members_data = UserMinimalSerializer(
        source='members', many=True, read_only=True)

    class Meta:
        model = Board
        fields = ['id', 'title', 'members', 'owner_data', 'members_data']

    def update(self, instance, validated_data):
        if 'title' in validated_data:
            instance.title = validated_data['title']
            instance.save()

        if 'members' in validated_data:
            members = validated_data['members']
            instance.members.set(members)
        return instance


class EmailCheckQuerySerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class TaskCreateSerializer(serializers.ModelSerializer):

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

    def validate(self, attrs):

        board_id = attrs.pop("board")
        board = Board.objects.filter(pk=board_id).first()
        if not board:
            raise NotFound("Board nicht gefunden.")
        attrs["board"] = board

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

    def get_comments_count(self, obj):
        return getattr(obj, 'comments_count', None) or obj.comments.count()


class TaskReadSerializer(serializers.ModelSerializer):
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

    def get_comments_count(self, obj):
        try:
            return obj.comments.count()
        except AttributeError:
            return 0


class TaskUpdateSerializer(serializers.ModelSerializer):
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

    def validate(self, attrs):

        board = self.instance.board

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

    def update(self, instance, validated_data):
        for f in ('title', 'description', 'status', 'priority', 'due_date', 'assignee', 'reviewer'):
            if f in validated_data:
                setattr(instance, f, validated_data[f])
        instance.save()
        return instance


class TaskCommentSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    class Meta:
        model = TaskComment
        fields = ['id', 'created_at', 'author', 'content']
        read_only_fields = ['id', 'created_at', 'author']

    def get_author(self, obj):
        full = f"{(obj.author.first_name or '').strip()} {(obj.author.last_name or '').strip()}".strip()
        return full or obj.author.username

    def validate_content(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError(
                "Der Kommentarinhalt darf nicht leer sein.")
        return value
