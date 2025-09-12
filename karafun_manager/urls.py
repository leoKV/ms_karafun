from django.urls import path
from . import views

urlpatterns = [
    path('check/', views.check_connection),
    path('abrirKarafun/', views.abrir_karafun),
    path('syncDrive/', views.sync_drive),
    path('crearKarafun/', views.crear_karafun),
    path('subirKarafun/', views.subir_karafun),
    path('downloadKaraoke/', views.download_karaoke),
    path('deleteKaraoke/', views.delete_karaoke),
    path('abrirAudacity/', views.abrir_audacity),
    path('manipularKarafun/', views.manipular_karafun),
    path('recrearKarafun/', views.recrear_karafun),
    path('openCarpeta/', views.abrir_carpeta),
    path('verArchivos/', views.ver_archivos),
    path('deleteCarpeta/', views.delete_carpeta),
    path('comprobarAudio/', views.comprobar_audio),
    path('validarKFN/', views.comprobar_kfn),
    path('terminarCancion/', views.terminar_canciones)
]