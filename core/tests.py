"""Tests for the core RFID parking app."""

from __future__ import annotations

import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import Car, EntryLog, format_duration
from core.services import process_scan

User = get_user_model()


class FormatDurationTests(TestCase):
    def test_minutes_only(self):
        self.assertEqual(format_duration(timedelta(minutes=5)), "5 min")

    def test_hours_minutes(self):
        self.assertEqual(format_duration(timedelta(hours=2, minutes=30)), "2 saat 30 min")

    def test_days_hours_minutes(self):
        self.assertEqual(
            format_duration(timedelta(days=1, hours=3, minutes=15)),
            "1 kún, 3 saat, 15 min",
        )

    def test_negative_clamped(self):
        self.assertEqual(format_duration(timedelta(seconds=-10)), "0 min")


class CarModelTests(TestCase):
    def test_status_label(self):
        car = Car.objects.create(title="01 A", rfid_tag="TAG-1")
        self.assertEqual(car.status_label, "Sırtta")
        car.is_inside = True
        self.assertEqual(car.status_label, "Ishinde")
        car.is_active = False
        self.assertEqual(car.status_label, "Aktiv emes")

    def test_get_duration_when_outside(self):
        car = Car.objects.create(title="01 A", rfid_tag="TAG-2")
        self.assertEqual(car.get_duration(), "—")

    def test_get_duration_when_inside(self):
        car = Car.objects.create(
            title="01 A",
            rfid_tag="TAG-3",
            is_inside=True,
            last_entry_time=timezone.now() - timedelta(minutes=10),
        )
        self.assertIn("min", car.get_duration())


@override_settings(SCAN_COOLDOWN_IN=0, SCAN_COOLDOWN_OUT=0)
class ProcessScanTests(TestCase):
    def setUp(self):
        self.car = Car.objects.create(title="01 A 123 AA", owner="Test Owner", rfid_tag="EPC-001")

    def test_unknown_tag_creates_denied_log(self):
        result = process_scan("UNKNOWN-TAG")
        self.assertEqual(result.action, EntryLog.Action.DENIED)
        self.assertFalse(result.authorized)
        self.assertEqual(EntryLog.objects.filter(action="DENIED").count(), 1)

    def test_inactive_car_is_denied(self):
        self.car.is_active = False
        self.car.save()
        result = process_scan("EPC-001")
        self.assertEqual(result.action, EntryLog.Action.DENIED)
        self.assertFalse(result.authorized)

    def test_first_scan_logs_entry(self):
        result = process_scan("EPC-001")
        self.car.refresh_from_db()
        self.assertEqual(result.action, EntryLog.Action.IN)
        self.assertTrue(self.car.is_inside)
        self.assertIsNotNone(self.car.last_entry_time)

    def test_second_scan_logs_exit_with_duration(self):
        process_scan("EPC-001")
        # bump entry time back so duration is non-zero
        self.car.refresh_from_db()
        self.car.last_entry_time = timezone.now() - timedelta(minutes=15)
        self.car.save()
        result = process_scan("EPC-001")
        self.car.refresh_from_db()
        self.assertEqual(result.action, EntryLog.Action.OUT)
        self.assertFalse(self.car.is_inside)
        out_log = EntryLog.objects.filter(action="OUT").first()
        self.assertIsNotNone(out_log.stay_duration)

    def test_empty_tag_raises(self):
        with self.assertRaises(ValueError):
            process_scan("")


class ScanCooldownTests(TestCase):
    def setUp(self):
        self.car = Car.objects.create(title="01 A", rfid_tag="EPC-cool")

    @override_settings(SCAN_COOLDOWN_IN=60, SCAN_COOLDOWN_OUT=10)
    def test_cooldown_blocks_double_scan(self):
        first = process_scan("EPC-cool")
        self.assertEqual(first.action, "IN")
        second = process_scan("EPC-cool")
        self.assertEqual(second.action, "COOLDOWN")
        self.assertFalse(second.authorized)


