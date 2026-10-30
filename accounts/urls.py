from django.urls import path

from . import views

urlpatterns = [
    # Auth
    path("auth/csrf/", views.csrf, name="auth-csrf"),
    path("auth/signup/", views.SignupView.as_view(), name="auth-signup"),
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", views.MeView.as_view(), name="auth-me"),
    # User management (ADMIN / SUPER_ADMIN)
    path("accounts/users/", views.UsersView.as_view(), name="accounts-users"),
    path("accounts/users/<int:pk>/", views.UserDetailView.as_view(), name="accounts-user-detail"),
]
