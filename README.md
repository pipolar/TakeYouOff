# TakeYouOff — Sky Monitoring & Route Optimization

TakeYouOff es una aplicación ligera para monitorizar tráfico aéreo en una zona (mock o usando OpenSky), calcular rutas optimizadas y generar alertas de voz mediante ElevenLabs TTS. Está pensada para uso local y desarrollo rápido; proporciona una interfaz web (Flask + Leaflet) y endpoints REST para integrar funciones de análisis y TTS.

Este README recoge requisitos, configuración y pasos prácticos para correr el proyecto en otra máquina de forma reproducible.

---

**Características principales**
- Optimización de rutas (motor heurístico local)
- Mock de vuelos para desarrollo y pruebas
- Monitoreo de conflictos entre vuelos (simulado o real)
- Generación de audio de alerta mediante ElevenLabs (TTS)
- Interfaz web interactiva con mapa (Leaflet) y paneles de análisis

---

**Requisitos**
- Sistema operativo: Windows, macOS o Linux (desarrollado en Windows)
- Python 3.10 — 3.12 (3.12 recomendado)
- Git
- Navegador moderno (Chrome, Edge, Firefox)
- Puerto: 5000 (por defecto)

Dependencias Python: ver `requirements.txt`. Destacan `flask`, `requests`, `elevenlabs==1.59.0` y librerías auxiliares.

---

**Variables de entorno (clave)**
- `ELEVENLABS_API_KEY` — (requerida para TTS) clave de ElevenLabs.
- `ELEVENLABS_VOICE_ID` — id de la voz (opcional, hay valores por defecto en el código).
- `OPENSKY_CLIENT_ID` / `OPENSKY_CLIENT_SECRET` — credenciales OpenSky (opcional).
- `DEV_MOCK` — si se establece en `1`, la aplicación usa datos mock y no requiere claves externas.

Se puede crear un archivo `.env` con estas variables para desarrollo.

Ejemplo `.env`:

```
ELEVENLABS_API_KEY=tu_api_key_aqui
ELEVENLABS_VOICE_ID=EXAVITQu4vr4xnSDxMaL
OPENSKY_CLIENT_ID=
OPENSKY_CLIENT_SECRET=
DEV_MOCK=1
```

---

Instalación y ejecución (PowerShell)

1) Clonar el repositorio:

```pwsh
git clone <repo-url> TakeYouOff
Set-Location .\TakeYouOff
```

2) Crear y activar entorno virtual (Windows PowerShell):

```pwsh
python -m venv .venv
.venv\Scripts\Activate.ps1
# Si PowerShell bloquea la ejecución: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

3) Instalar dependencias:

```pwsh
pip install --upgrade pip
pip install -r requirements.txt
```

4) Configurar variables de entorno: crea `.env` o exporta en la sesión:

```pwsh
#$env:ELEVENLABS_API_KEY = "tu_api_key"
#$env:DEV_MOCK = "0"
```

5) Ejecutar el servidor:

```pwsh
# Opción directa
python .\app.py

# Opción usando script incluido (si disponible)
.\start_server.ps1
```

6) Abrir la UI en el navegador: `http://127.0.0.1:5000/`.

---

Endpoints útiles
- `POST /api/optimize-route` — calcula ruta optimizada. Payload JSON: `origen`, `destino`, `restricciones` (opcional), `force_audio` (boolean).
- `GET /api/vuelos` — devuelve la lista de vuelos simulados o reales.
- `POST /api/conflict-analysis` — análisis de conflicto entre dos vuelos.

Consulta el código (`app.py`) para ver detalles y formatos esperados.

---

Reproducción de audio (debug)
- Los navegadores bloquean autoplay: hay una función `unlockAudio()` en la UI que debe activarse por interacción del usuario (submit de formulario o botón de monitoreo). Si no escuchas audio:
  - Haz click en la página antes de lanzar la alerta.
  - Verifica que en la respuesta JSON del endpoint `audio_alert_data` no sea `null` (es un data URL `data:audio/...` o `audio_alert_url` apuntando a `/static/audio/archivo.mp3`).
  - Revisa los logs del servidor para errores relacionados con ElevenLabs (inicialización o errores HTTP). Un log típico exitoso: `SERVERS: ElevenLabs Client Inicializado.`
  - Para depuración considera habilitar `save_to_file=True` temporalmente (el servidor guardará MP3 en `static/audio/`).

---

Desarrollo y tests
- Tests básicos incluidos: revisa `tests/` para pruebas unitarias.
- Ejecutar tests (si tienes pytest instalado):

```pwsh
pip install pytest
pytest -q
```

---

Despliegue y producción
- No uses `app.run(debug=True)` en producción. Implementa un servidor WSGI como Gunicorn/uvicorn o empaqueta con Docker.
- Asegura las claves (no las incluyas en repos públicos). Considera usar secretos del proveedor de hosting o variables de entorno protegidas.

Ejemplo Dockerfile (básico):

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
ENV FLASK_RUN_PORT=5000
EXPOSE 5000
CMD ["python", "app.py"]
```

---

Solución de problemas comunes
- Error: `ElevenLabs SDK no disponible` — instala la dependencia: `pip install elevenlabs==1.59.0`.
- Error: `Cliente ElevenLabs no inicializado` — revisa que `ELEVENLABS_API_KEY` esté definida y accesible desde el entorno donde arranca Flask.
- Problemas con OpenSky — si no hay credenciales, activa `DEV_MOCK=1` para usar datos simulados.
- Permisos de escritura en `static/audio` — asegúrate que el usuario que ejecuta el servidor pueda escribir en esa carpeta.

---

Contribuir
- Lee `CONTRIBUTING.md` para pautas de contribución.
- Usa ramas feature/bugfix y abre pull requests claros con descripción de cambios.

---

Archivo de licencia
- Este repositorio incluye `LICENSE` en la raíz; respeta sus términos al redistribuir.

---

Contacto y soporte
- Para dudas específicas sobre la integración con ElevenLabs o OpenSky, incluye en el issue:
  - Versión de Python
  - Logs relevantes (nivel INFO/ERROR)
  - `.env` (sin claves) y pasos reproducibles

---

Gracias por usar TakeYouOff. Si quieres, puedo:
- Añadir un `.env.example` automáticamente, o
- Cambiar temporalmente el endpoint para que guarde MP3s en `static/audio` y devuelva una URL (útil para debugging), o
- Ejecutar pruebas locales del endpoint `/api/optimize-route`.
# TakeYouOff

> Nota: La integración con OpenRouter fue removida del proyecto. Las llamadas a OpenRouter se han eliminado y las funciones relacionadas devuelven mensajes por defecto o usan alternativas (por ejemplo, geocoding mediante Nominatim). Si necesitas volver a integrar otro proveedor de IA, actualiza `app.py` con la nueva implementación.

> Nota: La integración con Wolfram (wolframclient / WolframKernel) también fue removida. La lógica de optimización en `app.py` ahora utiliza una implementación en Python puro. Se eliminó el script de configuración de Wolfram (`setup_wolfram.py`) y se actualizaron las plantillas y mensajes para no mencionar Wolfram.

> Nota: La integración con MongoDB fue eliminada. Cualquier código que antes persistía datos en MongoDB ha sido modificado para eliminar dependencias (`pymongo`) y ya no intenta conectarse a una base de datos. Si quieres restaurar persistencia, ofrece una alternativa (archivo local, SQLite, o volver a integrar MongoDB) y puedo implementarla.