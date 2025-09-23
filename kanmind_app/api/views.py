from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied, NotFound
from kanmind_app.models import Board, Task
from .serializers import BoardListSerializer, BoardCreateSerializer, BoardDetailSerializer, UserMinimalSerializer, BoardPatchSerializer, EmailCheckQuerySerializer, TaskCreateSerializer, TaskReadSerializer, TaskUpdateSerializer, TaskCommentSerializer
from django.db.models import Count, Q, Prefetch
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth.models import User
from kanmind_app.models import TaskComment


"""
GET: List of Boards (only those where the user is owner or member)
POST: Create a new Board (the creating user becomes the owner and a member)
Permissions: Authenticated users only
Response-Fileds: id, title, owner, member_count, ticket_count, tasks_to_do_count, tasks_high_prio_count

"""


class BoardListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    """
returns a queryset of Boards where the requesting user is either the owner or a member.
"""

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
    """
    Returns the appropriate serializer class based on the HTTP method of the request.
    If the request method is POST, it returns BoardCreateSerializer for creating a new board.
"""

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return BoardCreateSerializer
        return BoardListSerializer
    """
    When creating a new board, this method saves the board instance and adds the requesting user as a member.
"""

    def perform_create(self, serializer):
        board_instance = serializer.save()
        board_instance.members.add(self.request.user)


"""
GET: Details of a specific Board (only if the user is owner or member)
PUT/PATCH: Update a specific Board (only if the user is owner or member)
DELETE: Delete a specific Board (only if the user is the owner)
Permissions: Authenticated users only
"""


class BoardDetailUpdateView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "pk"

    """
    Returns the appropriate serializer class based on the HTTP method of the request.
    If the request method is PUT or PATCH, it returns BoardPatchSerializer for updating the board.
    Otherwise, it returns BoardDetailSerializer for retrieving board details.
"""

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return BoardPatchSerializer
        return BoardDetailSerializer

    """
    Retrieves a Board object based on the provided primary key (pk) in the URL.
    It checks if the requesting user is either the owner or a member of the board.
    If the board does not exist or the user does not have permission, it raises appropriate exceptions
"""

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

    """
    Deletes the specified Board instance if the requesting user is the owner.
    If the user is not the owner, it raises a PermissionDenied exception.
"""

    def perform_destroy(self, instance: Board):
        if instance.owner_id != self.request.user.id:
            raise PermissionDenied(
                "Nur der Eigentümer darf dieses Board löschen.")
        instance.delete()


"""
API view to check if a user with a given email exists and return minimal user info.
Will be executed by the frontend
"""


class EmailCheckView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    """
    Handles GET requests to check if a user with the provided email exists.
    If found, returns minimal user information; otherwise, raises a NotFound exception.
"""

    def get(self, request):
        q = EmailCheckQuerySerializer(data=request.query_params)
        q.is_valid(raise_exception=True)
        email = q.validated_data['email']

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise NotFound("Nutzer mit dieser E-Mail-Adresse nicht gefunden.")
        return Response(UserMinimalSerializer(user).data, status=200)


"""
 GET: List of Tasks assigned to the user
 POST: Create a new Task (only if the user is member or owner of the board he or she wants to create the task in)
 permissions: Authenticated users only
 Response-Fields for GET: id, title, description, status, priority, due_date, board (id, title), assignee (id, username), reviewer (id, username)
 Response-Fields for POST: id, title, description, status, priority, due_date, board (id, title), assignee (id, username), reviewer (id, username), created_by (id, username)
"""


class TaskCreateView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskCreateSerializer

    """
    Validates and saves a new Task instance, ensuring that the requesting user is either a member or the owner of the associated board.
    Raises PermissionDenied if the user does not have the required permissions.
"""

    def perform_create(self, serializer):
        board = serializer.validated_data['board']
        user = self.request.user
        is_member = board.members.filter(id=user.id).exists()
        if not (is_member or board.owner_id == user.id):
            raise PermissionDenied(
                "Nur Mitglieder oder der Eigentümer des Boards können Aufgaben erstellen.")
        serializer.save(created_by=user)


