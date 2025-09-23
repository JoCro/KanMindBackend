from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied, NotFound
from kanmind_app.models import Board, Task
from .serializers import BoardListSerializer, BoardCreateSerializer, BoardDetailSerializer, UserMinimalSerializer, BoardPatchSerializer, EmailCheckQuerySerializer, TaskCreateSerializer, TaskReadSerializer, TaskUpdateSerializer, TaskCommentSerializer
from django.db.models import Count, Q, Prefetch
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth.models import User
from kanmind_app.models import TaskComment


class BoardListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return (
            Board.objects
            .filter(Q(owner=user) | Q(members=user))
            .select_related("owner")
            .annotate(
                member_count=Count("members", distinct=True),
                ticket_count=Count("tasks", distinct=True),
                tasks_to_do_count=Count(
                    "tasks",
                    filter=Q(tasks__status=Task.Status.TODO),
                    distinct=True,
                ),
                tasks_high_prio_count=Count(
                    "tasks",
                    filter=Q(tasks__priority=Task.Priority.HIGH),
                    distinct=True,
                ),
            )
            .distinct()
            .order_by("id")
        )

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return BoardCreateSerializer
        return BoardListSerializer

    def perform_create(self, serializer):
        board_instance = serializer.save()
        board_instance.members.add(self.request.user)


class BoardDetailUpdateView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "pk"

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return BoardPatchSerializer
        return BoardDetailSerializer

    def get_object(self):
        pk = self.kwargs.get(self.lookup_url_kwarg)
        try:
            board = (Board.objects
                     .select_related("owner")
                     .prefetch_related("members")
                     .get(pk=pk))
        except Board.DoesNotExist:
            raise NotFound("Board nicht gefunden.")

        user = self.request.user

        if board.owner_id != user.id and not board.members.filter(id=user.id).exists():
            raise PermissionDenied(
                "Zugriff verboten: kein Mitglied und nicht Eigentümer.")
        return board

    def perform_destroy(self, instance: Board):
        if instance.owner_id != self.request.user.id:
            raise PermissionDenied(
                "Nur der Eigentümer darf dieses Board löschen.")
        instance.delete()


class EmailCheckView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        q = EmailCheckQuerySerializer(data=request.query_params)
        q.is_valid(raise_exception=True)
        email = q.validated_data['email']

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise NotFound("Nutzer mit dieser E-Mail-Adresse nicht gefunden.")
        return Response(UserMinimalSerializer(user).data, status=200)


class TaskCreateView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskCreateSerializer

    def perform_create(self, serializer):
        board = serializer.validated_data['board']
        user = self.request.user
        is_member = board.members.filter(id=user.id).exists()
        if not (is_member or board.owner_id == user.id):
            raise PermissionDenied(
                "Nur Mitglieder oder der Eigentümer des Boards können Aufgaben erstellen.")
        serializer.save(created_by=user)


class AssignedTasksView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskReadSerializer

    def get_queryset(self):
        user = self.request.user
        return (Task.objects
                .filter(assignee=user)
                .select_related('board', 'assignee', 'reviewer')
                .order_by('due_date', 'id')
                )


class ReviewingTasksView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskReadSerializer

    def get_queryset(self):
        user = self.request.user
        return (Task.objects
                .filter(reviewer=user)
                .select_related('board', 'assignee', 'reviewer')
                .order_by('due_date', 'id')
                )


class TaskDetailUpdateView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskUpdateSerializer
    lookup_url_kwarg = "pk"

    def get_object(self):
        pk = self.kwargs.get(self.lookup_url_kwarg)
        try:
            task = (Task.objects
                    .select_related('board', 'assignee', 'reviewer')
                    .get(pk=pk))
        except Task.DoesNotExist:
            raise NotFound("Task nicht gefunden.")

        user = self.request.user
        board = task.board

        if not (board.owner_id == user.id or board.members.filter(id=user.id).exists()):
            raise PermissionDenied(
                "Zugriff verboten: kein Mitglied und nicht Eigentümer des Boards.")
        return task

    def perform_destroy(self, instance: Task):
        user = self.request.user
        creator_id = getattr(instance, 'created_by_id', None)
        if not (creator_id == user.id or instance.board.owner_id == user.id):
            raise PermissionDenied(
                "Nur der Ersteller des Tasks oder der Eigentümer des Boards darf diesen Task löschen.")
        instance.delete()


class TaskCommentListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskCommentSerializer
    lookup_url_kwarg = 'task_id'

    def _get_task_or_404_checked(self):
        task_id = self.kwargs.get(
            self.lookup_url_kwarg) or self.kwargs.get('pk')
        try:
            task = Task.objects.select_related("board").get(pk=task_id)
        except Task.DoesNotExist:
            raise NotFound("Task nicht gefunden.")
        user = self.request.user
        board = task.board
        if not (board.owner_id == user.id or board.members.filter(id=user.id).exists()):
            raise PermissionDenied(
                "Zugriff verboten: kein Mitglied des Boards.")
        return task

    def get_queryset(self):
        task = self._get_task_or_404_checked()
        return (
            TaskComment.objects
            .filter(task=task)
            .select_related("author")
            .order_by("created_at", "id")
        )

    def perform_create(self, serializer):
        task = self._get_task_or_404_checked()
        serializer.save(task=task, author=self.request.user)


class TaskCommentDestroyView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg_task = 'task_id'
    lookup_url_kwarg_comment = 'comment_id'

    def get_object(self):
        task_id = self.kwargs.get(self.lookup_url_kwarg_task)
        comment_id = self.kwargs.get(self.lookup_url_kwarg_comment)

        try:
            task = Task.objects.only('id').get(pk=task_id)
        except Task.DoesNotExist:
            raise NotFound('Task wurde nicht gefunden.')

        try:
            comment = TaskComment.objects.select_related(
                'author', 'task').get(pk=comment_id, task=task)
        except TaskComment.DoesNotExist:
            raise NotFound('Kommentar konnte nicht gefunden werden.')

        if comment.author_id != self.request.user.id:
            raise PermissionDenied(
                'Nur der Ersteller des KOmmentars darf ihn löschen.')

        return comment
