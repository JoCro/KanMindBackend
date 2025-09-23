from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.authtoken.models import Token
from .serializers import RegistrationSerializer, LoginSerializer


class RegistrationView(APIView):
    """View for user registration. It handles POST requests to create a new user and return an authentication token, fullname, email, and user ID"""
    permission_classes = [permissions.AllowAny]

    """Handle POST request to register a new user and return an auth token and user details."""

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        token, _ = Token.objects.get_or_create(user=user)
        fullname = f"{user.first_name} {user.last_name}".strip(
        ) or user.username

        return Response({
            'token': token.key,
            'fullname': fullname,
            'email': user.email,
            'user_id': user.id,
        },
            status=status.HTTP_201_CREATED,)


class LoginView(APIView):
    """View for user login. It handles POST requests to authenticate a user and return an authentication token, fullname, email, and user ID."""
    permission_classes = [permissions.AllowAny]

    """Handle POST request to authenticate a user and return an auth token and user details."""

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        token, _ = Token.objects.get_or_create(user=user)
        fullname = f"{user.first_name} {user.last_name}".strip(
        ) or user.username

        return Response({

            'token': token.key,
            'fullname': fullname,
            'email': user.email,
            'user_id': user.id,
        },
            status=status.HTTP_200_OK,
        )
