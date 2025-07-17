from dataclasses import dataclass
from typing import List, Optional
from karafun_manager.models.Eff1 import Eff1
from karafun_manager.models.Eff2 import Eff2

@dataclass
class General:
    title: str = ""
    artist: str = ""
    album: str = ""
    compose: str = ""
    year: str = ""
    track: str = ""
    general_id: str = "-1"

    copyright: str = ""
    comment: str = ""
    source: str = ""
    effect_count: str = "2"
    language_id: str = ""
    diff_men: str = "0"
    diff_women: str = "0"
    kfn_type: str = "0"
    properties: str = "24"
    karaoke_version: str = ""
    vocal_guide: str = ""
    kara_funization: str = ""
    info_screen_bmp: str = ""
    global_shift: str = "0"

    l_mark: Optional[List[str]] = None
    eff1: Optional[Eff1] = None
    eff2: Optional[Eff2] = None
    text_trak: str = ""

    def __post_init__(self):
        if self.l_mark is None:
            self.l_mark = []
