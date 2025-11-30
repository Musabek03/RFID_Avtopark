from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Car, EntryLog
from .forms import CarForm # Если у тебя есть формы, иначе удали эту строку и используй HTML форму
import json
from datetime import timedelta
from django.utils import timezone

#Dashboard
def index(request):
    cars_inside = Car.objects.filter(is_inside=True).order_by('-created_at')
    
    count = cars_inside.count()
    
    return render(request, 'dashboard.html', {
        'cars': cars_inside,
        'count': count
    })

def history(request):
    logs = EntryLog.objects.select_related('car').order_by('-timestamp')
    return render(request, 'history.html', {'logs': logs})

# Add car
def add_car(request):
    tag_from_url = request.GET.get('tag')
    
    if request.method == 'POST':
        form = CarForm(request.POST)
        if form.is_valid():
            form.save() 
            return redirect('dashboard')
    else:
        if tag_from_url:
            form = CarForm(initial={'rfid_tag': tag_from_url})
        else:
            form = CarForm()
            
    return render(request, 'add_car.html', {'form': form})

# API for scanner
@csrf_exempt
def rfid_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            tag = data.get('rfid_tag')
            
            if not tag:
                return JsonResponse({'status': 'error', 'message': 'Teg joq'}, status=400)

            MIN_DELAY_SECONDS = 60 

            try:
                car = Car.objects.get(rfid_tag=tag)
                authorized = True
                
                last_log = EntryLog.objects.filter(car=car).order_by('-timestamp').first()
                
                if last_log:
                    time_diff = timezone.now() - last_log.timestamp
                    if time_diff < timedelta(seconds=MIN_DELAY_SECONDS):
                        return JsonResponse({
                            'status': 'warning', 
                            'message': f"Juda tez! Kutin {int(60 - time_diff.total_seconds())} sek.",
                            'authorized': False
                        })

                if car.is_inside:
                    action = 'OUT'
                    message = f"🚗 Shigiw: {car.title}"
                    car.is_inside = False 
                else:
                    action = 'IN'
                    message = f"🚙 Kiriw: {car.title}"
                    car.is_inside = True 
                
                car.save() 

            except Car.DoesNotExist:
                car = None
                authorized = False
                action = 'DENIED'
                message = "Biytanis avtomobil! Ruxsat joq"

            EntryLog.objects.create(
                car=car,
                rfid_tag=tag,
                is_authorized=authorized,
                action=action
            )

            print(f"📡 SCAN: {tag} -> {action}")
            return JsonResponse({'status': 'success', 'message': message, 'authorized': authorized})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Tek gana POST zaproslar'}, status=405)