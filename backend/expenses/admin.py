from django.contrib import admin

from .models import Category, Expense


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "keywords"]
    search_fields = ["name", "keywords"]
    readonly_fields = ["name"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Expense)
