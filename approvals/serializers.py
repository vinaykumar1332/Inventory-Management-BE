from rest_framework import serializers

from .models import ApprovalRequest, ApprovalStatus


class SubmitterSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    role = serializers.CharField()


class ApprovalRequestSerializer(serializers.ModelSerializer):
    submitted_by = SubmitterSerializer(read_only=True)
    reviewed_by = SubmitterSerializer(read_only=True)

    class Meta:
        model = ApprovalRequest
        fields = [
            "id", "type", "status",
            "site_id", "site_name",
            "title", "details",
            "submitted_by", "reviewed_by", "reviewer_note",
            "created_at", "reviewed_at",
        ]
        read_only_fields = fields


class CreateApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalRequest
        fields = ["type", "site_id", "site_name", "title", "details"]

    def create(self, validated_data):
        validated_data["submitted_by"] = self.context["request"].user
        return super().create(validated_data)


class ReviewApprovalSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    reviewer_note = serializers.CharField(allow_blank=True, default="")
