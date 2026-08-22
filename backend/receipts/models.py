from django.db import models


class OCRCorrectionHistory(models.Model):
    expense = models.OneToOneField(
        "expenses.Expense",
        on_delete=models.CASCADE,
        related_name="ocr_correction_history",
    )
    ocr_values = models.JSONField(default=dict)
    saved_values = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
