import os
import struct
from pathlib import Path
import shutil
import zipfile
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from ms_karafun import config
from concurrent.futures import ThreadPoolExecutor
from karafun_manager.repositories.cancion_repository import CancionRepository
from karafun_manager.utils.drive_manager import search_kfn, download_all_files, upload_kfn, download_k, verificar_audio
from karafun_manager.utils.audacity import open_audacity, open_carpeta, view_files
from karafun_manager.utils.karafun_studio import manipular_kfn, recrear_kfn, verificar_kfn, finalizar_karaoke
from karafun_manager.utils.print import _log_print
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
            msg = _log_print("ERROR",f"{e}")
            logger.error(msg)
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
            msg = _log_print("ERROR",f"{e}")
            logger.error(msg)
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

@csrf_exempt
def abrir_karafun(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            key = body.get('key')
            result = search_kfn(key)
            if not result.get("success") and "No hay KFN" in result.get("message", ""):
                download_all_files(key)
                return JsonResponse({"success": False, "message": "No hay KFN."})
            return JsonResponse(result)
        except Exception as e:
            msg = _log_print("ERROR",f"{e}")
            logger.error(msg)
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
                msg = _log_print("ERROR","El archivo main.mp3 es obligatorio.")
                logger.error(msg)
                return JsonResponse({'success': False, 'message': 'El archivo main.mp3 es obligatorio.'})
            datos = repo.get_song_ini(cancion_id)
            if not datos:
                msg = _log_print("ERROR","No se pudieron obtener datos de Songini.")
                logger.error(msg)
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
            if not verificar_recursos():
                msg = _log_print("WARNING","No se pudieron verificar los recursos.")
                logger.info(msg)
                return JsonResponse({'success': False, 'message': 'No se pudieron verificar los recursos.'})
            # Crear Karafun.
            kfun = KaraokeFunForm(cancion)
            result = kfun.genera_archivo_kfun()
            if result[0] == "0":  # Éxito
                # Actualizar porcentaje a 40%
                repo.update_porcentaje_avance(cancion_id=cancion_id, porcentaje=40)
                search_kfn(key)
                return JsonResponse({
                    'success': True,
                    'message': result[1]
                })
            else:  # Error en la generación
                return JsonResponse({'success': False, 'message': result[1]})
        except Exception as e:
            msg = _log_print("ERROR",f"{e}")
            logger.error(msg)
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

def verificar_recursos():
    try:
        path_fondos = config.get_path_img_fondo()
        if os.path.exists(path_fondos):
            return True
        path_resources = os.path.join(os.getcwd(), "resources")
        path_zip = os.path.join(path_resources, "resources.zip")
        path_d = Path(config.get_path_img_fondo())
        path_destino = path_d.parent
        if not os.path.exists(path_zip):
            msg = _log_print("ERROR",f"No se encontró el archivo: {path_zip}")
            logger.error(msg)
            return False
        msg = _log_print("INFO",f"Extrayendo {path_zip} a {path_destino}...")
        logger.info(msg)
        with zipfile.ZipFile(path_zip, 'r') as zip_ref:
            zip_ref.extractall(path_destino)
        shutil.rmtree(path_resources)
        msg = _log_print("INFO","Extracción completada y archivo ZIP eliminado.")
        logger.info(msg)
        return True
    except Exception as e:
        msg = _log_print("ERROR",f"Fallo al verificar/extraer recursos: {e}")
        logger.error(msg)
        return False

@csrf_exempt
def download_karaoke(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            key = body.get('key')
            drive_id = body.get('drive_id')
            tipo = body.get('tipo')
            result = download_k(key, drive_id, tipo)
            return JsonResponse(result)
        except Exception as e:
            msg = _log_print("ERROR",f"{e}")
            logger.error(msg)
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

@csrf_exempt
def delete_karaoke(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            key = body.get('key')
            tipo = body.get('tipo')
            key_dir = os.path.join(config.get_path_main(), key)
            karaoke_dir = ''
            if tipo == 1:
                karaoke_dir = 'karaoke_final'
            elif tipo == 2:
                karaoke_dir = 'ensayo'
            dest_dir = os.path.join(key_dir, karaoke_dir)
            if os.path.exists(dest_dir):
                shutil.rmtree(dest_dir)
                msg = _log_print("INFO",f"Carpeta Eliminada: {dest_dir}")
                logger.info(msg)
                result = {"success": True, "message": msg}
            else:
                msg = _log_print("WARNING",f"La carpeta no existe: {dest_dir}")
                logger.warning(msg)
                result = {"success": False, "message": msg}
            return JsonResponse(result)
        except Exception as e:
            msg = _log_print("ERROR",f"{e}")
            logger.error(msg)
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

@csrf_exempt
def abrir_audacity(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            key = body.get('key')
            result = open_audacity(key)
            return JsonResponse(result)
        except Exception as e:
            msg = _log_print("ERROR",f"{e}")
            logger.error(msg)
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

@csrf_exempt
def manipular_karafun(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            key = body.get('key')
            result = manipular_kfn(key)
            return JsonResponse(result)
        except Exception as e:
            msg = _log_print("ERROR",f"{e}")
            logger.error(msg)
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

@csrf_exempt
def recrear_karafun(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            key = body.get('key')
            archivos = body.get('archivos', [])
            if not isinstance(archivos, list):
                return JsonResponse({'success': False, 'message': 'Formato inválido: se esperaba una lista de archivos.'})
            audio = body.get('audio')
            fondo = body.get('fondo')
            opc = body.get('opc')
            result = recrear_kfn(key, archivos, audio, fondo, opc)
            return JsonResponse(result)
        except Exception as e:
            msg = _log_print("ERROR",f"{e}")
            logger.error(msg)
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

@csrf_exempt
def abrir_carpeta(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            key = body.get('key')
            result = open_carpeta(key)
            return JsonResponse(result)
        except Exception as e:
            msg = _log_print("ERROR",f"{e}")
            logger.error(msg)
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

@csrf_exempt
def ver_archivos(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            key = body.get('key')
            result = view_files(key)
            return JsonResponse(result)
        except Exception as e:
            msg = _log_print("ERROR",f"{e}")
            logger.error(msg)
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

@csrf_exempt
def delete_carpeta(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            keys = body.get('keys', [])
            if not isinstance(keys, list):
                return JsonResponse({'success': False, 'message': 'Formato inválido: se esperaba una lista de keys'})
            dir_path = Path(config.get_path_main())
            cantidad = len(keys)
            def worker(key):
                carpeta_path = dir_path / key
                if carpeta_path.exists() and carpeta_path.is_dir():
                    try:
                        shutil.rmtree(carpeta_path)
                    except Exception as e:
                        msg = _log_print("ERROR",f"key: {key} Error al eliminar: {str(e)}")
                        logger.error(msg)
                else:
                    msg = _log_print("WARNING",f"key: {key}, No encontrada.")
                    logger.warning(msg)
            with ThreadPoolExecutor(max_workers=max(cantidad, 1)) as executor:
                for key in keys:
                    executor.submit(worker, key)
            return JsonResponse({'success': True, 'message': '¡Archivo(s) Locales eliminados!'})
        except Exception as e:
            msg = _log_print("ERROR",f"{e}")
            logger.error(msg)
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

@csrf_exempt
def comprobar_audio(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            keys = body.get('keys', [])
            tipo_proceso = body.get('tipo_proceso')
            if not isinstance(keys, list):
                return JsonResponse({'success': False, 'message': 'Formato inválido: se esperaba una lista de keys'})
            cantidad = len(keys)
            resultados = []
            def worker(key):
                result = verificar_audio(key, tipo_proceso)
                return {'key': key, 'resultado': result}
            with ThreadPoolExecutor(max_workers= cantidad) as executor:
                futures = [executor.submit(worker, key) for key in keys]
                for future in futures:
                    resultados.append(future.result())
            return JsonResponse({'success': True, 'message': '¡Audios Comprobados Correctamente!','resultados':resultados})
        except Exception as e:
            msg = _log_print("ERROR",f"{e}")
            logger.error(msg)
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

@csrf_exempt
def comprobar_kfn(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            canciones = body.get('data', [])
            tipo_proceso = body.get('tipo_proceso')
            if not isinstance(canciones, list):
                return JsonResponse({'success': False, 'message': 'Formato inválido: se esperaba una lista de canciones'})
            cantidad = len(canciones)
            resultados = []
            def worker(cancion):
                key = cancion['key']
                result = verificar_kfn(key, tipo_proceso)
                return {**cancion, "resultado": result}
            with ThreadPoolExecutor(max_workers= cantidad) as executor:
                futures = [executor.submit(worker, c) for c in canciones]
                for future in futures:
                    resultados.append(future.result())
            # Filtrar solo canciones completas.
            canciones_validas = [
                {k: v for k, v in r.items() if k != "resultado"}
                for r in resultados if r["resultado"]["success"]
            ]
            msg = _log_print("INFO","Comprobación completada")
            logger.info(msg)
            return JsonResponse({
                'success': True,
                'message': 'Validación completada',
                'Cantidad': len(canciones_validas),
                'data': canciones_validas
            })
        except Exception as e:
            msg = _log_print("ERROR",f"{e}")
            logger.error(msg)
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método no permitido'})



@csrf_exempt
def terminar_canciones(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            keys = body.get('keys', [])
            if not isinstance(keys, list):
                return JsonResponse({'success': False, 'message': 'Formato inválido: se esperaba una lista de keys'})
            cantidad = len(keys)
            resultados = []
            def worker(key):
                result = finalizar_karaoke(key)
                return {'key': key, 'resultado': result}
            with ThreadPoolExecutor(max_workers= cantidad) as executor:
                futures = [executor.submit(worker, key) for key in keys]
                for future in futures:
                    resultados.append(future.result())
            return JsonResponse({'success': True, 'message': '¡Canciones Terminadas!','resultados':resultados})
        except Exception as e:
            msg = _log_print("ERROR",f"{e}")
            logger.error(msg)
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método no permitido'})