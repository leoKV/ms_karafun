from django.db import connections
from karafun_manager.utils.print import _log_print
import logging
from karafun_manager.utils import logs
logger =  logging.getLogger(__name__)

class CancionRepository:
    def get_parent_folder(self):
        with connections['default'].cursor() as cursor:
            cursor.execute("select * from public.sps_kia_folder()")
            result = cursor.fetchone()
        if result:
            return result[0]
        msg = _log_print("WARNING","No se encontro el link para la carpeta kia_songs.")
        logger.warning(msg)
        return ''

    def get_song_ini(self, cancion_id):
        with connections['default'].cursor() as cursor:
            cursor.execute(
                """
                select * from public.sps_song_ini(%s)
                """,
                [cancion_id]
            )
            result = cursor.fetchone()
        if result:
            return {
                "songini": result[0],
                "letra": result[1]
            }
        msg = _log_print("WARNING",f"No se encontro Song.ini para la canción con ID: {cancion_id}")
        logger.warning(msg)
        return None

    def get_porcentaje_kfn(self):
        with connections['default'].cursor()  as cursor:
            cursor.execute("select * from public.sps_porcentaje_kfn()")
            result = cursor.fetchone()
        if result:
            return result[0]
        return 80

    def update_porcentaje_avance(self, cancion_id, porcentaje):
        with connections['default'].cursor() as cursor:
            cursor.execute(
                """
                select * from public.spu_porcentaje_avance(%s, %s)
                """,
                [ cancion_id, porcentaje]
            )

    def update_song_ini(self, key, song_ini, render_ini):
        with connections['default'].cursor() as cursor:
            cursor.execute(
                """
                select * from public.spu_song_ini_2(%s, %s, %s)
                """,
                [key, song_ini, render_ini]
            )
            result = cursor.fetchone()
        if result and len(result[0]) > 0:
            retorno = result[0]
            if retorno[0] == '0':
                return True
            msg = _log_print("WARNING", f"Error al actualizar song_ini: {retorno[1]}")
            logger.warning(msg)
            return False
        msg = _log_print("WARNING", "La función spu_song_ini_2 no devolvió resultados.")
        logger.warning(msg)
        return False