from django.contrib import admin
from .models import Car, ParkingSession

@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('license_plate', 'brand', 'model', 'rfid_tag')
    search_fields = ('license_plate', 'rfid_tag')

@admin.register(ParkingSession)
class ParkingSessionAdmin(admin.ModelAdmin):
    list_display = ('car', 'entry_time', 'exit_time', 'is_inside')
    list_filter = ('is_inside', 'entry_time')
    search_fields = ('car__license_plate',)