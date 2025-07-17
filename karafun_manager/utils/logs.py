import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
import glob
from ms_karafun import config

# Crear carpeta de logs si no existe
log_dir = config.get_path_logs()
os.makedirs(log_dir, exist_ok=True)

# Nombre base del archivo de log con fecha actual
simulated_day = datetime.now() - timedelta(days=int(os.environ.get("SIMULATED_DAYS_AGO", 0)))
log_date = simulated_day.strftime('%Y-%m-%d')

# log_date = datetime.now().strftime('%Y-%m-%d')
log_filename = f'logs_procesos.log.{log_date}'
log_path = os.path.join(log_dir, log_filename)

# Configurar el handler para rotar por tamaño (10 MB)
log_handler = RotatingFileHandler(
    filename=log_path,
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=3  # 1 actual + 4 backups = máx. 5 archivos por día
)

log_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))

# Configuración root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)

# 🧹 Limpiar logs antiguos (máx. 10 días)
def limpiar_logs_antiguos():
    archivos_logs = sorted(
        glob.glob(os.path.join(log_dir, 'logs_procesos.log.*')),
        key=os.path.getmtime
    )

    # Agrupar por fecha (sin extensiones de rotación .1, .2, etc.)
    fechas_logs = {}
    for path in archivos_logs:
        base = os.path.basename(path)
        parts = base.split('.')
        if len(parts) >= 4:
            fecha = parts[3]
            if fecha not in fechas_logs:
                fechas_logs[fecha] = []
            fechas_logs[fecha].append(path)

    # Si hay más de 10 fechas distintas, eliminar las más antiguas
    fechas_ordenadas = sorted(fechas_logs.keys())
    if len(fechas_ordenadas) > 10:
        fechas_a_eliminar = fechas_ordenadas[:len(fechas_ordenadas) - 10]
        for fecha in fechas_a_eliminar:
            for archivo in fechas_logs[fecha]:
                try:
                    os.remove(archivo)
                except Exception as e:
                    print(f"[WARN] No se pudo eliminar el archivo {archivo}: {e}")

# Ejecutar limpieza al cargar
limpiar_logs_antiguos()
