"""Business logic for handling RFID scan events.

The logic is extracted from `views.rfid_api` so it can be unit-tested in
isolation and reused (e.g. from management commands or background workers).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import Car, EntryLog, format_duration

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScanResult:
    """The outcome of processing one RFID scan event."""

    status: str  # "success" | "warning" | "error"
    message: str
    action: str  # IN / OUT / DENIED / COOLDOWN
    authorized: bool
    car_id: int | None = None
    log_id: int | None = None


def process_scan(rfid_tag: str, *, now=None) -> ScanResult:
    """Process a single scanned RFID tag, persisting an EntryLog row."""
    now = now or timezone.now()
    tag = (rfid_tag or "").strip()
    if not tag:
        raise ValueError("Empty RFID tag")

    car = Car.objects.filter(rfid_tag=tag).first()

    if car is None:
        log = EntryLog.objects.create(
            car=None,
            rfid_tag=tag,
            is_authorized=False,
            action=EntryLog.Action.DENIED,
            note="Biytanıs teg",
        )
        message = f"Biytanıs teg: {tag} — ruxsat joq"
        logger.info("DENIED scan tag=%s", tag)
        return ScanResult(
            status="success",
            message=message,
            action=EntryLog.Action.DENIED,
            authorized=False,
            log_id=log.id,
        )

    if not car.is_active:
        log = EntryLog.objects.create(
            car=car,
            rfid_tag=tag,
            is_authorized=False,
            action=EntryLog.Action.DENIED,
            note="Aktiv emes karta",
        )
        logger.info("DENIED inactive car=%s tag=%s", car.id, tag)
        return ScanResult(
            status="success",
            message=f"{car.title} — aktiv emes karta",
            action=EntryLog.Action.DENIED,
            authorized=False,
            car_id=car.id,
            log_id=log.id,
        )

    last_log = (
        EntryLog.objects.filter(car=car, action__in=["IN", "OUT"]).order_by("-timestamp").first()
    )
    if last_log is not None:
        min_delay = (
            settings.SCAN_COOLDOWN_OUT
            if last_log.action == EntryLog.Action.OUT
            else settings.SCAN_COOLDOWN_IN
        )
        elapsed = now - last_log.timestamp
        if elapsed < timedelta(seconds=min_delay):
            remaining = int(min_delay - elapsed.total_seconds())
            log = EntryLog.objects.create(
                car=car,
                rfid_tag=tag,
                is_authorized=False,
                action=EntryLog.Action.COOLDOWN,
                note=f"Cooldown: {remaining}s qaldı",
            )
            return ScanResult(
                status="warning",
                message=f"Júdá tez! {remaining} sek kútiń",
                action=EntryLog.Action.COOLDOWN,
                authorized=False,
                car_id=car.id,
                log_id=log.id,
            )

    duration_text = None
    if car.is_inside:
        action = EntryLog.Action.OUT
        message = f"↑ Shıǵıw: {car.title}"
        if car.last_entry_time:
            duration_text = format_duration(now - car.last_entry_time)
        car.is_inside = False
        car.last_exit_time = now
    else:
        action = EntryLog.Action.IN
        message = f"↓ Kiriw: {car.title}"
        car.is_inside = True
        car.last_entry_time = now

    car.save(update_fields=["is_inside", "last_entry_time", "last_exit_time", "updated_at"])
    log = EntryLog.objects.create(
        car=car,
        rfid_tag=tag,
        is_authorized=True,
        action=action,
        stay_duration=duration_text,
    )
    logger.info("SCAN car=%s tag=%s action=%s", car.id, tag, action)
    return ScanResult(
        status="success",
        message=message,
        action=action,
        authorized=True,
        car_id=car.id,
        log_id=log.id,
    )
