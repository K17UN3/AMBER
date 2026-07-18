from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from unittest.mock import patch

from .models import Category, Expense
from .services import classify_category
from receipts.models import OCRCorrectionHistory, OCRJob


User = get_user_model()


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
        self.categories = {category.name: category for category in Category.objects.all()}
        self.payload = {
            "shop_name": "アンバーマート",
            "purchased_at": "2026-06-13",
            "total_amount": 1280,
            "category": "食費",
            "raw_ocr_text": "アンバーマート\n合計 1280",
        }

    def create_expense(self, *, user, **values):
        category = values.pop("category")
        if isinstance(category, str):
            category = self.categories[category]
        return Expense.objects.create(user=user, category=category, **values)

    def test_monthly_summary_returns_only_current_user_totals(self):
        self.create_expense(user=self.user, purchased_at="2026-06-05", total_amount=2500, category="食費")
        self.create_expense(user=self.user, purchased_at="2026-06-10", total_amount=1800, category="日用品")
        self.create_expense(user=self.user, purchased_at="2026-06-12", total_amount=4200, category="食費")
        self.create_expense(user=self.other_user, purchased_at="2026-06-07", total_amount=9999, category="その他")

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
        self.assertEqual(response.data["category"], "食費")

    def test_expense_create_records_ocr_correction_history(self):
        ocr_job = OCRJob.objects.create(
            user=self.user,
            original_filename="receipt.jpg",
            content_type="image/jpeg",
            file_size=5,
            status=OCRJob.Status.SUCCEEDED,
            shop_name="OCR店名",
            purchased_at="2026-06-13",
            total_amount=1200,
            raw_ocr_text="OCR店名\n合計 1200",
            category=self.categories["食費"],
            image="receipts/test/receipt.jpg",
        )
        self.client.force_authenticate(self.user)

        response = self.client.post(
            reverse("expense-list"),
            {
                **self.payload,
                "ocr_job_id": str(ocr_job.id),
                "shop_name": "修正後の店名",
                "category": "日用品",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        history = OCRCorrectionHistory.objects.get()
        self.assertEqual(history.job, ocr_job)
        self.assertEqual(history.expense_id, response.data["id"])
        self.assertEqual(history.ocr_values["shop_name"], "OCR店名")
        self.assertEqual(history.saved_values["shop_name"], "修正後の店名")
        self.assertEqual(history.ocr_values["category"], "食費")
        self.assertEqual(history.saved_values["category"], "日用品")
        self.assertEqual(Expense.objects.get().category.name, "日用品")

        summary_response = self.client.get(
            reverse("monthly-summary"),
            {"year": 2026, "month": 6},
        )
        self.assertEqual(
            summary_response.data["categories"],
            [{"category": "日用品", "total": 1280}],
        )

    def test_expense_create_rolls_back_when_history_creation_fails(self):
        ocr_job = OCRJob.objects.create(
            user=self.user,
            original_filename="receipt.jpg",
            content_type="image/jpeg",
            file_size=5,
            status=OCRJob.Status.SUCCEEDED,
            image="receipts/test/receipt.jpg",
        )
        self.client.force_authenticate(self.user)

        with patch("expenses.views.OCRCorrectionHistory.objects.create", side_effect=RuntimeError("history failed")):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    reverse("expense-list"),
                    {**self.payload, "ocr_job_id": str(ocr_job.id)},
                    format="json",
                )

        self.assertEqual(Expense.objects.count(), 0)

    def test_expense_create_validates_required_fields(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("expense-list"), {"shop_name": "アンバー"}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("purchased_at", response.data)
        self.assertIn("total_amount", response.data)
        self.assertIn("category", response.data)

    def test_expense_create_rejects_unknown_category(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            reverse("expense-list"),
            {**self.payload, "category": "医療費"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("category", response.data)

    def test_category_list_returns_the_four_initial_categories(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("category-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [category["name"] for category in response.data],
            ["食費", "日用品", "交通費", "その他"],
        )

    def test_category_list_requires_login(self):
        response = self.client.get(reverse("category-list"))

        self.assertEqual(response.status_code, 403)

    def test_expense_list_returns_only_current_user_records(self):
        self.create_expense(user=self.user, **self.payload)
        self.create_expense(
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

    def test_monthly_summary_requires_login(self):
        response = self.client.get(reverse("monthly-summary"), {"year": 2026, "month": 6})

        self.assertEqual(response.status_code, 403)

    def test_monthly_summary_returns_totals_for_current_user_and_month(self):
        self.create_expense(user=self.user, **self.payload)
        self.create_expense(
            user=self.user,
            shop_name="ドラッグストア",
            purchased_at="2026-06-20",
            total_amount=720,
            category="日用品",
        )
        self.create_expense(
            user=self.user,
            shop_name="別月の店",
            purchased_at="2026-05-31",
            total_amount=5000,
            category="食費",
        )
        self.create_expense(
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
        self.create_expense(
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


class CategoryClassificationTests(TestCase):
    def test_classifies_shop_name_before_ocr_text(self):
        category = classify_category(
            shop_name="駅前スーパー",
            raw_ocr_text="ドラッグストア 洗剤",
        )

        self.assertEqual(category.name, "食費")

    def test_classifies_normalized_ocr_keyword(self):
        category = classify_category(raw_ocr_text="交通系ＩＣでお支払い")

        self.assertEqual(category.name, "交通費")

    def test_returns_other_when_no_keyword_matches(self):
        category = classify_category(shop_name="アンバー商会", raw_ocr_text="合計 1,280円")

        self.assertEqual(category.name, "その他")
