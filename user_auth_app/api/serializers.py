from django.contrib.auth import get_user_model, password_validation
from rest_framework import serializers


User = get_user_model()


class RegistrationSerializer(serializers.Serializer):
    """Serializer for user registration. It includes fields for fullname, email, password, and repeated_password. It validates that the passwords match and that the email is unique. It also creates a new user with a unique username based on the email prefix."""
    fullname = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    repeated_password = serializers.CharField(
        write_only=True, trim_whitespace=False)

    """Custom validation to ensure passwords match and email is unique."""

    def validate(self, attrs):
        if attrs['password'] != attrs['repeated_password']:
            raise serializers.ValidationError("Passwords do not match.")
        if User.objects.filter(email__iexact=attrs['email']).exists():
            raise serializers.ValidationError("Email is already in use.")

        password_validation.validate_password(attrs['password'])
        return attrs

    """Create a new user with a unique username based on the email prefix."""

    def create(self, validated_data):
        fullname = validated_data['fullname'].strip()
        email = validated_data['email'].strip()
        password = validated_data['password']

        base = (email.split('@')[0] or 'user')[:150]
        username = base
        i = 1
        while User.objects.filter(username=username).exists():
            suffix = f"_{i}"
            username = (base[:150 - len(suffix)]) + suffix
            i += 1

        parts = fullname.split()
        first_name = parts[0] if parts else ''
        last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login. It includes fields for email and password. It validates the credentials and returns the authenticated user."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    """Custom validation to authenticate the user based on email and password. It checks if the user exists, if the account is active, and if the password is correct."""

    def validate(self, attrs):
        email = attrs.get('email', '').strip()
        password = attrs.get('password', '')

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid email or password.")
        except User.MultipleObjectsReturned:
            user = User.objects.filter(email__iexact=email).first()

        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")
        if not user.check_password(password):
            raise serializers.ValidationError("Invalid email or password.")

        attrs['user'] = user
        return attrs
