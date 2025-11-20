from django.shortcuts import render, redirect
from django.views import View
from django.utils import timezone
from .models import Car, ParkingSession
from django.contrib import messages
from django.views.generic import ListView, CreateView
from .forms import CarForm
from django.urls import reverse_lazy


class DashboardView(ListView):
    model = ParkingSession
    template_name = 'dashboard.html'  
    context_object_name = 'sessions'

    def get_queryset(self):
        return ParkingSession.objects.filter(is_inside=True).order_by('-entry_time')
    

    def post(self, request, *args, **kwargs):
        
        rfid_tag = request.POST.get('rfid_tag')
        
        try:
            car = Car.objects.get(rfid_tag=rfid_tag)
        except Car.DoesNotExist:
            messages.error(request, f"{rfid_tag} Tegli avtomobil tabilmadi!")
            return redirect('dashboard') 

        
        active_session = ParkingSession.objects.filter(car=car, is_inside=True).first()

        if active_session:
            active_session.exit_time = timezone.now()
            active_session.is_inside = False
            active_session.save()
            messages.success(request, f"Avtomobil {car.license_plate} parkovkadan shiqti.")
        else:
            ParkingSession.objects.create(car=car)
            messages.success(request, f"Avtomobil {car.license_plate} parkovkaga kirdi.")
        
        return redirect('dashboard') 



class HistoryListView(ListView):
    model = ParkingSession
    template_name = 'history.html'
    context_object_name = 'parking_sessions' 
    queryset = ParkingSession.objects.all().order_by('-entry_time')



class CarCreateView(CreateView):
    model = Car
    form_class = CarForm
    template_name = 'add_car.html'
    success_url = reverse_lazy('dashboard') 

    def form_valid(self, form):
        messages.success(self.request, f"Avtomobil {form.instance.license_plate} qosildi.")
        return super().form_valid(form)