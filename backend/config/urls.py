from django.contrib import admin
from django.http import JsonResponse
from django.urls import path

from accounts.views import CsrfTokenView, CurrentUserView, LoginView, LogoutView, RegisterView
from expenses.views import ExpenseDetailView, ExpenseListCreateView, MonthlyExpenseSummaryView
from receipts.views import ReceiptAnalyzeView


def health_check(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("admin/", admin.site.urls),
    path("api/auth/csrf/", CsrfTokenView.as_view(), name="auth-csrf"),
    path("api/auth/user/", CurrentUserView.as_view(), name="auth-user"),
    path("api/auth/register/", RegisterView.as_view(), name="auth-register"),
    path("api/auth/login/", LoginView.as_view(), name="auth-login"),
    path("api/auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("api/expenses/", ExpenseListCreateView.as_view(), name="expense-list"),
    path("api/expenses/<int:pk>/", ExpenseDetailView.as_view(), name="expense-detail"),
    path("api/receipts/analyze/", ReceiptAnalyzeView.as_view(), name="receipt-analyze"),
    path("api/summary/monthly/", MonthlyExpenseSummaryView.as_view(), name="monthly-summary"),
]
