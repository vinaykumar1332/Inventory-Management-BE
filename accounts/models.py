from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class Role(models.TextChoices):
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
    ADMIN = "ADMIN", "Admin"
    STOREKEEPER = "STOREKEEPER", "Storekeeper"
    SITE_MANAGER = "SITE_MANAGER", "Site Manager"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email, full_name, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        if not full_name:
            raise ValueError("Users must have a full name.")
        user = self.model(email=self.normalize_email(email).lower(), full_name=full_name.strip(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, full_name, password=None, role=Role.SITE_MANAGER, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create(email, full_name, password, role=role, **extra_fields)

    def create_superuser(self, email, full_name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True or extra_fields.get("is_superuser") is not True:
            raise ValueError("Superusers must have is_staff=True and is_superuser=True.")
        extra_fields["role"] = Role.SUPER_ADMIN
        return self._create(email, full_name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Account used to sign in. Email is the login field."""

    email = models.EmailField("email address", unique=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SITE_MANAGER)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(
        default=False,
        help_text="Designates whether the user can log in to the Django admin site.",
    )
    # Profile fields — populated by admins after account creation
    phone = models.CharField(max_length=30, blank=True, default="")
    employee_id = models.CharField(max_length=50, blank=True, default="")
    designation = models.CharField(max_length=100, blank=True, default="")
    first_login_completed = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    avatar_url = models.URLField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        ordering = ["full_name", "email"]
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name.split(" ")[0]
