import os
import shutil
import subprocess
import struct
from karafun_manager.services.KaraokeFUNForm2 import KaraokeFunForm2
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

def manipular_kfn(key: str) -> dict:
    try:
        song_dir = os.path.join(config.get_path_main(), key)
        kfn_path = os.path.join(song_dir, 'kara_fun.kfn')
        if not os.path.isfile(kfn_path):
            msg = "[ERROR] No se encontro el archivo KFN"
            print(msg)
            logger.error(msg)
            return {'success': False, 'message': msg}
        extract_dir = os.path.join(song_dir, 'kfn_temp')
        with open(kfn_path, 'rb') as f:
            # 1) Firma
            if _read_exact(f, 4) != b'KFNB':
                msg = 'Archivo inválido: firma KFNB no encontrada.'
                print(msg)
                logger.error(msg)
                return {'success': False, 'message': msg}
            # 2) Tags - ENDH
            _read_tag_block(f)
            # 3) Tabla de archivos
            entries, data_base = _read_files_table(f)
            # 4) Extraer archivos
            archivos_extraidos = _extract_files(f, entries, data_base, extract_dir)
        # ---- 1.- Lista de archivos del KFN.
        archivos_kfn = [os.path.basename(p) for p in archivos_extraidos]
        # ---- 2.- Lista de archivos del proyecto.
        exts_validas = {'.mp3', '.jpg', '.png'}
        archivos_dir = [
            f for f in os.listdir(song_dir)
            if os.path.isfile(os.path.join(song_dir, f)) and os.path.splitext(f)[1].lower() in exts_validas
        ]
        # Excluir los que ya están en el KFN
        archivos_proyecto = [f for f in archivos_dir if f not in archivos_kfn]
        # Identificar archivo de audio y fondo desde Song.ini
        selected_audio = None
        selected_background = None
        song_ini = os.path.join(extract_dir, "Song.ini")
        if os.path.isfile(song_ini):
            with open(song_ini, "r", encoding="utf-8", errors="ignore") as ini:
                for line in ini:
                    line = line.strip()
                    # Audio actual (Source=..., archivo)
                    if line.startswith("Source="):
                        parts = line.split(",")
                        if len(parts) >= 3:
                            selected_audio = parts[2].strip()
                    # Fondo actual (LibImage=archivo)
                    elif line.startswith("LibImage="):
                        selected_background = line.split("=", 1)[1].strip()
        msg = 'KFN leído correctamente.'
        print(msg)
        logger.error(msg)
        return {
            'success': True,
            'message': msg,
            'archivos_kfn': archivos_kfn,
            'archivos_proyecto': archivos_proyecto,
            'selected_audio': selected_audio,
            'selected_background': selected_background
        }
    except UnicodeDecodeError as e:
        msg = f"Error de decodificación: {str(e)}"
        print(msg)
        logger.error(msg)
        return {'success': False, 'message': msg}
    except Exception as e:
        msg = f"[ERROR] {str(e)}"
        print(msg)
        logger.error(msg)
        return {'success': False, 'message': msg}

def _read_exact(f, n: int) -> bytes:
    b = f.read(n)
    if b is None or len(b) != n:
        raise IOError(f"EOF al leer {n} bytes")
    return b

def _read_u32(f) -> int:
    return struct.unpack('<I', _read_exact(f, 4))[0]

def _read_tag_block(f):
    tags = []
    while True:
        name = _read_exact(f, 4).decode('ascii')
        typ = _read_exact(f, 1)[0]
        if typ == 2:
            length = _read_u32(f)
            value_bytes = _read_exact(f, length)
            try:
                value = value_bytes.decode('utf-8')
            except UnicodeDecodeError:
                value = value_bytes
        else:
            uval = _read_u32(f)
            value = uval - (1 << 32) if (uval & 0x80000000) else uval
        tags.append({'name': name, 'type': typ, 'value': value})
        if name == 'ENDH':
            break
    return tags

