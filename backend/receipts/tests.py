from datetime import timedelta
from io import BytesIO
import os

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import OCRJob
from .services import extract_shop_name, extract_total_amount
from .storage import CloudinaryReceiptStorage
from .worker import _download_image_to_temporary_file, process_next_ocr_job

User = get_user_model()


class ReceiptAnalyzeApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="StrongPass123",
        )

    def test_analyze_requires_login(self):
        response = self.client.post(reverse("receipt-analyze"))

        self.assertEqual(response.status_code, 403)

    def test_analyze_creates_pending_job_without_saving_expense(self):
        self.client.force_authenticate(self.user)
        image = SimpleUploadedFile(
            "receipt.jpg",
            b"fake image bytes",
            content_type="image/jpeg",
        )

        response = self.client.post(reverse("receipt-analyze"), {"image": image}, format="multipart")

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], OCRJob.Status.PENDING)
        self.assertEqual(response.data["image"]["name"], "receipt.jpg")
        self.assertEqual(response.data["image"]["content_type"], "image/jpeg")
        self.assertEqual(OCRJob.objects.count(), 1)

    def test_job_status_is_only_available_to_its_owner(self):
        self.client.force_authenticate(self.user)
        job = OCRJob.objects.create(
            user=self.user,
            image=SimpleUploadedFile("receipt.jpg", b"image", content_type="image/jpeg"),
            original_filename="receipt.jpg",
            content_type="image/jpeg",
            file_size=5,
        )
        response = self.client.get(reverse("ocr-job-detail", kwargs={"job_id": job.id}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(job.id))

        other_user = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="StrongPass123",
        )
        self.client.force_authenticate(other_user)
        response = self.client.get(reverse("ocr-job-detail", kwargs={"job_id": job.id}))
        self.assertEqual(response.status_code, 404)

    def test_worker_persists_text_coordinates_and_extracted_values(self):
        job = OCRJob.objects.create(
            user=self.user,
            image=SimpleUploadedFile("receipt.jpg", b"image", content_type="image/jpeg"),
            original_filename="receipt.jpg",
            content_type="image/jpeg",
            file_size=5,
        )
        expected = {
            "raw_ocr_text": "アンバーマート\n2026/07/11\n合計 1,280",
            "ocr_lines": [{"text": "アンバーマート", "confidence": 0.99, "coordinates": [[0, 0], [1, 1]]}],
            "shop_name": "アンバーマート",
            "purchased_at": "2026-07-11",
            "total_amount": 1280,
        }

        with self.settings():
            from unittest.mock import patch

            with patch("receipts.worker.analyze_receipt", return_value=expected):
                self.assertTrue(process_next_ocr_job())

        job.refresh_from_db()
        self.assertEqual(job.status, OCRJob.Status.SUCCEEDED)
        self.assertEqual(job.shop_name, "アンバーマート")
        self.assertEqual(job.purchased_at.isoformat(), "2026-07-11")
        self.assertEqual(job.total_amount, 1280)
        self.assertEqual(job.ocr_lines, expected["ocr_lines"])
        self.assertEqual(job.attempt_count, 1)

    def test_worker_recovers_a_stale_job_within_retry_limit(self):
        job = OCRJob.objects.create(
            user=self.user,
            image=SimpleUploadedFile("receipt.jpg", b"image", content_type="image/jpeg"),
            original_filename="receipt.jpg",
            content_type="image/jpeg",
            file_size=5,
            status=OCRJob.Status.PROCESSING,
            started_at=timezone.now() - timedelta(minutes=6),
            attempt_count=1,
        )
        expected = {
            "raw_ocr_text": "",
            "ocr_lines": [],
            "shop_name": None,
            "purchased_at": None,
            "total_amount": None,
        }

        from unittest.mock import patch

        with patch("receipts.worker.analyze_receipt", return_value=expected):
            self.assertTrue(process_next_ocr_job())

        job.refresh_from_db()
        self.assertEqual(job.status, OCRJob.Status.SUCCEEDED)
        self.assertEqual(job.attempt_count, 2)

    def test_worker_fails_a_stale_job_after_maximum_attempts(self):
        job = OCRJob.objects.create(
            user=self.user,
            image=SimpleUploadedFile("receipt.jpg", b"image", content_type="image/jpeg"),
            original_filename="receipt.jpg",
            content_type="image/jpeg",
            file_size=5,
            status=OCRJob.Status.PROCESSING,
            started_at=timezone.now() - timedelta(minutes=6),
            attempt_count=3,
        )

        self.assertFalse(process_next_ocr_job())

        job.refresh_from_db()
        self.assertEqual(job.status, OCRJob.Status.FAILED)
        self.assertIn("タイムアウト", job.error_message)

    def test_worker_marks_unexpected_storage_errors_as_failed(self):
        job = OCRJob.objects.create(
            user=self.user,
            image=SimpleUploadedFile("receipt.jpg", b"image", content_type="image/jpeg"),
            original_filename="receipt.jpg",
            content_type="image/jpeg",
            file_size=5,
        )

        from unittest.mock import patch

        with patch("receipts.worker._download_image_to_temporary_file", side_effect=NotImplementedError):
            self.assertTrue(process_next_ocr_job())

        job.refresh_from_db()
        self.assertEqual(job.status, OCRJob.Status.FAILED)

    def test_temporary_file_is_removed_when_download_copy_fails(self):
        job = OCRJob.objects.create(
            user=self.user,
            image=SimpleUploadedFile("receipt.jpg", b"image", content_type="image/jpeg"),
            original_filename="receipt.jpg",
            content_type="image/jpeg",
            file_size=5,
        )

        from unittest.mock import patch

        with patch("receipts.worker.shutil.copyfileobj", side_effect=OSError("copy failed")):
            with patch("receipts.worker.os.unlink", wraps=os.unlink) as unlink:
                with self.assertRaises(OSError):
                    _download_image_to_temporary_file(job)

        self.assertTrue(any(str(call.args[0]).endswith(".jpg") for call in unlink.call_args_list))

    def test_analyze_rejects_missing_image(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("receipt-analyze"), {}, format="multipart")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "レシート画像を選択してください。")

    def test_analyze_rejects_non_image_upload(self):
        self.client.force_authenticate(self.user)
        text_file = SimpleUploadedFile(
            "receipt.txt",
            b"not an image",
            content_type="text/plain",
        )

        response = self.client.post(reverse("receipt-analyze"), {"image": text_file}, format="multipart")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "画像ファイルを選択してください。")


