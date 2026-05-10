"""HTTP views for the core app."""

from __future__ import annotations

import csv
import json
import logging
from datetime import date, timedelta
from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncHour
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from .forms import CarForm, HistoryFilterForm
from .models import Car, EntryLog, format_duration
from .services import process_scan

logger = logging.getLogger(__name__)


# ─── HELPERS ──────────────────────────────────────────────────────────────


def _today_start():
    return timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)


def _filtered_logs(request: HttpRequest):
    qs = EntryLog.objects.select_related("car").order_by("-timestamp")
    form = HistoryFilterForm(request.GET or None)
    if form.is_valid():
        cd = form.cleaned_data
        if cd.get("action"):
            qs = qs.filter(action=cd["action"])
        if cd.get("q"):
            term = cd["q"]
            qs = qs.filter(
                Q(rfid_tag__icontains=term)
                | Q(car__title__icontains=term)
                | Q(car__owner__icontains=term)
            )
        if cd.get("date_from"):
            qs = qs.filter(timestamp__date__gte=cd["date_from"])
        if cd.get("date_to"):
            qs = qs.filter(timestamp__date__lte=cd["date_to"])
    return qs, form


# ─── DASHBOARD ────────────────────────────────────────────────────────────


@login_required
def index(request: HttpRequest) -> HttpResponse:
    cars_inside = Car.objects.filter(is_inside=True, is_active=True).order_by("-last_entry_time")
    today_start = _today_start()
    context = {
        "cars": cars_inside,
        "count": cars_inside.count(),
        "total_cars": Car.objects.filter(is_active=True).count(),
        "today_entries": EntryLog.objects.filter(action="IN", timestamp__gte=today_start).count(),
        "today_exits": EntryLog.objects.filter(action="OUT", timestamp__gte=today_start).count(),
        "today_denied": EntryLog.objects.filter(
            action="DENIED", timestamp__gte=today_start
        ).count(),
    }
    return render(request, "dashboard.html", context)


@login_required
def dashboard_api(request: HttpRequest) -> JsonResponse:
    """JSON endpoint used by the dashboard for live (AJAX) refreshes."""
    cars_inside = list(
        Car.objects.filter(is_inside=True, is_active=True)
        .order_by("-last_entry_time")
        .values("id", "title", "owner", "rfid_tag", "vehicle_type", "last_entry_time")
    )
    for car in cars_inside:
        if car["last_entry_time"]:
            duration = timezone.now() - car["last_entry_time"]
            car["duration"] = format_duration(duration)
            car["last_entry_time"] = car["last_entry_time"].isoformat()
        else:
            car["duration"] = "—"
    today_start = _today_start()
    return JsonResponse(
        {
            "cars": cars_inside,
            "count": len(cars_inside),
            "total_cars": Car.objects.filter(is_active=True).count(),
            "today_entries": EntryLog.objects.filter(
                action="IN", timestamp__gte=today_start
            ).count(),
            "today_exits": EntryLog.objects.filter(
                action="OUT", timestamp__gte=today_start
            ).count(),
            "today_denied": EntryLog.objects.filter(
                action="DENIED", timestamp__gte=today_start
            ).count(),
            "server_time": timezone.now().isoformat(),
        }
    )


# ─── HISTORY ──────────────────────────────────────────────────────────────


@login_required
def history(request: HttpRequest) -> HttpResponse:
    qs, form = _filtered_logs(request)
    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "history.html",
        {"page_obj": page, "form": form, "total": paginator.count},
    )


@login_required
def history_export(request: HttpRequest) -> HttpResponse:
    """Export the filtered history as CSV or XLSX."""
    qs, _ = _filtered_logs(request)
    fmt = request.GET.get("format", "csv").lower()
    headers = [
        "Sáne",
        "Waqıt",
        "Avtomobil",
        "Iyesi",
        "RFID",
        "Háleket",
        "Túrǵan waqtı",
        "Eskerme",
    ]

    def row(log: EntryLog):
        return [
            log.timestamp.strftime("%Y-%m-%d"),
            log.timestamp.strftime("%H:%M:%S"),
            log.car.title if log.car else "—",
            log.car.owner if log.car else "—",
            log.rfid_tag,
            log.get_action_display(),
            log.stay_duration or "",
            log.note or "",
        ]

    if fmt == "xlsx":
        try:
            from openpyxl import Workbook
        except ImportError:  # pragma: no cover - guarded by requirements
            return HttpResponse("openpyxl ornatılmaǵan", status=500)
        wb = Workbook()
        ws = wb.active
        ws.title = "History"
        ws.append(headers)
        for log in qs.iterator():
            ws.append(row(log))
        for i in range(1, len(headers) + 1):
            ws.column_dimensions[chr(64 + i)].width = 18
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        resp = HttpResponse(
            buf.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp["Content-Disposition"] = (
            f'attachment; filename="rfid-history-{date.today().isoformat()}.xlsx"'
        )
        return resp

    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = (
        f'attachment; filename="rfid-history-{date.today().isoformat()}.csv"'
    )
    writer = csv.writer(resp)
    writer.writerow(headers)
    for log in qs.iterator():
        writer.writerow(row(log))
    return resp


# ─── CARS ─────────────────────────────────────────────────────────────────


@login_required
def car_list(request: HttpRequest) -> HttpResponse:
    qs = Car.objects.all().order_by("title")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(owner__icontains=q) | Q(rfid_tag__icontains=q))
    show_inactive = request.GET.get("show_inactive") == "1"
    if not show_inactive:
        qs = qs.filter(is_active=True)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "car_list.html",
        {"page_obj": page, "q": q, "show_inactive": show_inactive},
    )


