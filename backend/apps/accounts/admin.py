from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class RecoverUserAdmin(UserAdmin):
    list_display = ("email", "role", "is_active", "email_verified")
    fieldsets = UserAdmin.fieldsets + (("RecoverIQ", {"fields": (
        "role", "student_id", "department", "year", "campus", "email_verified", "staff_requested",
        "staff_title", "can_review_claims", "can_release_items")}),)
