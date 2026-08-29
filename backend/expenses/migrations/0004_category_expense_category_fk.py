import django.db.models.deletion
from django.db import migrations, models


INITIAL_CATEGORIES = [
    ("食費", "スーパー\n食品\n弁当\nパン\n牛乳\nコンビニ"),
    ("日用品", "薬局\n洗剤\nティッシュ\nドラッグストア"),
    ("交通費", "電車\nバス\n交通\nIC"),
    ("その他", ""),
]


def seed_categories_and_migrate_expenses(apps, schema_editor):
    Category = apps.get_model("expenses", "Category")
    Expense = apps.get_model("expenses", "Expense")

    categories = {}
    for name, keywords in INITIAL_CATEGORIES:
        category, _ = Category.objects.get_or_create(
            name=name,
            defaults={"keywords": keywords},
        )
        categories[name] = category

    other = categories["その他"]
    for expense in Expense.objects.all().iterator():
        expense.category_ref = categories.get(expense.category, other)
        expense.save(update_fields=["category_ref"])


class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0003_expense_image_format"),
    ]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=50, unique=True)),
                ("keywords", models.TextField(blank=True)),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.AddField(
            model_name="expense",
            name="category_ref",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="expenses",
                to="expenses.category",
            ),
        ),
        migrations.RunPython(seed_categories_and_migrate_expenses, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="expense",
            name="category",
        ),
        migrations.RenameField(
            model_name="expense",
            old_name="category_ref",
            new_name="category",
        ),
        migrations.AlterField(
            model_name="expense",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="expenses",
                to="expenses.category",
            ),
        ),
    ]
