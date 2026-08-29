from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("expenses", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="OCRCorrectionHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ocr_values", models.JSONField(default=dict)),
                ("saved_values", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expense", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="ocr_correction_history", to="expenses.expense")),
            ],
        ),
    ]