@login_required
def car_add(request: HttpRequest) -> HttpResponse:
    tag_from_url = request.GET.get("tag")
    if request.method == "POST":
        form = CarForm(request.POST)
        if form.is_valid():
            car = form.save()
            messages.success(request, f"{car.title} sátti qosıldı.")
            return redirect("car_list")
    else:
        form = CarForm(initial={"rfid_tag": tag_from_url} if tag_from_url else {})
    return render(request, "add_car.html", {"form": form})


@login_required
def car_edit(request: HttpRequest, pk: int) -> HttpResponse:
    car = get_object_or_404(Car, pk=pk)
    if request.method == "POST":
        form = CarForm(request.POST, instance=car)
        if form.is_valid():
            form.save()
            messages.success(request, f"{car.title} jańalandı.")
            return redirect("car_list")
    else:
        form = CarForm(instance=car)
    return render(request, "car_edit.html", {"form": form, "car": car})


@login_required
@require_POST
def car_delete(request: HttpRequest, pk: int) -> HttpResponse:
    car = get_object_or_404(Car, pk=pk)
    title = car.title
    car.delete()
    messages.success(request, f"{title} óshirildi.")
    return redirect("car_list")


# ─── STATISTICS ───────────────────────────────────────────────────────────


@login_required
def statistics(request: HttpRequest) -> HttpResponse:
    return render(request, "statistics.html")


@login_required
def statistics_api(request: HttpRequest) -> JsonResponse:
    """Return aggregated stats for the statistics dashboard."""
    days = int(request.GET.get("days", "7"))
    days = max(1, min(days, 90))
    start = timezone.now() - timedelta(days=days)

    by_day = (
        EntryLog.objects.filter(timestamp__gte=start)
        .annotate(day=TruncDate("timestamp"))
        .values("day", "action")
        .annotate(n=Count("id"))
        .order_by("day")
    )

    by_hour = (
        EntryLog.objects.filter(timestamp__gte=start, action__in=["IN", "OUT"])
        .annotate(hour=TruncHour("timestamp"))
        .values("hour")
        .annotate(n=Count("id"))
    )
    hours = [0] * 24
    for entry in by_hour:
        if entry["hour"]:
            hours[entry["hour"].hour] += entry["n"]

    by_type = list(
        Car.objects.filter(is_active=True)
        .values("vehicle_type")
        .annotate(n=Count("id"))
        .order_by("-n")
    )

    top_cars = list(
        EntryLog.objects.filter(timestamp__gte=start, action="IN", car__isnull=False)
        .values("car__id", "car__title")
        .annotate(n=Count("id"))
        .order_by("-n")[:10]
    )

    return JsonResponse(
        {
            "days": days,
            "by_day": [
                {
                    "day": item["day"].isoformat() if item["day"] else None,
                    "action": item["action"],
                    "count": item["n"],
                }
                for item in by_day
            ],
            "by_hour": hours,
            "by_type": by_type,
            "top_cars": top_cars,
            "totals": {
                "cars_active": Car.objects.filter(is_active=True).count(),
                "cars_inside": Car.objects.filter(is_active=True, is_inside=True).count(),
                "scans": EntryLog.objects.filter(timestamp__gte=start).count(),
                "denied": EntryLog.objects.filter(timestamp__gte=start, action="DENIED").count(),
            },
        }
    )


# ─── RFID API ─────────────────────────────────────────────────────────────


@csrf_exempt
@require_http_methods(["POST"])
def rfid_api(request: HttpRequest) -> JsonResponse:
    """Endpoint hit by `run_scanner.py` for every RFID scan event."""
    expected_token = settings.SCANNER_API_TOKEN
    if expected_token:
        provided = (
            request.headers.get("X-Api-Token")
            or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        )
        if provided != expected_token:
            return JsonResponse({"status": "error", "message": "Token nadurıs"}, status=401)

    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Nadurıs JSON"}, status=400)

    tag = (payload.get("rfid_tag") or "").strip()
    if not tag:
        return JsonResponse({"status": "error", "message": "Tag joq"}, status=400)

    try:
        result = process_scan(tag)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Scan handler crashed")
        return JsonResponse({"status": "error", "message": str(exc)}, status=500)

    return JsonResponse(
        {
            "status": result.status,
            "message": result.message,
            "action": result.action,
            "authorized": result.authorized,
        }
    )
