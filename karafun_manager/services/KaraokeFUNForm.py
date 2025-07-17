import re
import struct
from datetime import datetime
from pathlib import Path
from typing import List
from karafun_manager.models.Cancion import Cancion
from karafun_manager.models.ArchivoKFUN import ArchivoKFUN
from karafun_manager.models.FormatKFUN import FormatKFUN
from karafun_manager.models.General import General
from karafun_manager.models.TagKFUN import TagKFUN
from ms_karafun import config
import logging
from karafun_manager.utils import logs
logger = logging.getLogger(__name__)

class KaraokeFunForm:
    def __init__(self, cancion: Cancion):
        self.cancion = cancion
        self.m_file = None
    
    def genera_archivo_kfun(self) -> List[str]:
        r = ["0", "¡Archivo KFN Creado con Éxito!"]
        if not self.cancion:
            r = ["1", "La canción está vacía."]
            return r
        # Crear nombre de archivo destino .kfn
        mp3_path = Path(self.cancion.path_file_mp3)
        kfn_path = mp3_path.parent / "kara_fun.kfn"
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
        return r

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

    def _get_list_archivos(self) -> List[ArchivoKFUN]:
        l = []
        base_path = Path(config.get_path_img_fondo())
        # Imagen de Fondo
        if self.cancion.path_imagen_cliente:
            img_path = base_path / self.cancion.path_imagen_cliente
        else:
            img_path = base_path / "Fondo Karaoke IA_sin_logo.jpg"
        l.append(self._get_file(img_path, 3))
        # Archivo Main MP3
        l.append(self._get_file(self.cancion.path_file_mp3, 2))
        # no_vocals.mp3 (si existe)
        mp3_path = Path(self.cancion.path_file_mp3)
        no_vocals_path = mp3_path.parent / "no_vocals.mp3"
        if no_vocals_path.exists():
            l.append(self._get_file(str(no_vocals_path), 2))
        # Archivo virtual Song.ini
        if(self.cancion.song_ini):
            ini_text = self._ajustar_songini(self.cancion.song_ini)
            length = len(ini_text.encode('utf-8'))
        else:
            general = self._define_general()
            ini_text = general
            length = len(general.encode('utf-8'))
        song_ini = ArchivoKFUN(
            type=1,
            filename="Song.ini",
            length_in=length,
            length_out=length,
            offset=0,
            flags=0,
            file=ini_text.encode('utf-8')
        )
        l.append(song_ini)
        return l
    
    def _ajustar_songini(self, song_ini: str) -> str:
        nuevo_source = f"Source=1,I,{Path(self.cancion.path_file_mp3).name}"
        if "Source=" in song_ini:
            song_ini_mod = re.sub(r"^Source=.*$", nuevo_source, song_ini, flags=re.MULTILINE)
        else:
            song_ini_mod = song_ini.replace("[General]", f"[General]\n{nuevo_source}")
        return song_ini_mod

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

    def _get_encabezado_kfun(self) -> List[TagKFUN]:
        nombre_cancion = f"1,I,{Path(self.cancion.path_file_mp3).name}"
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
    
    def _define_general(self) -> str:
        # Año actual
        current_year = datetime.now().year
        # Nombre de la canción + source
        f_mp3 = Path(self.cancion.path_file_mp3)
        nombre_cancion = f"1,I,{self._remover_acentos(f_mp3.name)}"
        # Instancia General
        g = General()
        g.artist = self.cancion.artista
        g.title = self.cancion.nombre
        g.year = str(current_year)
        g.source = nombre_cancion
        # Bloque principal [General]
        ldato = [
            "[General]",
            f"Title={g.title}",
            f"Artist={g.artist}",
            f"Album={g.album}",
            f"Composer={g.compose}",
            f"Year={g.year}",
            f"Track={g.track}",
            f"GenreID={g.general_id}",
            f"Copyright={g.copyright}",
            f"Comment={g.comment}",
            f"Source={g.source}",
            f"EffectCount={g.effect_count}",
            f"LanguageID={g.language_id}",
            f"DiffMen={g.diff_men}",
            f"DiffWomen={g.diff_women}",
            f"KFNType={g.kfn_type}",
            f"Properties={g.properties}",
            f"KaraokeVersion={g.karaoke_version}",
            f"VocalGuide={g.vocal_guide}",
            f"KaraFunization={g.kara_funization}",
            f"InfoScreenBmp={g.info_screen_bmp}",
            f"GlobalShift={g.global_shift}",
            "",
            "[Marks]",
        ]
        for i in range(9):
            ldato.append(f"Mark{i}")
        ldato.append("")
        ldato.append("[MP3Music]")
        ldato.append("NumTracks=0")
        ldato.append("")
        # Imagen de Fondo
        base_path = Path(config.get_path_img_fondo())
        if self.cancion.path_imagen_cliente:
            img_path = base_path / self.cancion.path_imagen_cliente
        else:
            img_path = base_path / "Fondo Karaoke IA_sin_logo.jpg"
        name_file_fondo = img_path
        f = Path(name_file_fondo)
        # [Eff1] Imagen de fondo
        ldato += [
            "[Eff1]",
            "ID=51",
            "InPractice=0",
            "Enabled=-1",
            "Locked=0",
            "Color=#000000",
            f"LibImage={self._remover_acentos(f.name)}",
            "ImageColor=#FFFFFFFF",
            "AlphaBlending=Opacity",
            "OffsetX=0",
            "OffsetY=0",
            "Depth=0",
            "NbAnim=0",
            "",
        ]
        # [Eff2] Efecto de texto
        ldato += [
            "[Eff2]",
            "ID=2",
            "InPractice=1",
            "Enabled=-1",
            "Locked=0",
            "Font=Arial Black*40",
            "ActiveColor=#FF0000FF",
            "InactiveColor=#FFFFFFFF",
            "FrameColor=#000000FF",
            "InactiveFrameColor=#000000FF",
            "FrameType=Frame2",
            "FrameType=1",
            "Preview=1",
            "Fixed=0",
            "LineCount=4",
            "OffsetX=0",
            "OffsetY=0",
            "NbAnim=0",
        ]
        texto = self.cancion.letra_ref_orginal or ""
        texto += "\n-"
        lineas = texto.split("\n")
        ldato.append(f"TextCount={len(lineas)}")
        for i, linea in enumerate(lineas):
            ldato.append(f"Text{i}={linea}")
        ldato.append("InSync=1")
        # Concatenar todo con saltos de línea
        general = "\n".join(ldato) + "\n"
        return general
    
    def _parse(self, font_filename: str) -> bool:
        try:
            self.m_file = open(font_filename, 'rb')
            # Leer firma de archivo
            signature = self._read_bytes(4).decode('utf-8')
            if signature != "KFNB":
                return False
            # Leer encabezado
            while True:
                signature = self._read_bytes(4).decode('utf-8')
                type_ = self._read_byte()
                len_or_value = self._read_dword()
                print(f"signature: {signature} type: {type_} len_or_value: {len_or_value}")
                if type_ == 1:
                    pass
                elif type_ == 2:
                    buf = self._read_bytes(len_or_value)
                if signature == "ENDH":
                    break
            # Leer número de archivos
            num_files = self._read_dword()
            for _ in range(num_files):
                filename_len = self._read_dword()
                filename_bytes = self._read_bytes(filename_len)
                filename = filename_bytes.decode('utf-8')
                file_type = self._read_dword()
                file_length1 = self._read_dword()
                file_offset = self._read_dword()
                file_length2 = self._read_dword()
                file_flags = self._read_dword()
                print(
                    f"File {filename}, type: {file_type}, length1: {file_length1}, "
                    f"length2: {file_length2}, offset: {file_offset}, flags: {file_flags}"
                )
            print(f"Directory ends at offset {self.m_file.tell()}")
            return True
        except Exception as e:
            logger.error("[ERROR] No se pudo analizar el archivo .kfn: %s", str(e))
            return False
    
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