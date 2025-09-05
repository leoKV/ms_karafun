from datetime import datetime, timezone
import io
import os
import platform
import subprocess
from django.conf import settings
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account
from karafun_manager.repositories.cancion_repository import CancionRepository
from karafun_manager.utils.karafun_studio import open_karafun
from karafun_manager.utils.print import _log_print
from concurrent.futures import ThreadPoolExecutor
from ms_karafun import config
import logging
from karafun_manager.utils import logs
logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive"]
SERVICE_ACCOUNT_FILE = config.get_path_credentials()

# Autentica y devuelve un cliente de Google Drive API
def authenticate_drive():
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def download_file(file, dest_dir):
    try:
        service = authenticate_drive()
        file_id = file['id']
        file_name = file['name']
        if file_name in ['render_kfn_p1.mp4', 'render_kfn_p1_ensayo.mp4']:
            return
        drive_modified = datetime.strptime(file['modifiedTime'], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        local_path = os.path.join(dest_dir, file_name)
        if os.path.exists(local_path):
            local_modified = datetime.fromtimestamp(os.path.getmtime(local_path), tz=timezone.utc)
            if local_modified > drive_modified:
                msg = _log_print("INFO",f"El archivo local {file_name} es más reciente. Subiendo a Drive...")
                logger.info(msg)
                upload_file(service, local_path, file_id)
                return
            elif local_modified == drive_modified:
                msg = _log_print("INFO",f"El archivo {file_name} ya está actualizado.")
                logger.info(msg)
                return
            else:
                msg = _log_print("INFO",f"El archivo en Drive {file_name} es más reciente. Reemplazando...")
                logger.info(msg)
        request = service.files().get_media(fileId=file_id) # pylint: disable=no-member
        fh = io.FileIO(local_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            done = downloader.next_chunk()
        os.utime(local_path, (drive_modified.timestamp(), drive_modified.timestamp()))
        msg = _log_print("INFO",f"Archivo {file_name} descargado en: {local_path}")
        logger.info(msg)
    except Exception as e:
        msg = _log_print("ERROR",f"Error al descargar {file['name']}: {e}")
        logger.error(msg)

def download_all_files(song_key: str) -> dict:
    try:
        service = authenticate_drive()
        # Paso 1: Obtener ID del folder padre (kia_songs)
        parent_folder_id = CancionRepository().get_parent_folder()
        if not parent_folder_id:
            msg = _log_print("ERROR","No se pudo obtener la carpeta principal 'kia_songs'.")
            logger.error(msg)
            return {"success": False, "message": "No se pudo obtener la carpeta principal 'kia_songs'."}
        # Paso 2: Buscar la carpeta cuyo nombre sea igual a la key
        query = f"'{parent_folder_id}' in parents and name = '{song_key}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()  # pylint: disable=no-member
        folders = response.get('files', [])
        if not folders:
            msg = _log_print("ERROR",f"No se encontró la carpeta con key {song_key}")
            logger.error(msg)
            return {"success": False, "message": f"No se encontró la carpeta con key '{song_key}' en Google Drive."}
        folder_id = folders[0]['id']
        # Paso 3: Obtener todos los archivos dentro de la carpeta
        query = f"'{folder_id}' in parents and trashed = false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name, modifiedTime)').execute() # pylint: disable=no-member
        files = response.get('files', [])
        if not files:
            msg = _log_print("WARNING",f"No se encontraron archivos en la carpeta {song_key}")
            logger.warning(msg)
            return {"success": False, "message": f"No hay archivos en la carpeta con key '{song_key}'."}
        # Paso 4: Crear directorio local
        dest_dir = os.path.join(config.get_path_main(), song_key)
        os.makedirs(dest_dir, exist_ok=True)
        # Paso 5: Descargar todos los archivos
        with ThreadPoolExecutor(max_workers=10) as executor:
            for file in files:
                executor.submit(download_file, file, dest_dir)
        return {"success": True, "message": f"Archivos descargados para la key '{song_key}'."}
    except HttpError as error:
        msg = _log_print("ERROR",f"Error al acceder a Google Drive: {error}")
        logger.error(msg)
        return {"success": False, "message": "Error de conexión con Google Drive."}
    
def search_kfn(song_key: str, filename: str = "kara_fun.kfn") -> dict:
    try:
        dest_dir = os.path.join(config.get_path_main(), song_key)
        local_path = os.path.join(dest_dir, filename)
        if os.path.exists(local_path):
            msg = _log_print("INFO",f"Archivo local {filename} encontrado.")
            logger.info(msg)
            return open_karafun(local_path)
        msg = _log_print("ERROR",f"No se encontró el archivo {filename} en la carpeta local.")
        logger.error(msg)
        return {"success": False, "message": "No hay KFN."}
    except Exception as e:
        msg = _log_print("ERROR",f"Error al abrir el archivo KFN: {str(e)}")
        logger.error(msg)
        return {"success": False, "message": str(e)}
    
def upload_file(service, local_path, file_id):
    try:
        media = MediaFileUpload(local_path, resumable=True)
        service.files().update(fileId=file_id, media_body=media).execute()
        msg = _log_print("INFO",f"Archivo {os.path.basename(local_path)} actualizado en Google Drive.")
        logger.info(msg)
    except Exception as e:
        msg = _log_print("ERROR",f"Error al subir {os.path.basename(local_path)}: {str(e)}")
        logger.error(msg)

def upload_kfn(song_key: str) -> dict:
    try:
        service = authenticate_drive()
        # Paso 1: obtener carpeta padre (kia_songs)
        parent_folder_id = CancionRepository().get_parent_folder()
        if not parent_folder_id:
            return {"success": False, "message": "No se pudo obtener la carpeta principal 'kia_songs'."}
        # Paso 2: buscar carpeta de la canción
        query = f"'{parent_folder_id}' in parents and name = '{song_key}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute() # pylint: disable=no-member
        folders = response.get('files', [])
        if not folders:
            return {"success": False, "message": f"No se encontró la carpeta con key '{song_key}' en Google Drive."}
        folder_id = folders[0]['id']
        # Paso 3: ruta local del archivo
        dest_dir = os.path.join(config.get_path_main(), song_key)
        local_path = os.path.join(dest_dir, "kara_fun.kfn")
        if not os.path.exists(local_path):
            return {"success": False, "message": f"No se encontró el archivo local kara_fun.kfn para la key '{song_key}'."}
        # Paso 4: buscar archivo kara_fun.kfn en Drive
        query = f"'{folder_id}' in parents and name = 'kara_fun.kfn' and trashed = false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute() # pylint: disable=no-member
        files = response.get('files', [])
        if files:
            # Ya existe en Drive → actualizar
            file_id = files[0]['id']
            upload_file(service, local_path, file_id)
        else:
            # No existe → crear nuevo
            file_metadata = {
                'name': 'kara_fun.kfn',
                'parents': [folder_id]
            }
            media = MediaFileUpload(local_path, resumable=True)
            service.files().create(body=file_metadata, media_body=media, fields='id').execute() # pylint: disable=no-member
            msg = _log_print("INFO",f"Archivo kara_fun.kfn subido a la carpeta {song_key}")
            logger.info(msg)
        return {"success": True, "message": f"Archivo kara_fun.kfn subido para la key '{song_key}'."}
    except HttpError as error:
        return {"success": False, "message": f"Error de conexión con Google Drive: {error}"}
    except Exception as e:
        return {"success": False, "message": str(e)}

def download_k(song_key: str, drive_id:str, tipo:int) -> dict:
    try:
        key_dir = os.path.join(config.get_path_main(), song_key)
        karaoke_dir = ''
        if tipo == 1:
            karaoke_dir = 'karaoke_final'
        elif tipo == 2:
            karaoke_dir = 'ensayo'
        dest_dir = os.path.join(key_dir, karaoke_dir)
        os.makedirs(dest_dir, exist_ok=True)
        service = authenticate_drive()
        # 1. Obtener nombre del archivo en Drive
        file_info = service.files().get(fileId=drive_id, fields="name").execute() # pylint: disable=no-member
        original_name = file_info.get("name", "karaoke.mp4")
        final_path = os.path.join(dest_dir, original_name)
        if os.path.exists(final_path):
            abrir_video(final_path)
            msg = "Abriendo Archivo."
            return {"success": True, "message": msg}
        # 2. Descargar el archivo
        request = service.files().get_media(fileId=drive_id) # pylint: disable=no-member
        done = False
        fh = io.FileIO(final_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        while not done:
            done = downloader.next_chunk()
        msg = _log_print("INFO",f"Archivo Descargado en {final_path}")
        logger.info(msg)
        # 3. Abrir el archivo en el reproductor predeterminado
        abrir_video(final_path)
        msg = "Archivo Descargado."
        return {"success": True, "message": msg}
    except Exception as e:
        msg = _log_print("ERROR",f"Error al descargar Karaoke: {str(e)}")
        logger.error(msg)
        return {"success": False, "message": str(e)}
    
def abrir_video(final_path):
    sistema = platform.system()
    try:
        if sistema == "Windows":
            os.startfile(final_path)
        elif sistema == "Darwin":
            subprocess.run(["open", final_path])
        else:
            subprocess.run(["xdg-open", final_path])
        msg = _log_print("INFO",f"Reproduciendo: {final_path}")
        logger.info(msg)
    except Exception as e:
        msg = _log_print("ERROR",f"No se pudo reproducir el video: {e}")
        logger.error(msg)

def verificar_audio(song_key: str, tipo_proceso:int) -> dict:
    try:
        service = authenticate_drive()
        # Paso 1: obtener carpeta padre (kia_songs)
        parent_folder_id = CancionRepository().get_parent_folder()
        if not parent_folder_id:
            return {"success": False, "message": "No se pudo obtener la carpeta principal 'kia_songs'."}
        # Paso 2: buscar carpeta de la canción
        query = f"'{parent_folder_id}' in parents and name = '{song_key}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute() # pylint: disable=no-member
        folders = response.get('files', [])
        if not folders:
            return {"success": False, "message": f"No se encontró la carpeta con key '{song_key}' en Google Drive."}
        folder_id = folders[0]['id']
        # Paso 3: definir archivos esperados.
        expected_files = []
        if tipo_proceso == 6:
            expected_files = ["sin_voz.mp3", "no_vocals.mp3"]
        elif tipo_proceso == 8:
            expected_files = ["con_voz.mp3", "main.mp3"]
        # Paso 4: listar archivos dentro de la carpeta
        query_files = f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed = false"
        files_response = service.files().list(q=query_files, spaces='drive', fields='files(id, name)').execute() # pylint: disable=no-member
        files = files_response.get("files", [])
        found_files = [f["name"] for f in files]
        # Paso 5: verificar si alguno de los archivos existe.
        matched_files = [f for f in expected_files if f in found_files]
        if matched_files:
            return {"success": True, "message": f"Se encontraron los archivos requeridos en: {song_key}",
            }
        else:
            return {
                "success": False,
                "message": f"No se encontraron archivos clave en: {song_key}",
                "expected": expected_files
            }
    except HttpError as error:
        return {"success": False, "message": f"Error de conexión con Google Drive: {error}"}
    except Exception as e:
        return {"success": False, "message": str(e)}

# PRUEBAS
def upload_file_to_folder(file_path: str, folder_id: str, filename: str = None) -> str:
    try:
        service = authenticate_drive()
        file_metadata = {
            "name": filename or os.path.basename(file_path),
            "parents": [folder_id]
        }
        media = MediaFileUpload(file_path, resumable=True)
        file = service.files().create( # pylint: disable=no-member
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()
        msg = _log_print("INFO",f"Archivo subido a Google Drive: {file['id']}")
        logger.info(msg)
        return file["id"]
    except HttpError as error:
        msg = _log_print("ERROR",f"Error al subir archivo a Google Drive: {error}")
        logger.error(msg)
        return ""