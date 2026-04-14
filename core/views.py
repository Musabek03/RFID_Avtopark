from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Car, EntryLog
from .forms import CarForm
import json
from datetime import timedelta
from django.utils import timezone


# ─── DASHBOARD 
def index(request):
    cars_inside = Car.objects.filter(is_inside=True).order_by('-last_entry_time')
    count = cars_inside.count()

    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    total_cars    = Car.objects.count()
    today_entries = EntryLog.objects.filter(action='IN',     timestamp__gte=today_start).count()
    today_exits   = EntryLog.objects.filter(action='OUT',    timestamp__gte=today_start).count()
    today_denied  = EntryLog.objects.filter(action='DENIED', timestamp__gte=today_start).count()

    return render(request, 'dashboard.html', {
        'cars':          cars_inside,
        'count':         count,
        'total_cars':    total_cars,
        'today_entries': today_entries,
        'today_exits':   today_exits,
        'today_denied':  today_denied,
    })


# ─── HISTORY 
def history(request):
    logs = EntryLog.objects.select_related('car').order_by('-timestamp')

    # Optional filter
    f = request.GET.get('filter')
    if f in ('IN', 'OUT', 'DENIED'):
        logs = logs.filter(action=f)

    return render(request, 'history.html', {'logs': logs})


# ─── ADD CAR 
def add_car(request):
    tag_from_url = request.GET.get('tag')

    if request.method == 'POST':
        form = CarForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        initial = {'rfid_tag': tag_from_url} if tag_from_url else {}
        form = CarForm(initial=initial)

    return render(request, 'add_car.html', {'form': form})


# ─── RFID API 
@csrf_exempt
def rfid_api(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Tek ǵana POST'}, status=405)

    try:
        data = json.loads(request.body)
        tag  = data.get('rfid_tag', '').strip()

        if not tag:
            return JsonResponse({'status': 'error', 'message': 'Tag joq'}, status=400)

        duration_text = None

        try:
            car        = Car.objects.get(rfid_tag=tag)
            authorized = True

            # ─ cooldown ───
            last_log = EntryLog.objects.filter(car=car).order_by('-timestamp').first()
            if last_log:
                min_delay = 10 if last_log.action == 'OUT' else 60
                time_diff = timezone.now() - last_log.timestamp
                if time_diff < timedelta(seconds=min_delay):
                    remaining = int(min_delay - time_diff.total_seconds())
                    return JsonResponse({
                        'status':     'warning',
                        'message':    f"Juda tez! {remaining} sek kutiń",
                        'authorized': False,
                    })

            if car.is_inside:
                # ─ CHIQISH ─
                action  = 'OUT'
                message = f"↑ Shıǵıw: {car.title}"

                if car.last_entry_time:
                    diff          = timezone.now() - car.last_entry_time
                    total_seconds = int(diff.total_seconds())
                    days    = total_seconds // 86400
                    hours   = (total_seconds % 86400) // 3600
                    minutes = (total_seconds % 3600) // 60

                    if days > 0:
                        duration_text = f"{days} kun, {hours} saat, {minutes} min"
                    elif hours > 0:
                        duration_text = f"{hours} saat {minutes} min"
                    else:
                        duration_text = f"{minutes} min"

                car.is_inside = False

            else:
                # ─ KIRISH ─
                action  = 'IN'
                message = f"↓ Kiriw: {car.title}"
                car.is_inside       = True
                car.last_entry_time = timezone.now()

            car.save()

        except Car.DoesNotExist:
            car        = None
            authorized = False
            action     = 'DENIED'
            message    = f"Biytanis teg: {tag} — ruxsat joq"

        EntryLog.objects.create(
            car=car,
            rfid_tag=tag,
            is_authorized=authorized,
            action=action,
            stay_duration=duration_text,
        )

        print(f"📡 SCAN: {tag} → {action}")
        return JsonResponse({
            'status':     'success',
            'message':    message,
            'authorized': authorized,
            'action':     action,
        })

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Nadurıs JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)