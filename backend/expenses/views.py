from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Expense
from .serializers import ExpenseSerializer


class ExpenseListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        expenses = Expense.objects.filter(user=request.user)
        serializer = ExpenseSerializer(expenses, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ExpenseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        expense = serializer.save(user=request.user)
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
            expenses.values("category")
            .annotate(total=Sum("total_amount"))
            .order_by("category")
        )

        return Response(
            {
                "year": year,
                "month": month,
                "grand_total": grand_total,
                "categories": [
                    {"category": item["category"], "total": item["total"] or 0}
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
