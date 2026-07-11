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


class MonthlySummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()
        year = self._parse_query_int(request.query_params.get("year"), default=today.year)
        month = self._parse_query_int(request.query_params.get("month"), default=today.month)

        if year is None or year < 1:
            year = today.year
        if month is None or month < 1 or month > 12:
            month = today.month

        expenses = Expense.objects.filter(
            user=request.user,
            purchased_at__year=year,
            purchased_at__month=month,
        )

        categories = list(
            expenses.values("category").annotate(total=Sum("total_amount")).order_by("-total", "category")
        )
        grand_total = expenses.aggregate(total=Sum("total_amount"))["total"] or 0

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

    def _parse_query_int(self, value, default):
        if value in (None, ""):
            return default

        try:
            return int(value)
        except (TypeError, ValueError):
            return default
