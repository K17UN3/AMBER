from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from .image_storage import (
    ImageStorageError,
    StoredReceiptImage,
    delete_receipt_image,
    signed_receipt_image_url,
    upload_receipt_image,
)
from .models import Expense
from receipts.models import OCRCorrectionHistory


User = get_user_model()


@override_settings(CLOUDINARY_URL="cloudinary://key:secret@example")
class ReceiptImageStorageTests(SimpleTestCase):
    @patch("expenses.image_storage.cloudinary.uploader.upload")
    def test_upload_uses_authenticated_delivery(self, upload_mock):
        upload_mock.return_value = {
            "secure_url": "https://res.cloudinary.com/example/image/authenticated/new.jpg",
            "public_id": "amber/receipts/1/new",
            "format": "jpg",
        }
        image = SimpleUploadedFile("receipt.jpg", b"image-bytes", content_type="image/jpeg")

        stored_image = upload_receipt_image(image, user_id=1)

        self.assertEqual(stored_image.format, "jpg")
        self.assertEqual(upload_mock.call_args.kwargs["type"], "authenticated")

    @patch("expenses.image_storage.time", return_value=1000)
    @patch("expenses.image_storage.private_download_url", return_value="https://signed.example/receipt")
    def test_signed_url_is_short_lived_and_authenticated(self, download_url_mock, _time_mock):
        url = signed_receipt_image_url("amber/receipts/1/new", "jpg")

        self.assertEqual(url, "https://signed.example/receipt")
        download_url_mock.assert_called_once_with(
            "amber/receipts/1/new",
            "jpg",
            resource_type="image",
            type="authenticated",
            expires_at=1300,
            attachment=False,
        )

    @patch("expenses.image_storage.cloudinary.uploader.destroy")
    def test_delete_targets_authenticated_asset(self, destroy_mock):
        delete_receipt_image("amber/receipts/1/new")

        destroy_mock.assert_called_once_with(
            "amber/receipts/1/new",
            resource_type="image",
            type="authenticated",
            invalidate=True,
        )


class ExpenseApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="StrongPass123",
        )
        self.other_user = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="StrongPass123",
        )
        self.payload = {
            "shop_name": "アンバーマート",
            "purchased_at": "2026-06-13",
            "total_amount": 1280,
            "category": "食費",
            "raw_ocr_text": "アンバーマート\n合計 1280",
        }

    def test_monthly_summary_returns_only_current_user_totals(self):
        Expense.objects.create(user=self.user, purchased_at="2026-06-05", total_amount=2500, category="食費")
        Expense.objects.create(user=self.user, purchased_at="2026-06-10", total_amount=1800, category="日用品")
        Expense.objects.create(user=self.user, purchased_at="2026-06-12", total_amount=4200, category="食費")
        Expense.objects.create(user=self.other_user, purchased_at="2026-06-07", total_amount=9999, category="その他")

        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("monthly-summary"), {"year": 2026, "month": 6})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["year"], 2026)
        self.assertEqual(response.data["month"], 6)
        self.assertEqual(response.data["grand_total"], 8500)
        self.assertEqual(
            response.data["categories"],
            [
                {"category": "日用品", "total": 1800},
                {"category": "食費", "total": 6700},
            ],
        )

    def test_expense_create_requires_login(self):
        response = self.client.post(reverse("expense-list"), self.payload, format="json")

        self.assertEqual(response.status_code, 403)

    def test_expense_create_assigns_current_user(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("expense-list"), self.payload, format="json")

        self.assertEqual(response.status_code, 201)
        expense = Expense.objects.get()
        self.assertEqual(expense.user, self.user)
        self.assertEqual(response.data["user"], self.user.id)
        self.assertEqual(response.data["shop_name"], "アンバーマート")

    def test_expense_create_records_ocr_correction_history(self):
        self.client.force_authenticate(self.user)
        ocr_result = {
            "shop_name": "OCR店名",
            "purchased_at": "2026-06-13",
            "total_amount": 1200,
            "raw_ocr_text": "OCR店名\n合計 1200",
            "confidence": 91.5,
            "engine": "tesseract.js",
        }

        response = self.client.post(
            reverse("expense-list"),
            {**self.payload, "ocr_result": ocr_result, "shop_name": "修正後の店名"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        history = OCRCorrectionHistory.objects.get()
        self.assertEqual(history.expense_id, response.data["id"])
        self.assertEqual(history.ocr_values["shop_name"], "OCR店名")
        self.assertEqual(history.ocr_values["engine"], "tesseract.js")
        self.assertEqual(history.saved_values["shop_name"], "修正後の店名")
        self.assertNotIn("ocr_result", response.data)

    def test_expense_create_rolls_back_when_history_creation_fails(self):
        self.client.force_authenticate(self.user)
        ocr_result = {
            "shop_name": None,
            "purchased_at": None,
            "total_amount": None,
            "raw_ocr_text": "",
            "confidence": 0,
            "engine": "tesseract.js",
        }

        with patch("expenses.views.OCRCorrectionHistory.objects.create", side_effect=RuntimeError("history failed")):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    reverse("expense-list"),
                    {**self.payload, "ocr_result": ocr_result},
                    format="json",
                )

        self.assertEqual(Expense.objects.count(), 0)

    def test_expense_create_rejects_unknown_ocr_engine(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            reverse("expense-list"),
            {
                **self.payload,
                "ocr_result": {
                    "shop_name": None,
                    "purchased_at": None,
                    "total_amount": None,
                    "raw_ocr_text": "",
                    "confidence": 0,
                    "engine": "unknown",
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("engine", response.data["ocr_result"])

    def test_expense_create_validates_required_fields(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("expense-list"), {"shop_name": "アンバー"}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("purchased_at", response.data)
        self.assertIn("total_amount", response.data)
        self.assertIn("category", response.data)

    def test_expense_list_returns_only_current_user_records(self):
        Expense.objects.create(user=self.user, **self.payload)
        Expense.objects.create(
            user=self.other_user,
            shop_name="別ユーザー店",
            purchased_at="2026-06-13",
            total_amount=999,
            category="その他",
        )
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("expense-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["shop_name"], "アンバーマート")

    def test_expense_put_updates_current_user_record(self):
        expense = Expense.objects.create(
            user=self.user,
            image="https://res.cloudinary.com/demo/image/upload/old.jpg",
            image_public_id="amber/receipts/1/old",
            **self.payload,
        )
        self.client.force_authenticate(self.user)
        updated_payload = {
            **self.payload,
            "shop_name": "更新後マート",
            "total_amount": 1500,
            "category": "日用品",
        }

        response = self.client.put(
            reverse("expense-detail", args=[expense.id]),
            updated_payload,
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        expense.refresh_from_db()
        self.assertEqual(expense.shop_name, "更新後マート")
        self.assertEqual(expense.total_amount, 1500)
        self.assertEqual(expense.category, "日用品")
        self.assertEqual(expense.image_public_id, "amber/receipts/1/old")
        self.assertNotIn("image_public_id", response.data)

    def test_expense_put_validates_required_fields(self):
        expense = Expense.objects.create(user=self.user, **self.payload)
        self.client.force_authenticate(self.user)

        response = self.client.put(
            reverse("expense-detail", args=[expense.id]),
            {"shop_name": "更新後マート"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("purchased_at", response.data)
        self.assertIn("total_amount", response.data)
        self.assertIn("category", response.data)

    def test_expense_patch_updates_only_supplied_fields(self):
        expense = Expense.objects.create(user=self.user, **self.payload)
        self.client.force_authenticate(self.user)

        response = self.client.patch(
            reverse("expense-detail", args=[expense.id]),
            {"shop_name": "一部更新"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        expense.refresh_from_db()
        self.assertEqual(expense.shop_name, "一部更新")
        self.assertEqual(expense.total_amount, 1280)
        self.assertEqual(expense.category, "食費")

    def test_other_users_expense_cannot_be_viewed_updated_or_deleted(self):
        expense = Expense.objects.create(user=self.other_user, **self.payload)
        self.client.force_authenticate(self.user)

        detail_response = self.client.get(reverse("expense-detail", args=[expense.id]))
        update_response = self.client.patch(
            reverse("expense-detail", args=[expense.id]),
            {"shop_name": "不正更新"},
            format="json",
        )
        delete_response = self.client.delete(reverse("expense-detail", args=[expense.id]))

        self.assertEqual(detail_response.status_code, 404)
        self.assertEqual(update_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        expense.refresh_from_db()
        self.assertEqual(expense.shop_name, "アンバーマート")

    def test_expense_detail_update_and_delete_require_login(self):
        expense = Expense.objects.create(user=self.user, **self.payload)
        url = reverse("expense-detail", args=[expense.id])

        detail_response = self.client.get(url)
        update_response = self.client.patch(url, {"shop_name": "不正更新"}, format="json")
        delete_response = self.client.delete(url)

        self.assertEqual(detail_response.status_code, 403)
        self.assertEqual(update_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)
        expense.refresh_from_db()
        self.assertEqual(expense.shop_name, "アンバーマート")

    def test_expense_delete_removes_record(self):
        expense = Expense.objects.create(user=self.user, **self.payload)
        self.client.force_authenticate(self.user)

        response = self.client.delete(reverse("expense-detail", args=[expense.id]))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Expense.objects.filter(pk=expense.id).exists())

    @override_settings(CLOUDINARY_URL="cloudinary://key:secret@example")
    @patch("expenses.serializers.signed_receipt_image_url", return_value="https://signed.example/receipt")
    @patch("expenses.views.upload_receipt_image")
    def test_expense_create_uploads_authenticated_image_and_hides_storage_fields(
        self, upload_mock, signed_url_mock
    ):
        upload_mock.return_value = StoredReceiptImage(
            url="https://res.cloudinary.com/example/image/authenticated/new.jpg",
            public_id="amber/receipts/1/new",
            format="jpg",
        )
        self.client.force_authenticate(self.user)
        image = SimpleUploadedFile("receipt.jpg", b"image-bytes", content_type="image/jpeg")

        response = self.client.post(
            reverse("expense-list"),
            {**self.payload, "image": image},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        expense = Expense.objects.get()
        self.assertEqual(
            expense.image,
            "https://res.cloudinary.com/example/image/authenticated/new.jpg",
        )
        self.assertEqual(expense.image_public_id, "amber/receipts/1/new")
        self.assertEqual(expense.image_format, "jpg")
        self.assertEqual(response.data["image"], "https://signed.example/receipt")
        self.assertNotIn("image_public_id", response.data)
        self.assertNotIn("image_format", response.data)
        signed_url_mock.assert_called_once_with("amber/receipts/1/new", "jpg")

    @override_settings(CLOUDINARY_URL="cloudinary://key:secret@example")
    @patch("expenses.serializers.signed_receipt_image_url", return_value="https://signed.example/receipt")
    @patch("expenses.views.upload_receipt_image")
    def test_multipart_create_records_ocr_history(self, upload_mock, _signed_url_mock):
        upload_mock.return_value = StoredReceiptImage(
            url="https://res.cloudinary.com/example/image/authenticated/new.jpg",
            public_id="amber/receipts/1/new",
            format="jpg",
        )
        self.client.force_authenticate(self.user)
        image = SimpleUploadedFile("receipt.jpg", b"image-bytes", content_type="image/jpeg")
        ocr_result = (
            '{"shop_name":"OCR店名","purchased_at":"2026-06-13",'
            '"total_amount":1200,"raw_ocr_text":"OCR店名\\n合計 1200",'
            '"confidence":91.5,"engine":"tesseract.js"}'
        )

        response = self.client.post(
            reverse("expense-list"),
            {**self.payload, "image": image, "ocr_result": ocr_result},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(OCRCorrectionHistory.objects.get().ocr_values["shop_name"], "OCR店名")

    @override_settings(CLOUDINARY_URL="cloudinary://key:secret@example")
    @patch("expenses.serializers.signed_receipt_image_url", return_value="https://signed.example/receipt")
    @patch("expenses.views.delete_receipt_image")
    @patch("expenses.views.upload_receipt_image")
    def test_expense_image_replacement_cleans_up_old_image(
        self, upload_mock, delete_mock, _signed_url_mock
    ):
        expense = Expense.objects.create(
            user=self.user,
            image="https://res.cloudinary.com/example/image/upload/old.jpg",
            image_public_id="amber/receipts/1/old",
            **self.payload,
        )
        upload_mock.return_value = StoredReceiptImage(
            url="https://res.cloudinary.com/example/image/authenticated/new.jpg",
            public_id="amber/receipts/1/new",
            format="jpg",
        )
        self.client.force_authenticate(self.user)
        image = SimpleUploadedFile("receipt.jpg", b"image-bytes", content_type="image/jpeg")

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.put(
                reverse("expense-detail", args=[expense.id]),
                {**self.payload, "image": image},
                format="multipart",
            )

        self.assertEqual(response.status_code, 200)
        expense.refresh_from_db()
        self.assertEqual(expense.image_public_id, "amber/receipts/1/new")
        self.assertEqual(expense.image_format, "jpg")
        delete_mock.assert_called_once_with("amber/receipts/1/old")

    @patch("expenses.views.delete_receipt_image")
    def test_expense_delete_cleans_up_managed_image(self, delete_mock):
        expense = Expense.objects.create(
            user=self.user,
            image="https://res.cloudinary.com/example/image/upload/old.jpg",
            image_public_id="amber/receipts/1/old",
            **self.payload,
        )
        self.client.force_authenticate(self.user)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(reverse("expense-detail", args=[expense.id]))

        self.assertEqual(response.status_code, 204)
        delete_mock.assert_called_once_with("amber/receipts/1/old")

    @override_settings(CLOUDINARY_URL="")
    def test_image_upload_without_cloudinary_config_does_not_create_expense(self):
        self.client.force_authenticate(self.user)
        image = SimpleUploadedFile("receipt.jpg", b"image-bytes", content_type="image/jpeg")

        response = self.client.post(
            reverse("expense-list"),
            {**self.payload, "image": image},
            format="multipart",
        )

        self.assertEqual(response.status_code, 503)
        self.assertFalse(Expense.objects.exists())

    @override_settings(CLOUDINARY_URL="cloudinary://key:secret@example")
    @patch("expenses.views.upload_receipt_image")
    def test_image_upload_failure_does_not_create_expense(self, upload_mock):
        upload_mock.side_effect = ImageStorageError("画像の保存に失敗しました。")
        self.client.force_authenticate(self.user)
        image = SimpleUploadedFile("receipt.jpg", b"image-bytes", content_type="image/jpeg")

        response = self.client.post(
            reverse("expense-list"),
            {**self.payload, "image": image},
            format="multipart",
        )

        self.assertEqual(response.status_code, 503)
        self.assertFalse(Expense.objects.exists())

    def test_update_and_delete_are_reflected_in_monthly_summary(self):
        expense = Expense.objects.create(user=self.user, **self.payload)
        self.client.force_authenticate(self.user)

        self.client.patch(
            reverse("expense-detail", args=[expense.id]),
            {"total_amount": 2000, "category": "日用品"},
            format="json",
        )
        updated_summary = self.client.get(
            reverse("monthly-summary"),
            {"year": 2026, "month": 6},
        )
        self.client.delete(reverse("expense-detail", args=[expense.id]))
        deleted_summary = self.client.get(
            reverse("monthly-summary"),
            {"year": 2026, "month": 6},
        )

        self.assertEqual(updated_summary.data["grand_total"], 2000)
        self.assertEqual(
            updated_summary.data["categories"],
            [{"category": "日用品", "total": 2000}],
        )
        self.assertEqual(deleted_summary.data["grand_total"], 0)

    def test_monthly_summary_requires_login(self):
        response = self.client.get(reverse("monthly-summary"), {"year": 2026, "month": 6})

        self.assertEqual(response.status_code, 403)

    def test_monthly_summary_returns_totals_for_current_user_and_month(self):
        Expense.objects.create(user=self.user, **self.payload)
        Expense.objects.create(
            user=self.user,
            shop_name="ドラッグストア",
            purchased_at="2026-06-20",
            total_amount=720,
            category="日用品",
        )
        Expense.objects.create(
            user=self.user,
            shop_name="別月の店",
            purchased_at="2026-05-31",
            total_amount=5000,
            category="食費",
        )
        Expense.objects.create(
            user=self.other_user,
            shop_name="別ユーザー店",
            purchased_at="2026-06-13",
            total_amount=999,
            category="その他",
        )
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("monthly-summary"), {"year": 2026, "month": 6})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["year"], 2026)
        self.assertEqual(response.data["month"], 6)
        self.assertEqual(response.data["grand_total"], 2000)
        self.assertEqual(
            response.data["categories"],
            [
                {"category": "日用品", "total": 720},
                {"category": "食費", "total": 1280},
            ],
        )

    def test_monthly_summary_returns_zero_when_no_expenses(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("monthly-summary"), {"year": 2026, "month": 1})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["grand_total"], 0)
        self.assertEqual(response.data["categories"], [])

    def test_monthly_summary_defaults_to_current_year_month(self):
        today = timezone.localdate()
        Expense.objects.create(
            user=self.user,
            shop_name="今月の店",
            purchased_at=today,
            total_amount=300,
            category="その他",
        )
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("monthly-summary"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["year"], today.year)
        self.assertEqual(response.data["month"], today.month)
        self.assertEqual(response.data["grand_total"], 300)

    def test_monthly_summary_rejects_invalid_query_params(self):
        self.client.force_authenticate(self.user)

        invalid_year_response = self.client.get(reverse("monthly-summary"), {"year": "abc", "month": 6})
        invalid_month_response = self.client.get(reverse("monthly-summary"), {"year": 2026, "month": 13})

        self.assertEqual(invalid_year_response.status_code, 400)
        self.assertEqual(invalid_month_response.status_code, 400)
