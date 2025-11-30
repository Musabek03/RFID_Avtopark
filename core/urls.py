from django.urls import path
from . import views

urlpatterns = [
   
    path('', views.index, name='dashboard'),
    path('history/', views.history, name='history'),
    path('add-car/', views.add_car, name='add_car'),
    path('api/scan/', views.rfid_api, name='rfid_api'),
]