def _read_files_table(f):
    num_files = _read_u32(f)
    entries = []
    for _ in range(num_files):
        name_len = _read_u32(f)
        name_bytes = _read_exact(f, name_len)
        name = name_bytes.decode('utf-8', errors='strict')
        ftype = _read_u32(f)
        length_out = _read_u32(f)
        offset = _read_u32(f)
        length_in = _read_u32(f)
        flags = _read_u32(f)
        entries.append({
            'filename': name,
            'type': ftype,
            'length_out': length_out,
            'offset': offset,
            'length_in': length_in,
            'flags': flags,
        })
    data_base = f.tell()
    return entries, data_base

def _extract_files(f, entries, data_base, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    extracted = []
    for e in entries:
        f.seek(data_base + e['offset'])
        data = _read_exact(f, e['length_in'])
        out_path = os.path.join(out_dir, e['filename'])
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'wb') as w:
            w.write(data)
        extracted.append(out_path)
    return extracted

def recrear_kfn(key:str, archivos: list[str], audio:str, fondo: str) -> dict:
    try:
        song_dir = os.path.join(config.get_path_main(), key)
        extract_dir = os.path.join(song_dir, 'kfn_temp')
        # Obtener archivos actuales en extract_dir
        archivos_actuales = os.listdir(extract_dir)
        # Archivos eliminados.
        to_delete = [f for f in archivos_actuales if f not in archivos]
        # Archivos agregados.
        to_copy = [f for f in archivos if f not in archivos_actuales]
        # 1. Eliminar archivos.
        for f in to_delete:
            ruta = os.path.join(extract_dir, f)
            if os.path.isfile(ruta):
                os.remove(ruta)
        # 2. Copiar nuevos archivos
        for f in to_copy:
            src = os.path.join(song_dir, f)
            dst = os.path.join(extract_dir, f)
            if os.path.exists(src):
                shutil.copy2(src, dst)
            else:
                msg = f"[WARNING] El archivo {f} no existe en {song_dir}"
                print(msg)
                logger.warning(msg)
        # 3. Actualizar Song.ini
        actualizar_song_ini(extract_dir, audio, fondo)
        # 4.Recrear Karafun
        kfun = KaraokeFunForm2(song_dir, extract_dir, audio)
        result = kfun.genera_archivo_kfun()
        if result[0] == "0":
            # Eliminar carpeta temporal.
            shutil.rmtree(extract_dir)
            kfn_path = os.path.join(song_dir, 'kara_fun.kfn')
            open_karafun(kfn_path)
            return {"success":True, "message":result[1]}
        else:
            return {"success":False, "message":result[1]}
    except UnicodeDecodeError as e:
        msg = f"Error de decodificación: {str(e)}"
        print(msg)
        logger.error(msg)
        return {'success': False, 'message': msg}
    except Exception as e:
        msg = f"[ERROR] {str(e)}"
        print(msg)
        logger.error(msg)
        return {'success': False, 'message': msg}
    
def actualizar_song_ini(extract_dir: str, audio: str, fondo: str):
    try:
        ini_path = os.path.join(extract_dir, "Song.ini")
        if not os.path.exists(ini_path):
            return {"success": False, "message": "Song.ini no encontrado en extract_dir"}
        with open(ini_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        nuevas_lineas = []
        for line in lines:
            if line.startswith("Source="):
                # Sobrescribir con el nuevo audio
                nuevas_lineas.append(f"Source=1,I,{audio}\n")
            elif line.startswith("LibImage="):
                # Sobrescribir con el nuevo fondo
                nuevas_lineas.append(f"LibImage={fondo}\n")
            else:
                nuevas_lineas.append(line)
        # Guardar el archivo actualizado
        with open(ini_path, "w", encoding="utf-8") as f:
            f.writelines(nuevas_lineas)
        msg = "[INFO] Song.ini actualizado."
        print(msg)
        logger.info(msg)
    except Exception as e:
        msg = f"[ERROR] Error al actualizar Song.ini: {str(e)}"
        print(msg)
        logger.error(msg)