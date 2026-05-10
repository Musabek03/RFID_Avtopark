"""Forms for the core app."""

from django import forms

from .models import Car


class CarForm(forms.ModelForm):
    class Meta:
        model = Car
        fields = [
            "title",
            "owner",
            "phone",
            "rfid_tag",
            "vehicle_type",
            "color",
            "is_active",
            "description",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Mısalı: 95 Z 777 ZZ"}
            ),
            "owner": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Atı familiyası"}
            ),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "+998 ..."}),
            "rfid_tag": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Skanerlanǵanda avtomat tolıqtırıladı",
                    "style": "font-family: var(--font-mono); letter-spacing: 2px;",
                }
            ),
            "vehicle_type": forms.Select(attrs={"class": "form-control"}),
            "color": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Mısalı: aq, qara"}
            ),
            "is_active": forms.CheckboxInput(),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Qosımsha maǵlıwmat...",
                }
            ),
        }
        labels = {
            "title": "Avtomobil nomeri",
            "owner": "Iyesi",
            "phone": "Telefon",
            "rfid_tag": "RFID kod",
            "vehicle_type": "Avtomobil túri",
            "color": "Reńi",
            "is_active": "Aktiv",
            "description": "Qosımsha",
        }


class HistoryFilterForm(forms.Form):
    """Filter form for the entry-log history page."""

    action = forms.ChoiceField(
        required=False,
        choices=[
            ("", "Hámmesi"),
            ("IN", "Kiriw"),
            ("OUT", "Shıǵıw"),
            ("DENIED", "Inkar etildi"),
            ("COOLDOWN", "Cooldown"),
        ],
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    q = forms.CharField(
        required=False,
        label="Izlew",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Avtomobil nomeri, iye yamasa RFID...",
            }
        ),
    )
    date_from = forms.DateField(
        required=False,
        label="Sáneden",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    date_to = forms.DateField(
        required=False,
        label="Sánege shekem",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
