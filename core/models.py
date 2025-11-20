from django.db import models
from django.utils import timezone


class Car(models.Model):
    license_plate = models.CharField(max_length=50, unique=True, verbose_name="Avto_Nomer")
    brand = models.CharField(max_length=50, verbose_name="Marka")
    model = models.CharField(max_length=50, verbose_name="Model")
    owner_name = models.CharField(max_length=100, blank=True, verbose_name="Avtomobil iyesi")
    rfid_tag = models.CharField(max_length=100, unique=True, verbose_name="RFID-tag")

    def __str__(self):
        return f"Avtomobil nomeri: {self.license_plate} ||  Avtomobil modeli: {self.model} || Avtomobil iyesi: {self.owner_name}"


class ParkingSession(models.Model):
    car  = models.ForeignKey(Car, on_delete=models.CASCADE, verbose_name="Avtomobil", related_name="Session")
    entry_time = models.DateTimeField(default=timezone.now, verbose_name="Kiriw waqti")
    exit_time =  models.DateTimeField(null=True, blank=True, verbose_name="Shigiw waqti")
    is_inside = models.BooleanField(default=True, verbose_name="Avtomobil parkovkada")

    def __str__(self):
        return f"{self.car} ushin sessiya {self.entry_time.strftime('%Y-%m-%d %H:%M')} da baslandi"
    
    @property
    def duration(self):
        if self.exit_time:
            return self.exit_time - self.entry_time
        return None