"""
GET: List of Tasks assigned to the authenticated user
Permissions: Authenticated users only
"""


class AssignedTasksView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskReadSerializer

    """
    Returns a queryset of Tasks that are assigned to the requesting user, ordered by due date and ID.
"""

    def get_queryset(self):
        user = self.request.user
        return (Task.objects
                .filter(assignee=user)
                .select_related('board', 'assignee', 'reviewer')
                .order_by('due_date', 'id')
                )


"""
get: List of Tasks where the authenticated user is the reviewer
Permissions: Authenticated users only
"""


class ReviewingTasksView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskReadSerializer

    """
    Returns a queryset of Tasks that the requesting user is reviewing, ordered by due date and ID.
"""

    def get_queryset(self):
        user = self.request.user
        return (Task.objects
                .filter(reviewer=user)
                .select_related('board', 'assignee', 'reviewer')
                .order_by('due_date', 'id')
                )


"""
GET: Details of a specific Task (only if the user is owner or member of the board the task belongs to)
PUT/PATCH: Update a specific Task (only if the user is owner or member of the board the task belongs to)
DELETE: Delete a specific Task (only if the user is the creator of the task or the owner of the board the task belongs to)
Permissions: Authenticated users only
"""


class TaskDetailUpdateView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskUpdateSerializer
    lookup_url_kwarg = "pk"

    """
 retrieves a Task object based on the provided primary key (pk) in the URL.
    It checks if the requesting user is either the owner or a member of the board associated with the task.
    If the task does not exist or the user does not have permission, it raises appropriate exceptions
"""

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

    """
    Deletes the specified Task instance if the requesting user is either the creator of the task or the owner of the associated board.
    If the user does not have the required permissions, it raises a PermissionDenied exception.
"""

    def perform_destroy(self, instance: Task):
        user = self.request.user
        creator_id = getattr(instance, 'created_by_id', None)
        if not (creator_id == user.id or instance.board.owner_id == user.id):
            raise PermissionDenied(
                "Nur der Ersteller des Tasks oder der Eigentümer des Boards darf diesen Task löschen.")
        instance.delete()


"""
get: List of Comments for a specific Task (only if the user is owner or member of the board the task belongs to)
post: Create a new Comment for a specific Task (only if the user is owner or member of the board the task belongs to)
delete: Delete a specific Comment (only if the user is the author of the comment)
Permissions: Authenticated users only
Response-Fields for GET: id, content, created_at, author (id, username)
Response-Fields for POST: id, content, created_at, author (id, username), task (id)
"""


class TaskCommentListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskCommentSerializer
    lookup_url_kwarg = 'task_id'

    """
    Helper method to retrieve a Task object and check if the requesting user has permission to access it.
    Raises NotFound if the task does not exist and PermissionDenied if the user is neither the owner nor a member of the associated board.
"""

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

    """
    Returns a queryset of TaskComments associated with the specified Task, ensuring the requesting user has permission to view them.
"""

    def get_queryset(self):
        task = self._get_task_or_404_checked()
        return (
            TaskComment.objects
            .filter(task=task)
            .select_related("author")
            .order_by("created_at", "id")
        )

    """
    Validates and saves a new TaskComment instance, associating it with the specified Task and setting the author to the requesting user.
"""

    def perform_create(self, serializer):
        task = self._get_task_or_404_checked()
        serializer.save(task=task, author=self.request.user)


"""
DELETE: Delete a specific Comment (only if the user is the author of the comment)
"""


class TaskCommentDestroyView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg_task = 'task_id'
    lookup_url_kwarg_comment = 'comment_id'

    """
    Retrieves a TaskComment object based on the provided task_id and comment_id in the URL.
    It checks if the requesting user is the author of the comment.
    If the task or comment does not exist, or if the user is not the author, it raises appropriate exceptions.
"""

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
