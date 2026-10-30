from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import User


class UserAdminCreationForm(UserCreationForm):
    """Creates users keyed by email. Django's default form expects a username field."""

    class Meta:
        model = User
        fields = ("email", "full_name", "role")


class UserAdminChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"
