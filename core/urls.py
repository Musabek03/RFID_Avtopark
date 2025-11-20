from django.urls import path
from .views import DashboardView, HistoryListView, CarCreateView

urlpatterns = [
    path('', DashboardView.as_view(), name="dashboard"),
    path('history/', HistoryListView.as_view(), name="history"),
    path('add-car/', CarCreateView.as_view(), name="add_car"),
]
