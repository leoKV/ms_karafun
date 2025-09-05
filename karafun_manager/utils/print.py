from datetime import datetime

# Imprime los mensajes en consola con un formato estándar.
def _log_print(level:str, message:str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{level}] {timestamp} {message}"
    print(formatted)
    return formatted