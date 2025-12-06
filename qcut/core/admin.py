from django.contrib import admin
from .models import CustomUser, QueueSession
from django.contrib.auth.admin import UserAdmin

admin.site.register(QueueSession)

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser

    fieldsets = UserAdmin.fieldsets + (
        (None, {"fields": ("full_name", "phone_number", "user_type", "address", "google_map_url", "latitude", "longitude")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "password1", "password2", "full_name", "phone_number", "user_type"),
        }),
    )

    list_display = ("id", "full_name", "phone_number","address", "user_type", "is_staff")
