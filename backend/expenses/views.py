import json

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .image_storage import (
    ImageStorageError,
    ImageValidationError,
    delete_receipt_image,
    upload_receipt_image,
)
from .models import Category, Expense
from .serializers import (
    CategoryClassificationInputSerializer,
    CategorySerializer,
    ExpenseSerializer,
)
from .services import classify_category
from receipts.models import OCRCorrectionHistory


class ImageStorageUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "image_storage_unavailable"


class CategoryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(CategorySerializer(Category.objects.all(), many=True).data)


class CategoryClassifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CategoryClassificationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = classify_category(**serializer.validated_data)
        return Response(CategorySerializer(category).data)


class ExpenseListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        expenses = Expense.objects.filter(user=request.user).select_related("category")
        serializer = ExpenseSerializer(expenses, many=True)
        return Response(serializer.data)

    def post(self, request):
        data, image = _expense_request_data(request)
        serializer = ExpenseSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        ocr_result = serializer.validated_data.get("ocr_result")
        uploaded_image = _upload_image_or_error(image, request.user.id)
        image_values = _uploaded_image_values(uploaded_image)
        try:
            with transaction.atomic():
                expense = serializer.save(user=request.user, **image_values)
                if ocr_result:
                    automatic_category = ocr_result.get("category")
                    if automatic_category is None:
                        automatic_category = classify_category(
                            shop_name=ocr_result.get("shop_name") or "",
                            raw_ocr_text=ocr_result.get("raw_ocr_text") or "",
                        ).name
                    OCRCorrectionHistory.objects.create(
                        expense=expense,
                        ocr_values={
                            **ocr_result,
                            "purchased_at": (
                                ocr_result["purchased_at"].isoformat()
                                if ocr_result["purchased_at"]
                                else None
                            ),
                            "category": automatic_category,
                        },
                        saved_values={
                            "shop_name": expense.shop_name,
                            "purchased_at": expense.purchased_at.isoformat(),
                            "total_amount": expense.total_amount,
                            "category": expense.category.name,
                            "raw_ocr_text": expense.raw_ocr_text,
                        },
                    )
        except Exception:
            if uploaded_image:
                delete_receipt_image(uploaded_image.public_id)
            raise
        return Response(ExpenseSerializer(expense).data, status=status.HTTP_201_CREATED)


class ExpenseDetailView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request, pk):
        expense = self._get_expense(request, pk)

        serializer = ExpenseSerializer(expense)
        return Response(serializer.data)

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def delete(self, request, pk):
        expense = self._get_expense(request, pk)
        public_id = expense.image_public_id

        with transaction.atomic():
            expense.delete()
            if public_id:
                transaction.on_commit(lambda public_id=public_id: delete_receipt_image(public_id))

        return Response(status=status.HTTP_204_NO_CONTENT)

    def _update(self, request, pk, partial):
        expense = self._get_expense(request, pk)
        data, image = _expense_request_data(request)
        serializer = ExpenseSerializer(expense, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)

        uploaded_image = _upload_image_or_error(image, request.user.id)
        old_public_id = expense.image_public_id
        image_values = _uploaded_image_values(uploaded_image)

        try:
            with transaction.atomic():
                expense = serializer.save(**image_values)
                if old_public_id and old_public_id != expense.image_public_id:
                    transaction.on_commit(
                        lambda public_id=old_public_id: delete_receipt_image(public_id)
                    )
        except Exception:
            if uploaded_image:
                delete_receipt_image(uploaded_image.public_id)
            raise

        return Response(ExpenseSerializer(expense).data)

    @staticmethod
    def _get_expense(request, pk):
        expense = (
            Expense.objects.filter(user=request.user, pk=pk)
            .select_related("category")
            .first()
        )
        if expense is None:
            raise NotFound()
        return expense


def _expense_request_data(request):
    image = request.FILES.get("image")
    if image is None:
        return request.data, None

    data = {key: value for key, value in request.data.items() if key != "image"}
    ocr_result = data.get("ocr_result")
    if isinstance(ocr_result, str):
        try:
            data["ocr_result"] = json.loads(ocr_result)
        except json.JSONDecodeError as exc:
            raise ValidationError({"ocr_result": ["OCR解析結果の形式が不正です。"]}) from exc
    return data, image


def _upload_image_or_error(image, user_id):
    if image is None:
        return None

    try:
        return upload_receipt_image(image, user_id)
    except ImageValidationError as exc:
        raise ValidationError({"image": [str(exc)]}) from exc
    except ImageStorageError as exc:
        raise ImageStorageUnavailable(str(exc)) from exc


def _uploaded_image_values(uploaded_image):
    if uploaded_image is None:
        return {}
    return {
        "image": uploaded_image.url,
        "image_public_id": uploaded_image.public_id,
        "image_format": uploaded_image.format,
    }


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
