# Microservicio Karafun

El objetivo de este microservicio es establecer una conexión local con el aplicativo web denominado "Karaoke IA", el cual está alojado en un hosting administrado de Hostinger. El microservicio es capaz de abrir archivos Karafun, al descargarlos de Google Drive, Sincronización de Archivos Locales y crear archivos nuevos de Karafun.

## 🚀 Requisitos Previos

Antes de comenzar, asegúrate de tener instalado lo siguiente:

- Python 3.8 o superior
- pip (Gestor de paquetes de Python)
- Virtualenv (recomendado)
- Karafun Studio
- Credenciales de Google Drive

## 🛠️ Configuración del Entorno

1. **Clona el repositorio**:

   ```bash
   git clone https://github.com/leoKV/ms_karafun.git
   cd ms_karafun

2. **Agregar Credenciales**:
   Es necesario aseguarse de que las credenciales de Google Drive se encuentran presentes en la raíz del proyecto:
   
   <img width="232" height="243" alt="image" src="https://github.com/user-attachments/assets/e10e6cff-7196-4621-883d-f9fb6dc47688" />

3. **Instalar dependencias**:

   ```bash
   pip install -r requirements.txt
   
4. **Verificar conexión a base de datos en el archivo settings.py**:
   
    <img width="250" height="130" alt="image" src="https://github.com/user-attachments/assets/7a57ff6b-1082-4e62-98d0-240270f30a37" />

    <img width="639" height="294" alt="image" src="https://github.com/user-attachments/assets/aa0f4548-e8d8-4372-9c80-792010eb7c95" />
    
5. **Verificar las rutas en el archivo .env**:

    <img width="956" height="212" alt="image" src="https://github.com/user-attachments/assets/03fc3103-7144-4ba6-8b10-58e7407cef7a" />

6. **Correr el proyecto**:
   ```bash
   venv\Scripts\activate
   python manage.py runserver 127.0.0.1:5000
