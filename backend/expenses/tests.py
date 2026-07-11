from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Expense


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
                {"category": "食費", "total": 6700},
                {"category": "日用品", "total": 1800},
            ],
        )

    def test_monthly_summary_defaults_to_current_month_when_params_are_invalid(self):
        today = timezone.localdate()
        Expense.objects.create(
            user=self.user,
            purchased_at=f"{today.year}-{today.month:02d}-01",
            total_amount=1000,
            category="その他",
        )
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("monthly-summary"), {"year": "bad", "month": 99})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["year"], today.year)
        self.assertEqual(response.data["month"], today.month)
        self.assertEqual(response.data["grand_total"], 1000)
        self.assertEqual(response.data["categories"], [{"category": "その他", "total": 1000}])

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
