from django.db import models
from django.contrib.auth.models import User


class Board(models.Model):
    """Model representing a board. It includes fields for title, owner, members, and creation timestamp."""

    title = models.CharField(max_length=100)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='owned_boards')
    members = models.ManyToManyField(User, related_name='boards', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    """String representation of the Board model. it returns the title of the board (itself)."""

    def __str__(self):
        return self.title


class Task(models.Model):
    """Model representing a task within a board. it includes fields for title, description, status, priority, assignee, reviewer, due date, and timestamps."""

    class Status(models.TextChoices):
        """ Status choices for a task. """

        TODO = 'to-do', 'To do'
        IN_PROGRESS = 'in-progress', 'In progress'
        REVIEW = 'review', 'Review'
        DONE = 'done', 'Done'

    class Priority(models.TextChoices):
        """ Priority choices for a task. """

        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'

    board = models.ForeignKey(
        Board, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.TODO)
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    assignee = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_tasks')
    reviewer = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='review_tasks')
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='created_tasks',
        null=True, blank=True
    )

    """String representation of the Board model. it returns the title of the board (itself)."""

    def __str__(self):
        return self.title


class TaskComment(models.Model):
    """Model representing comments on tasks. It includes fields for the associated task, author, content, and creation timestamp."""
    task = models.ForeignKey(
        'Task', on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='task_comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    """String representation of the TaskComment model. it returns the comment's primary key and associated task's primary key."""

    def __str__(self):
        return f"Comment #{self.pk} on Task #{self.task_id}"
