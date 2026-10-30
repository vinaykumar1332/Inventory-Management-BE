from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers

from .models import Role, User

# Fields exposed on every user response (auth endpoints + admin list)
USER_FIELDS = [
    "id", "email", "full_name", "role", "is_active", "is_staff",
    "phone", "employee_id", "designation", "first_login_completed",
    "is_approved", "avatar_url",
    "created_at", "updated_at",
]


class UserSerializer(serializers.ModelSerializer):
    """Read-only snapshot of one user. Used by auth endpoints (me, login, signup)."""

    class Meta:
        model = User
        fields = USER_FIELDS
        read_only_fields = USER_FIELDS


# ---------- Signup / Login ----------

class SignupSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_full_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Enter your full name.")
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs):
        candidate = User(email=attrs["email"], full_name=attrs["full_name"])
        try:
            password_validation.validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        try:
            with transaction.atomic():
                return User.objects.create_user(
                    email=validated_data["email"],
                    full_name=validated_data["full_name"],
                    password=validated_data["password"],
                    role=Role.SITE_MANAGER,
                )
        except IntegrityError as exc:
            raise serializers.ValidationError({"email": ["An account with this email already exists."]}) from exc


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)


# ---------- Admin user management ----------

class AdminCreateUserSerializer(serializers.Serializer):
    """Create any role of user. Only admins/super-admins reach this endpoint."""

    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    role = serializers.ChoiceField(choices=Role.choices, default=Role.SITE_MANAGER)
    phone = serializers.CharField(max_length=30, allow_blank=True, default="")
    employee_id = serializers.CharField(max_length=50, allow_blank=True, default="")
    designation = serializers.CharField(max_length=100, allow_blank=True, default="")

    def validate_full_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Enter the full name.")
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs):
        candidate = User(email=attrs["email"], full_name=attrs["full_name"])
        try:
            password_validation.validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        role = validated_data.pop("role", Role.SITE_MANAGER)
        password = validated_data.pop("password")
        is_staff = role in (Role.SUPER_ADMIN, Role.ADMIN)
        is_superuser = role == Role.SUPER_ADMIN
        try:
            with transaction.atomic():
                return User.objects.create_user(
                    email=validated_data["email"],
                    full_name=validated_data["full_name"],
                    password=password,
                    role=role,
                    phone=validated_data.get("phone", ""),
                    employee_id=validated_data.get("employee_id", ""),
                    designation=validated_data.get("designation", ""),
                    is_staff=is_staff,
                    is_superuser=is_superuser,
                )
        except IntegrityError as exc:
            raise serializers.ValidationError({"email": ["An account with this email already exists."]}) from exc


class AdminUpdateUserSerializer(serializers.ModelSerializer):
    """Partial update. All fields optional; email uniqueness is re-checked."""

    class Meta:
        model = User
        fields = ["full_name", "role", "phone", "employee_id", "designation", "is_active", "first_login_completed", "is_approved", "avatar_url"]
        extra_kwargs = {f: {"required": False} for f in fields}

    def validate_role(self, value):
        # Prevent anyone from accidentally downgrading to STOREKEEPER via the API
        # (that role has no screens; leave it as a future concern).
        return value

    def validate_full_name(self, value):
        return value.strip()

    def update(self, instance, validated_data):
        role = validated_data.get("role")
        if role is not None:
            # Keep is_staff / is_superuser in sync with the role
            instance.is_staff = role in (Role.SUPER_ADMIN, Role.ADMIN)
            instance.is_superuser = role == Role.SUPER_ADMIN
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
