from django.db import connections
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
            logger.warning("[WARNING] No se encontro el link para la carpeta kia_songs")
            print("[WARNING] No se encontro el link para la carpeta kia_songs")
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
            logger.warning("[WARNING] No se encontro la información para la canción con ID: %s", cancion_id)
            print(f"[WARNING] No se encontro la información para la canción con ID: {cancion_id}")
            return None