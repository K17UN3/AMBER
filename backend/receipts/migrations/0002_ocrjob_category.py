import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0002_category_expense_category_fk"),
        ("receipts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="ocrjob",
            name="category",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="ocr_jobs",
                to="expenses.category",
            ),
        ),
    ]
