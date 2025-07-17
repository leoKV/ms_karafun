import os
import subprocess
from ms_karafun import config
import logging
from karafun_manager.utils import logs
logger = logging.getLogger(__name__)

def open_karafun(file_path: str) -> dict:
    karafun_exe = config.get_path_karafun()
    if not os.path.exists(karafun_exe):
        msg = "KaraFun Studio no está instalado o la ruta es incorrecta."
        logger.error("[ERROR] %s", msg)
        print(f"[ERROR] {msg}")
        return {"success": False, "message": msg}
    try:
        subprocess.Popen([karafun_exe, file_path], shell=False)
        msg = "Abriendo Archivo Karafun."
        logger.info("[INFO] %s", msg)
        print(f"[INFO] {msg}")
        return {"success": True, "message": msg}
    except Exception as e:
        msg = f"No se pudo lanzar KaraFun Studio: {e}"
        logger.error("[ERROR] %s", msg)
        print(f"[ERROR] {msg}")
        return {"success": False, "message": msg}