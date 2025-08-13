import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from ms_karafun import config
from concurrent.futures import ThreadPoolExecutor
from karafun_manager.repositories.cancion_repository import CancionRepository
from karafun_manager.utils.drive_manager import search_kfn, download_all_files, upload_kfn
from karafun_manager.models.Cancion import Cancion
from karafun_manager.services.KaraokeFUNForm import KaraokeFunForm
import logging
from karafun_manager.utils import logs
logger = logging.getLogger(__name__)

def check_connection(request):
    return JsonResponse({'status': True})

@csrf_exempt
def sync_drive(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            keys = body.get('keys', [])
            if not isinstance(keys, list):
                return JsonResponse({'success': False, 'message': 'Formato inválido: se esperaba una lista de keys'})
            cantidad = len(keys)
            resultados = []
            def worker(key):
                result = download_all_files(key)
                return {'key': key, 'resultado': result}
            with ThreadPoolExecutor(max_workers= cantidad) as executor:
                futures = [executor.submit(worker, key) for key in keys]
                for future in futures:
                    resultados.append(future.result())
            return JsonResponse({'success': True, 'message': '¡Archivos Sincronizados Correctamente!'})
        except Exception as e:
            print(f"[EXCEPTION] {e}")
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

@csrf_exempt
def subir_karafun(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            keys = body.get('keys', [])
            if not isinstance(keys, list):
                return JsonResponse({'success': False, 'message': 'Formato inválido: se esperaba una lista de keys'})
            cantidad = len(keys)
            resultados = []
            def worker(key):
                result = upload_kfn(key)
                return {'key': key, 'resultado': result}
            with ThreadPoolExecutor(max_workers= cantidad) as executor:
                futures = [executor.submit(worker, key) for key in keys]
                for future in futures:
                    resultados.append(future.result())
            return JsonResponse({'success': True, 'message': '¡Archivo(s) KFN Subido(s) a Google Drive!'})
        except Exception as e:
            print(f"[EXCEPTION] {e}")
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

@csrf_exempt
def abrir_karafun(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            key = body.get('key')
            result = search_kfn(key)
            return JsonResponse(result)
        except Exception as e:
            print(f"[EXCEPTION] {e}")
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

@csrf_exempt
def crear_karafun(request):
    if request.method == 'POST':
        try:
            repo = CancionRepository()
            body = json.loads(request.body)
            # Propiedades.
            cancion_id = body.get('cancion_id')
            key = body.get('key')
            nombre = body.get('nombre')
            artista = body.get('artista')
            cliente = body.get('cliente')
            path_imagen_cliente = body.get('path_imagen_cliente')
            # Path a Main.
            song_dir = os.path.join(config.get_path_main(), key)
            mp3_path = os.path.join(song_dir, 'main.mp3')
            if not mp3_path:
                logger.error("[ERROR] El archivo main.mp3 es obligatorio.")
                print("[ERROR] El archivo main.mp3 es obligatorio.")
                return JsonResponse({'success': False, 'message': 'El archivo main.mp3 es obligatorio.'})
            datos = repo.get_song_ini(cancion_id)
            if not datos:
                logger.error("[ERROR] No se pudieron obtener datos de Songini.")
                print("[ERROR] No se pudieron obtener datos de Songini.")
                return JsonResponse({'success': False, 'message': 'No se pudieron obtener datos de Songini.'})
            song_ini = datos.get("songini") or "" 
            letra = datos.get("letra") or ""
            # Construir Objeto de Cancion.
            cancion = Cancion(
                id=cancion_id,
                artista=artista,
                nombre=nombre,
                cliente=cliente,
                letra_ref_orginal=letra,
                path_file_mp3=mp3_path,
                song_ini=song_ini,
                key=key,
                path_imagen_cliente=path_imagen_cliente
            )
            # Crear Karafun.
            kfun = KaraokeFunForm(cancion)
            result = kfun.genera_archivo_kfun()
            if result[0] == "0":  # Éxito
                search_kfn(key)
                return JsonResponse({
                    'success': True,
                    'message': result[1]
                })
            else:  # Error en la generación
                return JsonResponse({'success': False, 'message': result[1]})
        except Exception as e:
            print(f"[EXCEPTION] {e}")
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método no permitido'})