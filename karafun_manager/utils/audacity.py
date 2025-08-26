import os
import platform
import subprocess
from ms_karafun import config
import logging
from karafun_manager.utils import logs
logger = logging.getLogger(__name__)

def open_audacity(key: str) -> dict:
    audacity_exe = config.get_path_audacity()
    dest_dir = os.path.join(config.get_path_main(), key)
    vocals = os.path.join(dest_dir, 'vocals.mp3')
    no_vocals = os.path.join(dest_dir, 'no_vocals.mp3')
    if not os.path.exists(audacity_exe):
        msg = "Audacity no está instalado o la ruta es incorrecta."
        logger.error("[ERROR] %s", msg)
        print(f"[ERROR] {msg}")
        return {"success": False, "message": msg}
    if not os.path.exists(vocals) or not os.path.exists(no_vocals):
        msg = "No se encontraron archivos de audio."
        logger.error("[ERROR] %s", msg)
        print(f"[ERROR] {msg}")
        return {"success": False, "message": msg}
    try:
        # Crear archivo .lof
        lof_path = os.path.join(dest_dir, 'open.lof')
        with open(lof_path, "w", encoding="utf-8") as lof:
            lof.write(f'file "{vocals}"\n')
            lof.write(f'file "{no_vocals}"\n')
        # Ejecutar Audacity con el .lof
        subprocess.Popen([audacity_exe, lof_path], shell=False)
        msg = "Abriendo Audacity..."
        logger.info("[INFO] %s", msg)
        print(f"[INFO] {msg}")
        return {"success": True, "message": msg}
    except Exception as e:
        msg = f"No se pudo lanzar Audacity: {e}"
        logger.error("[ERROR] %s", msg)
        print(f"[ERROR] {msg}")
        return {"success": False, "message": msg}
    


def open_carpeta(key: str) -> dict:
    dest_dir = os.path.join(config.get_path_main(), key)
    if not os.path.exists(dest_dir):
        msg = f"No se encontro la carpeta: {dest_dir}"
        logger.error("[ERROR] %s", msg)
        print(f"[ERROR] {msg}")
        return {"success": False, "message": msg}
    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(dest_dir)
        elif system == "Darwin":
            subprocess.Popen(["open", dest_dir])
        else:  # Linux (GNOME, KDE, XFCE, etc.)
            subprocess.Popen(["xdg-open", dest_dir])
        msg = "Abriendo Carpeta..."
        logger.info("[INFO] %s", msg)
        print(f"[INFO] {msg}")
        return {"success": True, "message": msg}
    except Exception as e:
        msg = f"No se pudo abrir la carpeta: {e}"
        logger.error("[ERROR] %s", msg)
        print(f"[ERROR] {msg}")
        return {"success": False, "message": msg}