import os
import struct
from pathlib import Path
from typing import List
from karafun_manager.models.ArchivoKFUN import ArchivoKFUN
from karafun_manager.models.FormatKFUN import FormatKFUN
from karafun_manager.models.TagKFUN import TagKFUN
from ms_karafun import config
import logging
from karafun_manager.utils import logs
logger = logging.getLogger(__name__)

class KaraokeFunForm2:
    def __init__(self, song_dir, extract_dir, audio):
        self.song_dir = song_dir
        self.extract_dir = extract_dir
        self.audio = audio
        self.m_file = None

    def genera_archivo_kfun(self) -> List[str]:
        r = ["0", "¡Archivo KFN Recreado con Éxito!"]
        # Crear nombre de archivo destino .kfn
        kfn_path = os.path.join(self.song_dir, "kara_fun.kfn")
        with open(kfn_path, "wb") as f:
            self.m_file = f
            # Escribir la firma del archivo
            self._write_bytes(b"KFNB")
            # Obtener la estructura de datos KFUN
            formato_kfun: FormatKFUN = self._carga_datos()
            # Escribir encabezados
            for encabezado in formato_kfun.l_tag:
                self._write_bytes(encabezado.name.encode("utf-8"))
                self._write_byte(encabezado.type)
                if encabezado.type == 2:
                    valor_str = str(encabezado.value)
                    if encabezado.name == "FLID":
                        self._write_int(16)
                        self._write_bytes(b"\x00" * 16)
                    else:
                        valor_bytes = valor_str.encode("utf-8")
                        self._write_int(len(valor_bytes))
                        self._write_bytes(valor_bytes)
                else:
                    self._write_int(int(encabezado.value))
            # Escribir metadatos de archivos
            archivos = formato_kfun.l_archivo
            self._write_int(len(archivos))
            for archivo in archivos:
                nombre_bytes = archivo.filename.encode("utf-8")
                self._write_int(len(nombre_bytes))
                self._write_bytes(nombre_bytes)
                self._write_int(archivo.type)
                self._write_int(archivo.length_out)
                self._write_int(archivo.offset)
                self._write_int(archivo.length_in)
                self._write_int(archivo.flags)
            # Escribir contenido de cada archivo
            for archivo in archivos:
                self._write_bytes(archivo.file)
        msg = "[INFO] Archivo KFN Recreado con Éxito"
        print(msg)
        logger.info(msg)
        return r
    
    def _carga_datos(self) -> FormatKFUN:
        kfun = FormatKFUN(
            l_tag=self._get_encabezado_kfun(),
            l_archivo=[]
        )
        la = self._get_list_archivos()
        indice = 0
        for a in la:
            a.offset = indice
            indice += len(a.file)
        kfun.l_archivo = la
        return kfun
    
    def _get_encabezado_kfun(self) -> List[TagKFUN]:
        nombre_cancion = f"1,I,{self.audio}"
        text = nombre_cancion.encode('utf-8').decode('utf-8')
        l = [
            TagKFUN("DIFM", 1, 0),
            TagKFUN("DIFW", 1, 0),
            TagKFUN("GNRE", 1, -1),
            TagKFUN("SFTV", 1, 18110997),
            TagKFUN("MUSL", 1, 0),
            TagKFUN("ANME", 1, 13),
            TagKFUN("TYPE", 1, 0),
            TagKFUN("FLID", 2, "                "),
            TagKFUN("SORC", 2, self._remover_acentos(text)),
            TagKFUN("RGHT", 1, 0),
            TagKFUN("PROV", 1, 0),
            TagKFUN("IDUS", 2, ""),
            TagKFUN("ENDH", 1, -1),
        ]
        return l
    
    def _get_list_archivos(self) -> List[ArchivoKFUN]:
        l = []
        for path in Path(self.extract_dir).iterdir():
            if not path.is_file():
                continue
            ext = path.suffix.lower()
            if path.name.lower() == "song.ini":
                tipo = 1
            elif ext == ".mp3":
                tipo = 2
            elif ext in [".jpg", ".jpeg", ".png"]:
                tipo = 3
            else:
                tipo = 0
            l.append(self._get_file(str(path), tipo))
        return l
    
    def _get_file(self, path_url: str, tipo: int) -> ArchivoKFUN:
        try:
            with open(path_url, 'rb') as f:
                bytes = f.read()
        except IOError as e:
            logger.error("[ERROR] No se pudo leer el archivo en _get_file(): %s", str(e))
            bytes = b''
        filename = Path(path_url).name
        archivo = ArchivoKFUN(
            type=tipo,
            filename=self._remover_acentos(filename),
            length_in=len(bytes),
            length_out=len(bytes),
            offset=0,
            flags=0,
            file=bytes
        )
        return archivo
    
    def _read_byte(self) -> int:
        byte = self.m_file.read(1)
        if not byte:
            raise EOFError("Fin del archivo")
        return byte[0]
    
    def _read_word(self) -> int:
        b1 = self._read_byte()
        b2 = self._read_byte()
        return (b2 << 8) | b1
    
    def _read_dword(self) -> int:
        b1 = self._read_byte()
        b2 = self._read_byte()
        b3 = self._read_byte()
        b4 = self._read_byte()
        return (b4 << 24) | (b3 << 16) | (b2 << 8) | b1
    
    def _read_bytes(self, length: int) -> bytes:
        data = self.m_file.read(length)
        if data is None or len(data) != length:
            raise IOError("No se pudieron leer los bytes requeridos")
        return data
    
    def _dump_hex(self, data: bytes) -> str:
        return ' '.join(f'{b:02X}' for b in data)
    
    def _read_utf8_string(self, length: int) -> str:
        data = self._read_bytes(length)
        return data.decode('utf-8')

    def _read_utf8_string_auto(self) -> str:
        length = self._read_dword()
        return self._read_utf8_string(length)

    def _remover_acentos(self, origen: str) -> str:
        con_acento = "ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿĀāĂăĄąĆćĈĉĊċČčĎďĐđĒēĔĕĖėĘęĚěĜĝĞğĠġȑȒȓȔȕȗȘș"
        sin_acento = "AAAAAAACEEEEIIIIDNOOOOOOUUUUYBaaaaaaaceeeeiiiionoooooouuuuybyAaAaAaCcCcCcCcDdDdEeEeEeEeEeGgGgGgrRrUuuSs"
        if len(con_acento) != len(sin_acento):
            raise RuntimeError("Revise las cadenas para la sustitución de acentos, longitudes diferentes")
        ejemplares = str.maketrans(dict(zip(con_acento, sin_acento)))
        return origen.translate(ejemplares)
    
    def _write_int(self, value: int) -> bytes:
        if value < 0:
            value = (1 << 32) + value
        data = struct.pack('<I', value)
        self.m_file.write(data)
        return data
    
    def _write_bytes(self, data: bytes):
        self.m_file.write(data)

    def _write_byte(self, value: int):
        value &= 0xFF
        self.m_file.write(bytes([value]))