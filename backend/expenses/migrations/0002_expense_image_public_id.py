from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="expense",
            name="image_public_id",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
