from datetime import datetime, timezone
import io
import os
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account
from karafun_manager.repositories.cancion_repository import CancionRepository
from karafun_manager.utils.karafun_studio import open_karafun
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
                logger.info("[INFO] El archivo local %s es más reciente. Subiendo a Drive...", file_name)
                print(f"[INFO] El archivo local {file_name} es más reciente. Subiendo a Drive...")
                upload_file(service, local_path, file_id)
                return
            elif local_modified == drive_modified:
                logger.info("[INFO] El archivo %s ya está actualizado.", file_name)
                print(f"[INFO] El archivo {file_name} ya está actualizado.")
                return
            else:
                logger.info("[INFO] El archivo en Drive %s es más reciente. Reemplazando...", file_name)
                print(f"[INFO] El archivo en Drive {file_name} es más reciente. Reemplazando...")
        request = service.files().get_media(fileId=file_id) # pylint: disable=no-member
        fh = io.FileIO(local_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            done = downloader.next_chunk()
        os.utime(local_path, (drive_modified.timestamp(), drive_modified.timestamp()))
        logger.info("[INFO] Archivo %s descargado en: %s", file_name, local_path)
        print(f"[INFO] Archivo {file_name} descargado en: {local_path}")
    except Exception as e:
        logger.error("[Error] Error al descargar %s: %s", file['name'], str(e))
        print(f"[ERROR] Error al descargar {file['name']}: {e}")
        
def download_all_files(song_key: str) -> dict:
    try:
        service = authenticate_drive()
        # Paso 1: Obtener ID del folder padre (kia_songs)
        parent_folder_id = CancionRepository().get_parent_folder()
        if not parent_folder_id:
            print("[ERROR] No se pudo obtener la carpeta principal 'kia_songs'.")
            return {"success": False, "message": "No se pudo obtener la carpeta principal 'kia_songs'."}
        # Paso 2: Buscar la carpeta cuyo nombre sea igual a la key
        query = f"'{parent_folder_id}' in parents and name = '{song_key}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()  # pylint: disable=no-member
        folders = response.get('files', [])
        if not folders:
            print(f"[ERROR] No se encontró la carpeta con key {song_key}")
            return {"success": False, "message": f"No se encontró la carpeta con key '{song_key}' en Google Drive."}
        folder_id = folders[0]['id']
        # Paso 3: Obtener todos los archivos dentro de la carpeta
        query = f"'{folder_id}' in parents and trashed = false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name, modifiedTime)').execute() # pylint: disable=no-member
        files = response.get('files', [])
        if not files:
            print(f"[WARNING] No se encontraron archivos en la carpeta {song_key}")
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
        print(f"[ERROR] Error al acceder a Google Drive: {error}")
        return {"success": False, "message": "Error de conexión con Google Drive."}
    
def search_kfn(song_key: str, filename: str = "kara_fun.kfn") -> dict:
    try:
        dest_dir = os.path.join(config.get_path_main(), song_key)
        local_path = os.path.join(dest_dir, filename)
        if os.path.exists(local_path):
            logger.info("[INFO] Archivo local %s encontrado.", filename)
            print(f"[INFO] Archivo local {filename} encontrado.")
            return open_karafun(local_path)
        logger.error("[ERROR] No se encontró el archivo %s en la carpeta local.", filename)
        print(f"[ERROR] No se encontró el archivo {filename} en la carpeta local.")
        return {"success": False, "message": "No hay KFN."}
    except Exception as e:
        logger.error("[ERROR] Error al abrir el archivo KFN: %s", str(e))
        print(f"[ERROR] Error al abrir el archivo KFN: {str(e)}")
        return {"success": False, "message": str(e)}

def upload_file(service, local_path, file_id):
    try:
        media = MediaFileUpload(local_path, resumable=True)
        service.files().update(fileId=file_id, media_body=media).execute()
        logger.info("[INFO] Archivo %s actualizado en Google Drive.", os.path.basename(local_path))
        print(f"[INFO] Archivo {os.path.basename(local_path)} actualizado en Google Drive.")
    except Exception as e:
        logger.error("[ERROR] Error al subir %s: %s", os.path.basename(local_path), str(e))
        print(f"[ERROR] Error al subir {os.path.basename(local_path)}: {str(e)}")

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
            msg = f"[INFO] Archivo kara_fun.kfn subido a la carpeta {song_key}"
            logger.info(msg)
            print(msg)
        return {"success": True, "message": f"Archivo kara_fun.kfn subido para la key '{song_key}'."}
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
        print(f"[INFO] Archivo subido a Google Drive: {file['id']}")
        return file["id"]
    except HttpError as error:
        print(f"[ERROR] Error al subir archivo a Google Drive: {error}")
        return ""
