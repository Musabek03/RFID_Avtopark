from django import forms
from .models import Car

class CarForm(forms.ModelForm):
    class Meta:
        model = Car
        fields = ['title', 'owner', 'rfid_tag', 'description'] 
        
        # CSS + Placeholderlar
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Misali: 95 Z 777 ZZ'
            }),
            'owner': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Misali: Palensheev Tolenshe'
            }),
            'rfid_tag': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Skanerlanganda avtomat to\'ldiriladi'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Qosimsha magliwmat...'
            }),
        }
        # Labels
        labels = {
            'title': 'Avtomobil nomeri',
            'owner': 'Iyesi',
            'rfid_tag': 'RFID Kod',
            'description': 'Qosimsha',
        }