from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class Type(Enum):
    FIRST = "Seleccione tipo"
    TEXT = "text"
    INTEGER = "integer"
    BOOLEAN = "boolean"

    @classmethod
    def get_type(cls, index: int):
        try:
            return list(cls)[index]
        except IndexError:
            return cls.FIRST

    @classmethod
    def get_by_def(cls, definition: str):
        for item in cls:
            if item.value == definition:
                return item
        return cls.FIRST

@dataclass
class Caracteristica:
    id: Optional[int] = None
    nombre: Optional[str] = ""
    key: Optional[str] = ""
    valor: Optional[str] = ""
    tipo: Type = Type.FIRST
    validation: Optional[str] = ""
    visible: bool = False

    def __init__(self, key: Optional[str] = "", valor: Optional[str] = ""):
        self.key = key
        self.valor = valor
        self.id = None
        self.nombre = ""
        self.tipo = Type.FIRST
        self.validation = ""
        self.visible = False

    def get_as_object(self) -> str:
        # Simulación de Constants.COMMA y Util.defaultIfEmpty
        COMMA = ","
        def default_if_empty(value: Optional[str]) -> str:
            return value if value else ""

        return f"({str(self.id)}{COMMA}" \
               f"{default_if_empty(self.nombre)}{COMMA}" \
               f"{default_if_empty(self.valor)}{COMMA}" \
               f"{default_if_empty(self.key)}{COMMA}" \
               f"{default_if_empty(self.tipo.value)}{COMMA}" \
               f"{default_if_empty(self.validation)}{COMMA}" \
               f"{str(self.visible)})"