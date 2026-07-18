from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, Expense
from .serializers import CategorySerializer, ExpenseSerializer
from receipts.models import OCRCorrectionHistory, OCRJob


class CategoryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CategorySerializer(Category.objects.all(), many=True)
        return Response(serializer.data)


class ExpenseListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        expenses = Expense.objects.filter(user=request.user)
        serializer = ExpenseSerializer(expenses, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ExpenseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ocr_job_id = serializer.validated_data.get("ocr_job_id")
        ocr_job = None
        if ocr_job_id:
            ocr_job = OCRJob.objects.filter(
                pk=ocr_job_id,
                user=request.user,
                status=OCRJob.Status.SUCCEEDED,
            ).first()
            if ocr_job is None:
                return Response({"ocr_job_id": ["完了したOCRジョブを指定してください。"]}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            expense = serializer.save(user=request.user)
            if ocr_job:
                OCRCorrectionHistory.objects.create(
                    job=ocr_job,
                    expense=expense,
                    ocr_values={
                        "shop_name": ocr_job.shop_name,
                        "purchased_at": ocr_job.purchased_at.isoformat() if ocr_job.purchased_at else None,
                        "total_amount": ocr_job.total_amount,
                        "raw_ocr_text": ocr_job.raw_ocr_text,
                        "category": ocr_job.category.name if ocr_job.category else "その他",
                    },
                    saved_values={
                        "shop_name": expense.shop_name,
                        "purchased_at": expense.purchased_at.isoformat(),
                        "total_amount": expense.total_amount,
                        "category": expense.category.name,
                        "raw_ocr_text": expense.raw_ocr_text,
                    },
                )
        return Response(ExpenseSerializer(expense).data, status=status.HTTP_201_CREATED)


class ExpenseDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        expense = Expense.objects.filter(user=request.user, pk=pk).first()
        if expense is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = ExpenseSerializer(expense)
        return Response(serializer.data)


class MonthlyExpenseSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        year, month, error = self._get_year_month(request)
        if error:
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

        expenses = Expense.objects.filter(
            user=request.user,
            purchased_at__year=year,
            purchased_at__month=month,
        )

        grand_total = expenses.aggregate(total=Sum("total_amount"))["total"] or 0
        categories = (
            expenses.values("category__name")
            .annotate(total=Sum("total_amount"))
            .order_by("category__name")
        )

        return Response(
            {
                "year": year,
                "month": month,
                "grand_total": grand_total,
                "categories": [
                    {"category": item["category__name"], "total": item["total"] or 0}
                    for item in categories
                ],
            }
        )

    def _get_year_month(self, request):
        today = timezone.localdate()
        year_value = request.query_params.get("year", today.year)
        month_value = request.query_params.get("month", today.month)

        try:
            year = int(year_value)
            month = int(month_value)
        except (TypeError, ValueError):
            return None, None, {"detail": "year and month must be integers."}

        if year < 1:
            return None, None, {"detail": "year must be greater than or equal to 1."}
        if month < 1 or month > 12:
            return None, None, {"detail": "month must be between 1 and 12."}

        return year, month, None
