import time
import sys

class RegistroEndpointsMiddleware:
    """
    Middleware para registrar cada solicitud HTTP procesada por Django.
    Imprime en stdout una línea por request con método, ruta, estado y tiempo ms.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        inicio = time.time()
        metodo = getattr(request, 'method', '-')
        ruta = getattr(request, 'path', '-')
        try:
            respuesta = self.get_response(request)
            estado = getattr(respuesta, 'status_code', '-')
            return respuesta
        finally:
            duracion_ms = int((time.time() - inicio) * 1000)
            linea = f"[{metodo}] {ruta} {estado} {duracion_ms}ms\n"
            try:
                sys.stdout.write(linea)
                sys.stdout.flush()
            except Exception:
                pass
