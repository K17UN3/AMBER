from django.db import transaction
from django.utils import timezone

from .models import OCRJob
from .services import OCRProcessingError, analyze_receipt


def process_next_ocr_job():
    with transaction.atomic():
        job = OCRJob.objects.filter(status=OCRJob.Status.PENDING).order_by("created_at").first()
        if job is None:
            return False
        claimed = OCRJob.objects.filter(pk=job.pk, status=OCRJob.Status.PENDING).update(
            status=OCRJob.Status.PROCESSING,
            started_at=timezone.now(),
        )

    if not claimed:
        return False

    job.refresh_from_db()
    try:
        result = analyze_receipt(job.image.path)
    except OCRProcessingError as error:
        job.status = OCRJob.Status.FAILED
        job.error_message = str(error)
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "error_message", "completed_at"])
        return True

    job.status = OCRJob.Status.SUCCEEDED
    job.raw_ocr_text = result["raw_ocr_text"]
    job.ocr_lines = result["ocr_lines"]
    job.shop_name = result["shop_name"] or ""
    job.purchased_at = result["purchased_at"] or None
    job.total_amount = result["total_amount"]
    job.completed_at = timezone.now()
    job.save(
        update_fields=[
            "status",
            "raw_ocr_text",
            "ocr_lines",
            "shop_name",
            "purchased_at",
            "total_amount",
            "completed_at",
        ]
    )
    return True
