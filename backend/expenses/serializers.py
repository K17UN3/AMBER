from rest_framework import serializers

from .image_storage import signed_receipt_image_url
from .models import Category, Expense


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]
        read_only_fields = ["id", "name"]


class CategoryClassificationInputSerializer(serializers.Serializer):
    shop_name = serializers.CharField(max_length=255, allow_blank=True, required=False)
    raw_ocr_text = serializers.CharField(allow_blank=True, required=False)


class ClientOCRResultSerializer(serializers.Serializer):
    shop_name = serializers.CharField(max_length=255, allow_blank=True, allow_null=True)
    purchased_at = serializers.DateField(allow_null=True)
    total_amount = serializers.IntegerField(min_value=0, allow_null=True)
    raw_ocr_text = serializers.CharField(allow_blank=True)
    confidence = serializers.FloatField(min_value=0, max_value=100)
    engine = serializers.ChoiceField(choices=["tesseract.js"])
    category = serializers.CharField(max_length=50, required=False)

    def validate_category(self, value):
        if not Category.objects.filter(name=value).exists():
            raise serializers.ValidationError("存在するカテゴリーを指定してください。")
        return value


class ExpenseSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    image = serializers.SerializerMethodField()
    ocr_result = ClientOCRResultSerializer(write_only=True, required=False)
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
            "ocr_result",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data.pop("ocr_result", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("ocr_result", None)
        return super().update(instance, validated_data)

    def get_image(self, expense):
        if expense.image_public_id:
            return signed_receipt_image_url(expense.image_public_id, expense.image_format)
        return expense.image
