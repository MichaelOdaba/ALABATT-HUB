from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Sports unit", {"fields": ("category", "role")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Sports unit", {"fields": ("email", "category", "role")}),
    )
    list_display = ("username", "email", "category", "role", "is_active")