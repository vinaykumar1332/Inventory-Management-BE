from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Role
from .models import ApprovalRequest, ApprovalStatus
from .serializers import (
    ApprovalRequestSerializer,
    CreateApprovalSerializer,
    ReviewApprovalSerializer,
)


def _can_review(user) -> bool:
    return user.role in (Role.SUPER_ADMIN, Role.ADMIN)


@method_decorator(csrf_protect, name="dispatch")
class ApprovalsView(APIView):
    """
    GET  /api/approvals/           — list pending approvals waiting for me (admin+)
                                     or my own submissions (?mine=1)
    POST /api/approvals/           — submit a new approval request
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        mine = request.query_params.get("mine") == "1"
        if mine:
            qs = ApprovalRequest.objects.filter(submitted_by=request.user)
        elif _can_review(request.user):
            qs = ApprovalRequest.objects.filter(status=ApprovalStatus.PENDING).exclude(submitted_by=request.user)
        else:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        history = request.query_params.get("history") == "1"
        if not history:
            qs = qs.filter(status=ApprovalStatus.PENDING)

        qs = qs.select_related("submitted_by", "reviewed_by").order_by("-created_at")
        return Response(ApprovalRequestSerializer(qs, many=True).data)

    def post(self, request):
        serializer = CreateApprovalSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response(ApprovalRequestSerializer(obj).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_protect, name="dispatch")
class ApprovalDetailView(APIView):
    """
    GET   /api/approvals/{id}/         — get one request
    POST  /api/approvals/{id}/review/  — approve or reject (admin+)
    """

    permission_classes = [IsAuthenticated]

    def _get(self, pk):
        try:
            return ApprovalRequest.objects.select_related("submitted_by", "reviewed_by").get(pk=pk)
        except ApprovalRequest.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if obj.submitted_by != request.user and not _can_review(request.user):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        return Response(ApprovalRequestSerializer(obj).data)


@method_decorator(csrf_protect, name="dispatch")
class ApprovalReviewView(APIView):
    """POST /api/approvals/{id}/review/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _can_review(request.user):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        try:
            obj = ApprovalRequest.objects.get(pk=pk)
        except ApprovalRequest.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if obj.status != ApprovalStatus.PENDING:
            return Response({"detail": "This request has already been reviewed."}, status=status.HTTP_400_BAD_REQUEST)

        if obj.submitted_by == request.user:
            return Response({"detail": "You cannot review your own submission."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ReviewApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        obj.status = ApprovalStatus.APPROVED if data["action"] == "approve" else ApprovalStatus.REJECTED
        obj.reviewed_by = request.user
        obj.reviewer_note = data.get("reviewer_note", "")
        obj.reviewed_at = timezone.now()
        obj.save()

        return Response(ApprovalRequestSerializer(obj).data)
