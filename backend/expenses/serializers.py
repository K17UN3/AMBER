from rest_framework import serializers

from .models import Category, Expense


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]
        read_only_fields = ["id", "name"]


class ExpenseSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    ocr_job_id = serializers.UUIDField(write_only=True, required=False)
    category = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Category.objects.all(),
    )

    class Meta:
        model = Expense
        fields = [
            "id",
            "user",
            "shop_name",
            "total_amount",
            "purchased_at",
            "category",
            "image",
            "raw_ocr_text",
            "ocr_job_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data.pop("ocr_job_id", None)
        return super().create(validated_data)