class ReceiptParsingTests(SimpleTestCase):
    def test_extract_total_amount_supports_comma_and_plain_integer_amounts(self):
        self.assertEqual(extract_total_amount("合計 1280"), 1280)
        self.assertEqual(extract_total_amount("合 計 ¥3,245"), 3245)
        self.assertEqual(extract_total_amount("合計 1,280"), 1280)
        self.assertEqual(extract_total_amount("合計 980"), 980)

    def test_extract_total_amount_handles_split_and_full_width_ocr_lines(self):
        self.assertEqual(extract_total_amount("３．２４5\n預／現計\n4点"), 3245)

    def test_extract_shop_name_prefers_confident_non_address_line(self):
        lines = [
            {"text": "ＭＡＲUてＡＭＡ", "confidence": 0.71},
            {"text": "La Fraise", "confidence": 0.99},
            {"text": "札幌市中央区南1条西2丁目", "confidence": 1.0},
            {"text": "1,400外", "confidence": 1.0},
        ]

        self.assertEqual(extract_shop_name(lines), "La Fraise")


class CloudinaryReceiptStorageTests(SimpleTestCase):
    def setUp(self):
        self.storage = CloudinaryReceiptStorage()

    def test_uploads_receipt_as_authenticated_asset(self):
        from unittest.mock import patch

        with patch(
            "receipts.storage.cloudinary.uploader.upload",
            return_value={"public_id": "amber/receipts/asset-id", "format": "jpg"},
        ) as upload:
            saved_name = self.storage._save("receipts/original.jpg", BytesIO(b"receipt"))

        self.assertEqual(saved_name, "amber/receipts/asset-id.jpg")
        self.assertEqual(upload.call_args.kwargs["type"], "authenticated")
        self.assertFalse(upload.call_args.kwargs["overwrite"])

    def test_open_uses_short_lived_authenticated_download_url(self):
        from unittest.mock import patch

        with patch(
            "receipts.storage.cloudinary.utils.private_download_url",
            return_value="https://api.cloudinary.example/private",
        ) as private_url:
            with patch("receipts.storage.urlopen", return_value=BytesIO(b"receipt bytes")):
                opened = self.storage._open("amber/receipts/asset-id.jpg")

        self.assertEqual(opened.read(), b"receipt bytes")
        self.assertEqual(private_url.call_args.args[:2], ("amber/receipts/asset-id", "jpg"))
        self.assertEqual(private_url.call_args.kwargs["type"], "authenticated")
