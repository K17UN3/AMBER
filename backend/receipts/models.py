import uuid

from django.conf import settings
from django.db import models


def receipt_upload_path(instance, filename):
    return f"receipts/{instance.user_id}/{instance.id or uuid.uuid4()}/{filename}"


class OCRJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待機中"
        PROCESSING = "processing", "解析中"
        SUCCEEDED = "succeeded", "成功"
        FAILED = "failed", "失敗"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ocr_jobs")
    image = models.FileField(upload_to=receipt_upload_path)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    file_size = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    attempt_count = models.PositiveIntegerField(default=0)
    shop_name = models.CharField(max_length=255, blank=True)
    purchased_at = models.DateField(null=True, blank=True)
    total_amount = models.PositiveIntegerField(null=True, blank=True)
    raw_ocr_text = models.TextField(blank=True)
    ocr_lines = models.JSONField(default=list, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["status", "created_at"], name="receipts_oc_status_8eb6e0_idx")]


class OCRCorrectionHistory(models.Model):
    job = models.ForeignKey(OCRJob, on_delete=models.CASCADE, related_name="correction_histories")
    expense = models.ForeignKey("expenses.Expense", on_delete=models.SET_NULL, null=True, blank=True)
    ocr_values = models.JSONField(default=dict)
    saved_values = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
