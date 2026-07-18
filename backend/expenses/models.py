from django.conf import settings
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    keywords = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class Expense(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="expenses")
    shop_name = models.CharField(max_length=255, blank=True)
    total_amount = models.PositiveIntegerField()
    purchased_at = models.DateField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="expenses")
    image = models.URLField(blank=True)
    raw_ocr_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-purchased_at", "-created_at"]

    def __str__(self):
        return f"{self.purchased_at} {self.shop_name or '未入力'} {self.total_amount}円"