class RfidApiTests(TestCase):
    def setUp(self):
        self.car = Car.objects.create(title="01 A", rfid_tag="EPC-API")
        self.url = reverse("rfid_api")

    @override_settings(SCANNER_API_TOKEN="", SCAN_COOLDOWN_IN=0, SCAN_COOLDOWN_OUT=0)
    def test_post_known_tag_returns_success(self):
        resp = self.client.post(
            self.url,
            data=json.dumps({"rfid_tag": "EPC-API"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "success")
        self.assertTrue(body["authorized"])

    def test_get_method_not_allowed(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 405)

    def test_invalid_json_rejected(self):
        resp = self.client.post(self.url, data="not-json", content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_missing_tag_rejected(self):
        resp = self.client.post(self.url, data=json.dumps({}), content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    @override_settings(SCANNER_API_TOKEN="secret-123")
    def test_token_required_when_configured(self):
        resp = self.client.post(
            self.url,
            data=json.dumps({"rfid_tag": "EPC-API"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)

    @override_settings(SCANNER_API_TOKEN="secret-123", SCAN_COOLDOWN_IN=0, SCAN_COOLDOWN_OUT=0)
    def test_token_accepted_when_correct(self):
        resp = self.client.post(
            self.url,
            data=json.dumps({"rfid_tag": "EPC-API"}),
            content_type="application/json",
            HTTP_X_API_TOKEN="secret-123",
        )
        self.assertEqual(resp.status_code, 200)


class AuthGatedViewsTests(TestCase):
    def test_dashboard_redirects_anon(self):
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)

    def test_dashboard_ok_when_logged_in(self):
        User.objects.create_user("admin", password="pw-12345!")
        self.client.login(username="admin", password="pw-12345!")
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 200)

    def test_history_export_csv(self):
        User.objects.create_user("admin", password="pw-12345!")
        self.client.login(username="admin", password="pw-12345!")
        Car.objects.create(title="01 A", rfid_tag="EPC-EXP")
        process_scan("EPC-EXP")
        resp = self.client.get(reverse("history_export") + "?format=csv")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp["Content-Type"])
        self.assertIn("Sáne", resp.content.decode("utf-8"))


class CarCrudTests(TestCase):
    def setUp(self):
        User.objects.create_user("admin", password="pw-12345!")
        self.client.login(username="admin", password="pw-12345!")

    def test_create_car(self):
        resp = self.client.post(
            reverse("car_add"),
            {
                "title": "01 A 100 AA",
                "owner": "Tester",
                "phone": "",
                "rfid_tag": "EPC-NEW",
                "vehicle_type": "SEDAN",
                "color": "aq",
                "is_active": "on",
                "description": "",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Car.objects.filter(rfid_tag="EPC-NEW").exists())

    def test_edit_car(self):
        car = Car.objects.create(title="OLD", rfid_tag="EPC-EDIT")
        resp = self.client.post(
            reverse("car_edit", args=[car.pk]),
            {
                "title": "NEW",
                "owner": "",
                "phone": "",
                "rfid_tag": "EPC-EDIT",
                "vehicle_type": "TRUCK",
                "color": "",
                "is_active": "on",
                "description": "",
            },
        )
        self.assertEqual(resp.status_code, 302)
        car.refresh_from_db()
        self.assertEqual(car.title, "NEW")
        self.assertEqual(car.vehicle_type, "TRUCK")

    def test_delete_car(self):
        car = Car.objects.create(title="DEL", rfid_tag="EPC-DEL")
        resp = self.client.post(reverse("car_delete", args=[car.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Car.objects.filter(pk=car.pk).exists())


class StatisticsApiTests(TestCase):
    def setUp(self):
        User.objects.create_user("admin", password="pw-12345!")
        self.client.login(username="admin", password="pw-12345!")

    def test_statistics_api_returns_json(self):
        resp = self.client.get(reverse("statistics_api"))
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("totals", body)
        self.assertIn("by_day", body)
        self.assertIn("by_hour", body)
        self.assertEqual(len(body["by_hour"]), 24)
