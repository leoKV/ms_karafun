from dataclasses import dataclass

@dataclass
class Eff2:
    id: str = "2"
    in_practice: str = "1"
    enabled: str = "-1"
    locked: str = "0"
    font: str = "Arial Black*36"
    active_color: str = "#FF0000FF"
    inactive_color: str = "#FFFFFFFF"
    frame_color: str = "#000000FF"
    inactive_frame_color: str = "#000000FF"
    frame_type: str = "Frame2"
    is_fill: str = "1"
    preview: str = "0"
    fixed: str = "0"
    line_count: str = "4"
    offset_x: str = "0"
    offset_y: str = "0"
    nb_anim: str = "0"
    text_count: str = "83"