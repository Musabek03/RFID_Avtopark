from django.contrib import admin
from .models import Car, EntryLog

@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'rfid_tag', 'created_at')
    search_fields = ('title', 'rfid_tag', 'owner')

@admin.register(EntryLog)
class EntryLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'car', 'rfid_tag', 'is_authorized')
    list_filter = ('is_authorized', 'timestamp')
    readonly_fields = ('timestamp', 'rfid_tag', 'car')