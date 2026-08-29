from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0002_expense_image_public_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="expense",
            name="image_format",
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
