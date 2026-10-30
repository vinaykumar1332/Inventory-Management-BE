from django.conf import settings
from django.db import models


class ApprovalType(models.TextChoices):
    SITE_MANAGER_CHANGE = "SITE_MANAGER_CHANGE", "Site Manager Change"
    STOCK_ADJUSTMENT = "STOCK_ADJUSTMENT", "Stock Adjustment"
    MATERIAL_ISSUE = "MATERIAL_ISSUE", "Material Issue"


class ApprovalStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class ApprovalRequest(models.Model):
    """A change that requires a second person to approve before it takes effect."""

    type = models.CharField(max_length=30, choices=ApprovalType.choices)
    status = models.CharField(max_length=10, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING)

    # Where this happened
    site_id = models.IntegerField(null=True, blank=True)
    site_name = models.CharField(max_length=200, blank=True, default="")

    # Human-readable summary lines shown in the list cards
    title = models.CharField(max_length=200)
    details = models.JSONField(default=dict, blank=True)

    # Who submitted and who reviewed
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="submitted_approvals",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_approvals",
    )
    reviewer_note = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.type}] {self.title} ({self.status})"
