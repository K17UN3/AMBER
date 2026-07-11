from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import OCRJob
from .worker import process_next_ocr_job

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
