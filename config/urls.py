from django.contrib import admin
from django.urls import include, path

from config.views import health

# API prefixes:
#   /api/auth/…        authentication (login, signup, logout, me, csrf)
#   /api/accounts/…    user management (list, create, patch)
#   /api/approvals/    approval requests
#   /api/sites/        sites (future)
#   /api/products/     products (future)
#   /api/inventory/    inventory (future)
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="api-health"),
    path("api/", include("accounts.urls")),
    path("api/", include("approvals.urls")),
]
