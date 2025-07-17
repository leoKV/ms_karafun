from dataclasses import dataclass

@dataclass
class ParametroMiniatura:
    inicio_y: int
    salto_linea: int
    ancho_circulo: int
    plano_x_circulo: int
    plano_y_circulo: int
    tamano_font: int
    tamano_letra_ind: int
    nom_artista_x:int
    nom_artista_y: int
    nom_artista_tam_font: int
    join: bool

