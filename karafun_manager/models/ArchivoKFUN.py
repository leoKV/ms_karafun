from dataclasses import dataclass
from typing import Optional

@dataclass
class ArchivoKFUN:
    type: int     
    filename: str
    length_in: int
    length_out: int
    offset: int
    flags: int
    file: Optional[bytes] = None