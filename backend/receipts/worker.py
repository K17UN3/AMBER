import os
import shutil
import tempfile
from datetime import timedelta
from pathlib import Path

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from expenses.services import classify_category

from .models import OCRJob
from .services import OCRProcessingError, analyze_receipt


MAX_OCR_ATTEMPTS = 3
OCR_JOB_LEASE = timedelta(minutes=5)


def process_next_ocr_job():
    now = timezone.now()
    _recover_stale_jobs(now)

    with transaction.atomic():
        job = (
            OCRJob.objects.filter(status=OCRJob.Status.PENDING, attempt_count__lt=MAX_OCR_ATTEMPTS)
            .order_by("created_at")
            .first()
        )
        if job is None:
            return False
        claimed = OCRJob.objects.filter(pk=job.pk, status=OCRJob.Status.PENDING).update(
            status=OCRJob.Status.PROCESSING,
            started_at=now,
            attempt_count=F("attempt_count") + 1,
        )

    if not claimed:
        return False

    job.refresh_from_db()
    temporary_path = None
    try:
        temporary_path = _download_image_to_temporary_file(job)
        result = analyze_receipt(temporary_path)
        category = classify_category(
            result["shop_name"] or "",
            result["raw_ocr_text"],
        )
    except Exception as error:
        _mark_job_failed(job, error)
        return True
    finally:
        if temporary_path:
            try:
                os.unlink(temporary_path)
            except OSError:
                pass

    job.status = OCRJob.Status.SUCCEEDED
    job.raw_ocr_text = result["raw_ocr_text"]
    job.ocr_lines = result["ocr_lines"]
    job.shop_name = result["shop_name"] or ""
    job.purchased_at = result["purchased_at"] or None
    job.total_amount = result["total_amount"]
    job.category = category
    job.completed_at = timezone.now()
    job.save(
        update_fields=[
            "status",
            "raw_ocr_text",
            "ocr_lines",
            "shop_name",
            "purchased_at",
            "total_amount",
            "category",
            "completed_at",
        ]
    )
    return True


def _recover_stale_jobs(now):
    stale_jobs = OCRJob.objects.filter(status=OCRJob.Status.PROCESSING).filter(
        Q(started_at__isnull=True) | Q(started_at__lt=now - OCR_JOB_LEASE)
    )
    stale_jobs.filter(attempt_count__gte=MAX_OCR_ATTEMPTS).update(
        status=OCRJob.Status.FAILED,
        error_message="OCR解析がタイムアウトしました。もう一度お試しください。",
        completed_at=now,
    )
    stale_jobs.filter(attempt_count__lt=MAX_OCR_ATTEMPTS).update(
        status=OCRJob.Status.PENDING,
        started_at=None,
    )


def _download_image_to_temporary_file(job):
    suffix = Path(job.original_filename).suffix or ".jpg"
    temporary_path = None
    try:
        with job.image.open("rb") as source, tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary_file:
            temporary_path = temporary_file.name
            shutil.copyfileobj(source, temporary_file)
        return temporary_path
    except Exception:
        if temporary_path:
            try:
                os.unlink(temporary_path)
            except OSError:
                pass
        raise


def _mark_job_failed(job, error):
    message = str(error) if isinstance(error, OCRProcessingError) else "OCR解析に失敗しました。もう一度お試しください。"
    job.status = OCRJob.Status.FAILED
    job.error_message = message
    job.completed_at = timezone.now()
    job.save(update_fields=["status", "error_message", "completed_at"])
