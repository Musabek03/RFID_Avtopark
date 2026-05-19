"""Core domain models for the RFID parking system."""

from datetime import timedelta

from django.db import models
from django.urls import reverse
from django.utils import timezone


def format_duration(delta: timedelta) -> str:
    """Format a `timedelta` as a short human-readable duration string."""
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        total_seconds = 0
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days > 0:
        return f"{days} kún, {hours} saat, {minutes} min"
    if hours > 0:
        return f"{hours} saat {minutes} min"
    return f"{minutes} min"


class Car(models.Model):
    """A vehicle registered in the parking system, identified by an RFID tag."""

    class VehicleType(models.TextChoices):
        SEDAN = "SEDAN", "Jeńil avtomobil"
        TRUCK = "TRUCK", "Júk avtomobili"
        BUS = "BUS", "Avtobus"
        MOTORCYCLE = "MOTO", "Mototsikl"
        VAN = "VAN", "Mikroavtobus"
        OTHER = "OTHER", "Basqa"

    title = models.CharField("Avtomobil nomeri", max_length=50)
    owner = models.CharField("Iyesi", max_length=100, blank=True)
    rfid_tag = models.CharField("RFID metka", max_length=50, unique=True)
    description = models.TextField("Qosımsha maǵlıwmat", blank=True)

    vehicle_type = models.CharField(
        "Avtomobil túri",
        max_length=10,
        choices=VehicleType.choices,
        default=VehicleType.SEDAN,
    )
    color = models.CharField("Reńi", max_length=30, blank=True)
    phone = models.CharField("Iye telefonı", max_length=30, blank=True)

    is_inside = models.BooleanField("Avtoparkte", default=False)
    is_active = models.BooleanField(
        "Aktiv",
        default=True,
        help_text="Aktiv emes kartalar ushın kiriw biykar etiledi.",
    )

    last_entry_time = models.DateTimeField("Sońǵı kiriw waqtı", null=True, blank=True)
    last_exit_time = models.DateTimeField("Sońǵı shıǵıw waqtı", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Avtomobil"
        verbose_name_plural = "Avtomobiller"
        ordering = ["title"]
        indexes = [
            models.Index(fields=["rfid_tag"]),
            models.Index(fields=["is_inside", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.owner})" if self.owner else self.title

    def get_absolute_url(self) -> str:
        return reverse("car_edit", kwargs={"pk": self.pk})

    def get_duration(self) -> str:
        if self.is_inside and self.last_entry_time:
            return format_duration(timezone.now() - self.last_entry_time)
        return "—"

    @property
    def status_label(self) -> str:
        if not self.is_active:
            return "Aktiv emes"
        return "Ishinde" if self.is_inside else "Sırtta"


class EntryLog(models.Model):
    """Audit log of every RFID scan event."""

    class Action(models.TextChoices):
        IN = "IN", "Kiriw"
        OUT = "OUT", "Shıǵıw"
        DENIED = "DENIED", "Biykar etildi"
        COOLDOWN = "COOLDOWN", "Júdá tez (cooldown)"

    car = models.ForeignKey(
        Car,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Avtomobil",
        related_name="entries",
    )
    rfid_tag = models.CharField("Oqılǵan teg", max_length=50)
    timestamp = models.DateTimeField("Waqıt", auto_now_add=True)
    is_authorized = models.BooleanField("Ruxsat berildi", default=False)
    stay_duration = models.CharField(  # noqa: DJ001
        "Túrǵan waqtı",
        max_length=50,
        blank=True,
        null=True,
    )
    action = models.CharField(
        "Háleket", max_length=10, choices=Action.choices, default=Action.DENIED
    )
    note = models.CharField("Eskertpe", max_length=255, blank=True)

    class Meta:
        verbose_name = "Kirdi-shıqtı jurnalı"
        verbose_name_plural = "Kirdi-shıqtı jurnalı"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["-timestamp"]),
            models.Index(fields=["action", "-timestamp"]),
        ]

    def __str__(self) -> str:
        return f"{self.timestamp:%H:%M} — {self.get_action_display()}"
