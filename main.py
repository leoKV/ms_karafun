import os
import sys
import argparse
import django
from django.core.management import call_command
from django.db import connections
from django.db.utils import OperationalError

def mostrar_banner():
    print("\n" + "="*50, flush=True)
    print("   Microservicio MS_Local   ", flush=True)
    print("="*50 + "\n", flush=True)

def validar_configuracion():
    try:
        from django.conf import settings
        
        if not hasattr(settings, 'DB_CONFIG_VALID') or not settings.DB_CONFIG_VALID:
            return False, "Configuración de base de datos inválida"
        
        if not settings.DATABASES or 'default' not in settings.DATABASES:
            return False, "No se pudo configurar la conexión a la base de datos"
        
        modo = getattr(settings, 'EXECUTION_MODE', 'desarrollo')
        if modo == 'ejecucion':
            try:
                conn = connections['default']
                # Abrir cursor valida credenciales/host/puerto
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
            except OperationalError as e:
                # Error de credenciales/host/puerto/DB
                return False, f"No se pudo conectar a la base de datos con los datos de 'config.json'. Detalle: {e}"
            except Exception as e:
                # Cualquier otro error inesperado
                return False, f"Error inesperado al probar la conexión a BD: {e}"
        
        return True, "Configuración válida"
        
    except Exception as e:
        return False, f"Error al validar configuración: {e}"

def mostrar_error_configuracion(modo_ejecucion):
    if modo_ejecucion == 'ejecucion':
        print("[ERROR] Configuración inválida. Revise 'config.json'.", flush=True)
    else:
        print("[ERROR] Configuración inválida. Revise 'ms_karafun/settings.py'.", flush=True)

def mostrar_error_detallado(error_original):
    """Muestra un mensaje de error conciso al usuario"""
    mensaje_error = str(error_original).lower()
    if 'connection' in mensaje_error or 'base de datos' in mensaje_error:
        print("[ERROR] No se pudo conectar a la BD. Revise 'config.json'.")
    else:
        print(f"[ERROR] {error_original}")

def ejecutar_servidor():
    puerto = 5000
    try:
        print(f"Servidor iniciado en: http://127.0.0.1:{puerto}", flush=True)
        call_command('runserver', f'127.0.0.1:{puerto}', '--noreload')
    except Exception as e:
        print(f"\n[ERROR] No se pudo iniciar el servidor: {e}", flush=True)
        sys.exit(1)

def iniciar_servidor():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ms_karafun.settings')
    
    try:
        django.setup()
    except Exception as e:
        print(f"Error al configurar Django: {e}", flush=True)
        return False
    
    mostrar_banner()
    
    from django.conf import settings
    modo_ejecucion = getattr(settings, 'EXECUTION_MODE', 'desarrollo')
    
    if modo_ejecucion == 'ejecucion':
        valido, mensaje = validar_configuracion()
        if not valido:
            mostrar_error_configuracion('ejecucion')
            return False
    
    ejecutar_servidor()
    return True

def main():
    # Configurar Django para obtener el modo de ejecución
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ms_karafun.settings')
    try:
        django.setup()
        from django.conf import settings
        modo_ejecucion = getattr(settings, 'EXECUTION_MODE', 'desarrollo')
    except Exception as e:
        print(f"Error al configurar Django: {e}", flush=True)
        modo_ejecucion = 'desarrollo'
    
    parser = argparse.ArgumentParser(description='Microservicio KaraFun')
    parser.add_argument('--modo', choices=['servidor', 'interfaz'], help='Modo de ejecución')
    args, _ = parser.parse_known_args()
    
    modo = args.modo if args.modo else 'interfaz'
    
    try:
        if modo == 'servidor':
            mostrar_banner()
            
            try:
                config_valida, mensaje = validar_configuracion()
                if not config_valida:
                    mostrar_error_configuracion(modo_ejecucion)
                    print(f"\nDetalles: {mensaje}", flush=True)
                    sys.exit(1)
                
                ejecutar_servidor()
            except KeyboardInterrupt:
                print("\n[INFO] Servidor detenido.", flush=True)
                sys.exit(0)
            except Exception as e:
                mostrar_error_detallado(e)
                sys.exit(1)
                
        elif modo == 'interfaz':
            from interfaz import iniciar_interfaz
            
            def iniciar_servidor_en_hilo():
                try:
                    mostrar_banner()
                    # Validar configuración antes de iniciar el servidor
                    config_valida, mensaje = validar_configuracion()
                    if not config_valida:
                        print(f"[ERROR] {mensaje}", flush=True)
                        os._exit(1)
                    
                    ejecutar_servidor()
                except Exception as e:
                    print(f"\n[ERROR] El servidor ha fallado: {e}", flush=True)
                    os._exit(1)
            
            # Iniciar el servidor en un hilo separado
            import threading
            servidor_thread = threading.Thread(target=iniciar_servidor_en_hilo, daemon=True)
            servidor_thread.start()
            
            # Pequeña pausa para asegurar que cualquier error del servidor se muestre primero
            import time
            time.sleep(1)
            
            # Iniciar la interfaz
            try:
                iniciar_interfaz()
            except Exception as e:
                print(f"\n[ERROR] No se pudo iniciar la interfaz: {e}", flush=True)
                sys.exit(1)
                
    except Exception as e:
        mostrar_error_detallado(e)
        sys.exit(1)

if __name__ == '__main__':
    main()