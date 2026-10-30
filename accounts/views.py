from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Role, User
from .serializers import (
    AdminCreateUserSerializer,
    AdminUpdateUserSerializer,
    LoginSerializer,
    SignupSerializer,
    UserSerializer,
)


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _is_admin_or_above(user) -> bool:
    return user.role in (Role.SUPER_ADMIN, Role.ADMIN)


def _is_super_admin(user) -> bool:
    return user.role == Role.SUPER_ADMIN


# ------------------------------------------------------------------ #
# Auth endpoints                                                       #
# ------------------------------------------------------------------ #

@ensure_csrf_cookie
def csrf(request):
    """Sets the csrftoken cookie. The frontend calls this once before its first POST."""
    return JsonResponse({"detail": "CSRF cookie set."})


@method_decorator(csrf_protect, name="dispatch")
class SignupView(APIView):
    """Creates a site-manager account and signs the user in."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = authenticate(request, username=data["email"].strip().lower(), password=data["password"])
        if user is None:
            return Response(
                {"code": "invalid_credentials", "detail": "Email or password is incorrect."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        login(request, user)
        return Response(UserSerializer(user).data)


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(csrf_protect, name="dispatch")
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        """Let any authenticated user update their own profile fields."""
        allowed = ["full_name", "phone", "designation", "avatar_url"]
        data = {k: v for k, v in request.data.items() if k in allowed}
        serializer = AdminUpdateUserSerializer(request.user, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        request.user.refresh_from_db()
        return Response(UserSerializer(request.user).data)


# ------------------------------------------------------------------ #
# User management (ADMIN / SUPER_ADMIN only)                          #
# ------------------------------------------------------------------ #

@method_decorator(csrf_protect, name="dispatch")
class UsersView(APIView):
    """
    GET  /api/accounts/users/  â€” list all users (admin/super-admin)
    POST /api/accounts/users/  â€” create a user with any role (admin/super-admin)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_admin_or_above(request.user):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        users = User.objects.all().order_by("full_name", "email")
        return Response(UserSerializer(users, many=True).data)

    def post(self, request):
        if not _is_admin_or_above(request.user):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        serializer = AdminCreateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data.get("role", Role.SITE_MANAGER)
        # Only a super-admin can create another admin or super-admin
        if role in (Role.ADMIN, Role.SUPER_ADMIN) and not _is_super_admin(request.user):
            return Response({"detail": "Only a Super Admin can create Admin accounts."}, status=status.HTTP_403_FORBIDDEN)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_protect, name="dispatch")
class UserDetailView(APIView):
    """
    GET   /api/accounts/users/{id}/  â€” get one user
    PATCH /api/accounts/users/{id}/  â€” update profile / role / status
    """

    permission_classes = [IsAuthenticated]

    def _get_user(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    def get(self, request, pk):
        if not _is_admin_or_above(request.user):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        user = self._get_user(pk)
        if not user:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(UserSerializer(user).data)

    def patch(self, request, pk):
        if not _is_admin_or_above(request.user):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        user = self._get_user(pk)
        if not user:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        # Admins cannot modify other admins or super-admins (only super-admin can)
        if user.role in (Role.ADMIN, Role.SUPER_ADMIN) and not _is_super_admin(request.user):
            return Response({"detail": "Only a Super Admin can modify Admin accounts."}, status=status.HTTP_403_FORBIDDEN)
        new_role = request.data.get("role")
        if new_role in (Role.ADMIN, Role.SUPER_ADMIN) and not _is_super_admin(request.user):
            return Response({"detail": "Only a Super Admin can assign the Admin role."}, status=status.HTTP_403_FORBIDDEN)
        serializer = AdminUpdateUserSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        user.refresh_from_db()
        return Response(UserSerializer(user).data)

