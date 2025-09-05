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
        else:
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
        else:
            msg = _log_print("WARNING",f"No se encontro la información para la canción con ID: {cancion_id}")
            logger.warning(msg)
            return None
    
    def update_porcentaje_avance(self, cancion_id, porcentaje):
        with connections['default'].cursor() as cursor:
            cursor.execute(
                """
                select * from public.spu_porcentaje_avance(%s, %s)
                """,
                [ cancion_id, porcentaje]
            )
    
    def get_porcentaje_kfn(self):
        with connections['default'].cursor()  as cursor:
            cursor.execute("select * from public.sps_porcentaje_kfn()")
            result = cursor.fetchone()
        if result:
            return result[0]
        else:
            return 80