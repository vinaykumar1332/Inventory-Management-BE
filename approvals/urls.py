from django.urls import path

from . import views

urlpatterns = [
    path("approvals/", views.ApprovalsView.as_view(), name="approvals-list"),
    path("approvals/<int:pk>/", views.ApprovalDetailView.as_view(), name="approvals-detail"),
    path("approvals/<int:pk>/review/", views.ApprovalReviewView.as_view(), name="approvals-review"),
]
