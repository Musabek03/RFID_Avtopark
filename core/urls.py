"""URL routes for the core app."""

from django.urls import path

from . import views

urlpatterns = [
    # Public web pages
    path("", views.index, name="dashboard"),
    path("history/", views.history, name="history"),
    path("history/export/", views.history_export, name="history_export"),
    path("statistics/", views.statistics, name="statistics"),
    # Vehicle CRUD
    path("cars/", views.car_list, name="car_list"),
    path("cars/add/", views.car_add, name="car_add"),
    path("cars/<int:pk>/edit/", views.car_edit, name="car_edit"),
    path("cars/<int:pk>/delete/", views.car_delete, name="car_delete"),
    # Legacy alias kept so existing scanners / bookmarks keep working.
    path("add-car/", views.car_add, name="add_car"),
    # APIs
    path("api/scan/", views.rfid_api, name="rfid_api"),
    path("api/dashboard/", views.dashboard_api, name="dashboard_api"),
    path("api/statistics/", views.statistics_api, name="statistics_api"),
]
