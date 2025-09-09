from django.contrib import admin
from django.urls import path, include
from .views import BoardListCreateView, BoardDetailUpdateView, EmailCheckView, TaskCreateView, AssignedTasksView, ReviewingTasksView, TaskDetailUpdateView, TaskCommentListCreateView, TaskCommentDestroyView

urlpatterns = [
    path('boards/', BoardListCreateView.as_view(), name='board-list'),
    path('boards/<int:pk>/', BoardDetailUpdateView.as_view(), name='board-detail'),
    path('email-check/', EmailCheckView.as_view(), name='email-check'),
    path('tasks/', TaskCreateView.as_view(), name='task-create'),
    path('tasks/assigned-to-me/', AssignedTasksView.as_view(),
         name='tasks-assigned-to-me'),

    path('tasks/reviewing/', ReviewingTasksView.as_view(), name='tasks-reviewing'),
    path('tasks/<int:pk>/', TaskDetailUpdateView.as_view(), name='task-detail'),
    path('tasks/<int:pk>/comments/',
         TaskCommentListCreateView.as_view(), name='task-comments'),

    path('tasks/<int:task_id>/comments/<int:comment_id>/',
         TaskCommentDestroyView.as_view(), name='task-comment-delete'),
]
