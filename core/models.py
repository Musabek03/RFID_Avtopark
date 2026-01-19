from django.db import models
from django.utils import timezone 

# --- CAR MODELI ---
class Car(models.Model):
    title = models.CharField("Avtomobil nomeri", max_length=50)
    owner = models.CharField("Iyesi", max_length=100, blank=True)
    rfid_tag = models.CharField("RFID metka", max_length=50, unique=True)
    description = models.TextField("Opisanie", blank=True)
    
    is_inside = models.BooleanField("Avtoparkte", default=False)
    
    # Kiriw waqtin eslep qaliw ushin
    last_entry_time = models.DateTimeField("Songi kiriw waqti", null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.owner})"

    # Dashboard ushin esaplaw
    def get_duration(self):
        if self.is_inside and self.last_entry_time:
            now = timezone.now()
            diff = now - self.last_entry_time
            total_seconds = int(diff.total_seconds())
            
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            minutes = (total_seconds % 3600) // 60
            
            if days > 0:
                return f"{days} kun, {hours} saat, {minutes} min"
            elif hours > 0:
                return f"{hours} saat {minutes} min"
            else:
                return f"{minutes} min"
        return "Jana kirdi" 

    class Meta:
        verbose_name = "Avtomobil"
        verbose_name_plural = "Avtomobiller"


# --- ENTRYLOG MODELI (Janalandi) ---
class EntryLog(models.Model):
    ACTION_CHOICES = [
        ('IN', 'Вход (Kiriw)'),
        ('OUT', 'Выход (Shigiw)'),
        ('DENIED', 'Отказано (Inkar etildi)') 
    ]

    car = models.ForeignKey(Car, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Avtomobil")
    rfid_tag = models.CharField("Oqilgan teg", max_length=50)
    timestamp = models.DateTimeField("Waqit", auto_now_add=True)
    is_authorized = models.BooleanField("Ruxsat berilgen", default=False)
    
    # --- QOSILGAN JANA MAYDAN ---
    stay_duration = models.CharField("Turǵan waqtı", max_length=50, blank=True, null=True)

    action = models.CharField("Status", max_length=10, choices=ACTION_CHOICES, default='DENIED')

    def __str__(self):
        return f"{self.timestamp.strftime('%H:%M')} - {self.get_action_display()}"

    class Meta:
        verbose_name = "Kirdi shiqti jurnali"
        verbose_name_plural = "Kirdi shiqti jurnali"
        ordering = ['-timestamp']