from django.urls import path
from . import views

urlpatterns = [
    path('check/', views.check_connection),
    path('abrirKarafun/', views.abrir_karafun),
    path('syncDrive/', views.sync_drive),
    path('crearKarafun/', views.crear_karafun)
]