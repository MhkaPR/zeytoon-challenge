"""Operator-facing admin for users, blocks, and roles.

Group membership (``regular`` / ``admin``) is edited here; django-guardian handles
object-level permissions. Runtime constants are edited through the constance admin.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("phone_number", "status", "is_active", "is_staff", "role")
    list_filter = ("status", "is_active", "is_staff", "groups")
    search_fields = ("phone_number", "username")
    ordering = ("phone_number",)
    fieldsets = (
        (None, {"fields": ("username", "phone_number", "password")}),
        ("Status", {"fields": ("status", "is_active", "is_staff", "is_superuser")}),
        ("Roles & permissions", {"fields": ("groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at")

    def role(self, obj):
        return obj.role()

    role.short_description = "Role"
