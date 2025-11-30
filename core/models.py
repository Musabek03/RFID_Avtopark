from django.db import models

class Car(models.Model):
    title = models.CharField("Avtomovil nomeri", max_length=50)
    owner = models.CharField("Iyesi", max_length=100, blank=True)
    rfid_tag = models.CharField("RFID metka", max_length=50, unique=True)
    description = models.TextField("Opisanie", blank=True)
    
    # НОВОЕ ПОЛЕ: Где сейчас машина? (False = Снаружи, True = Внутри)
    is_inside = models.BooleanField("Avtoparkte", default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.owner})"

    class Meta:
        verbose_name = "Avtomobil"
        verbose_name_plural = "Avtomobiller"

class EntryLog(models.Model):
    ACTION_CHOICES = [
        ('IN', 'Вход (Kiriw)'),
        ('OUT', 'Выход (Shigiw)'),
        ('DENIED', 'Отказано (Inkar etildi)') # Для чужих меток
    ]

    car = models.ForeignKey(Car, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Avtomobil")
    rfid_tag = models.CharField("Oqilgan teg", max_length=50)
    timestamp = models.DateTimeField("Waqit", auto_now_add=True)
    is_authorized = models.BooleanField("Ruxsat berilgen", default=False)
    
    # НОВОЕ ПОЛЕ: Тип действия
    action = models.CharField("Status", max_length=10, choices=ACTION_CHOICES, default='DENIED')

    def __str__(self):
        return f"{self.timestamp.strftime('%H:%M')} - {self.get_action_display()}"

    class Meta:
        verbose_name = "Kirdi shiqti jurnali"
        verbose_name_plural = "Kirdi shiqti jurnali"
        ordering = ['-timestamp']