"""Django admin registrations for core models."""

from django.contrib import admin

from .models import Car, EntryLog


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "owner",
        "rfid_tag",
        "vehicle_type",
        "is_inside",
        "is_active",
        "created_at",
    )
    list_filter = ("vehicle_type", "is_inside", "is_active")
    search_fields = ("title", "rfid_tag", "owner", "phone")
    readonly_fields = ("created_at", "updated_at", "last_entry_time", "last_exit_time")


@admin.register(EntryLog)
class EntryLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "car", "rfid_tag", "action", "is_authorized")
    list_filter = ("action", "is_authorized", "timestamp")
    search_fields = ("rfid_tag", "car__title", "car__owner")
    readonly_fields = ("timestamp", "rfid_tag", "car", "action", "is_authorized")
    date_hierarchy = "timestamp"
