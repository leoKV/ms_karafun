from dataclasses import dataclass

@dataclass
class Accion:
    indice: int
    nombre: str
    terminado: bool