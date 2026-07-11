import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

import receipts.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("expenses", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="OCRJob",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("image", models.FileField(upload_to=receipts.models.receipt_upload_path)),
                ("original_filename", models.CharField(max_length=255)),
                ("content_type", models.CharField(max_length=100)),
                ("file_size", models.PositiveIntegerField()),
                ("status", models.CharField(choices=[("pending", "待機中"), ("processing", "解析中"), ("succeeded", "成功"), ("failed", "失敗")], default="pending", max_length=20)),
                ("attempt_count", models.PositiveIntegerField(default=0)),
                ("shop_name", models.CharField(blank=True, max_length=255)),
                ("purchased_at", models.DateField(blank=True, null=True)),
                ("total_amount", models.PositiveIntegerField(blank=True, null=True)),
                ("raw_ocr_text", models.TextField(blank=True)),
                ("ocr_lines", models.JSONField(blank=True, default=list)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ocr_jobs", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="OCRCorrectionHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ocr_values", models.JSONField(default=dict)),
                ("saved_values", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expense", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="expenses.expense")),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="correction_histories", to="receipts.ocrjob")),
            ],
        ),
        migrations.AddIndex(
            model_name="ocrjob",
            index=models.Index(fields=["status", "created_at"], name="receipts_oc_status_8eb6e0_idx"),
        ),
    ]
