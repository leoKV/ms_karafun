from dataclasses import dataclass, field
from typing import List, Optional
from karafun_manager.models.Accion import Accion
from karafun_manager.models.ParametroMiniatura import ParametroMiniatura
from karafun_manager.models.Caracteristica import Caracteristica

@dataclass
class Cancion:
    id: int = 0
    artista: str = ""
    nombre:str = ""
    is_logo:bool = False
    url:str = ""
    cliente:str = ""
    letra_orginal:str = ""
    letra_ref_orginal:str =""
    letra_transcrita:str = ""
    path_file_text:str = ""
    path_file_ref_text:str = ""
    path_file_trans_text:str = ""
    path_file_mp3:str = ""
    procentaje:str = ""
    creador:str = ""
    fecha_hora:str = ""
    song_ini:str = ""
    usuario_id:int = 0
    estado:int = 0
    estado_descripcion:str = ""
    indice:str = ""
    gratis:bool = False
    key:str = ""
    referencia:str = ""
    path_kfn:str = ""
    path_kfn_archivos:str = ""
    archivos_cargados:str = ""
    costo:str = ""
    #Alertas
    alerta_coros: bool = False
    alerta_editar_audio: bool = False
    alerta_descripcion: str = ""
    visible: int = 1
    # Imagen del Cliente
    path_imagen_cliente: str = ""
    
    l_caracteristica: List[Caracteristica] = field(default_factory=list)
    l_accion: List[Accion] = field(default_factory=list)
    l_tag: Optional[List[str]] = None
    param_miniatura: Optional[ParametroMiniatura] = None

    def __post_init__(self):
        if self.l_tag is None:
            self.l_tag = []