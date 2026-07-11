from rest_framework import serializers

from .models import OCRJob


class OCRJobSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = OCRJob
        fields = [
            "id",
            "status",
            "shop_name",
            "purchased_at",
            "total_amount",
            "raw_ocr_text",
            "ocr_lines",
            "error_message",
            "image",
            "created_at",
            "started_at",
            "completed_at",
        ]

    def get_image(self, job):
        return {
            "name": job.original_filename,
            "size": job.file_size,
            "content_type": job.content_type,
        }
