# TakeYouOff ✈️📍

TakeYouOff es una aplicación web para monitoreo y soporte de planificación de vuelos: visualiza tráfico aéreo, calcula rutas optimizadas y emite alertas de voz en tiempo real. Está pensada como un prototipo extensible para integraciones de TTS (ElevenLabs) y modelos generativos (Gemini / Google Generative AI).

**Qué hace**
- **Monitorea vuelos** en una zona (mock o usando la API de OpenSky).
- **Calcula rutas optimizadas** entre origen y destino teniendo en cuenta restricciones.
- **Detecta conflictos y zonas restringidas** y genera notificaciones/alertas.
- **Genera audio de alerta** usando ElevenLabs (TTS) y lo reproduce en la interfaz web.
- **Soporta análisis IA**: integración con un microservicio de IA o con la API de Gemini directamente si está configurada.

**Qué implementamos en este repo (resumen de cambios recientes)**
- 🔊 **Arreglo de reproducción de audio (ElevenLabs)**: se detectó que el servidor generaba audio (HTTP 200) pero el frontend no lo reproducía. Se parcheó `templates/index.html` para invocar la función `playAlertAudio(...)` cuando la API devuelve `audio_alert_data` o `audio_alert_url`, permitiendo la reproducción en el navegador (sujeto a restricciones de autoplay del navegador).
- 🤖 **Integración de IA (Gemini)**: añadimos soporte flexible para análisis con Gemini:
	- Un microservicio opcional `ai_gemini_microservice/` (Flask) con endpoints `/analyze` y `/health`. Diseñado para modo `DEV_MOCK` y para usar el SDK de Google Generative AI si está disponible.
	- Llamada directa desde `app.py` al cliente de Gemini cuando `GOOGLE_API_KEY` está presente; si el SDK no está instalado o falla, `app.py` hace fallback hacia el microservicio y finalmente hacia un resumen humano legible.
- 📄 **Documentación y guía**: se añadieron `GEMINI_INTEGRATION.md` con recomendaciones de prompts y fallbacks, y el README ahora describe el proyecto y los pasos esenciales.

**Archivos relevantes **
- `app.py` — servidor principal: lógica de optimización, TTS (ElevenLabs) y la función `call_gemini_analysis()` que intenta: (1) cliente Gemini directo → (2) microservicio → (3) fallback.
- `templates/index.html` — frontend: se añadió la llamada a `playAlertAudio` tras la respuesta de `optimize-route`.
- `services/elevenlabs_service.py` (existente) — wrapper/uso del SDK de ElevenLabs.
- `ai_gemini_microservice/` — microservicio auxiliar con `app.py`, `requirements.txt`, `Dockerfile` y README (opcional, se puede ejecutar sin Docker).
- `GEMINI_INTEGRATION.md` — guía técnica para prompts, límites y estrategias de fallback.

**Variables de entorno importantes**
- `ELEVENLABS_API_KEY` — clave para generar TTS con ElevenLabs.
- `GOOGLE_API_KEY` — clave para usar Google Generative AI (Gemini) desde el SDK.
- `DEV_MOCK` — cuando está activado, muchas respuestas de IA y de vuelos se simulan para pruebas.


**Ideas / próximos pasos** ✨
- Integrar persistencia (SQLite o una DB ligera) para logs y trazas de alertas.
- Añadir autenticación y control de accesos en la UI/API.
- Mejorar experiencia de audio (pre-caching, indicación visual cuando audio no puede reproducirse por autoplay).

---

**Tecnologías usadas**
- Python 3.10+
- Flask
- ElevenLabs (`elevenlabs` Python SDK)
- Google Generative AI (`google-generativeai`)
- Requests (HTTP)
- Leaflet (mapa en frontend)
- Bootstrap (estilos)
- Chart.js (gráficos)
- OpenSky API (fuente de tráfico aéreo)
- Nominatim (geocoding)
- JavaScript, HTML, CSS
- Docker (opcional, para microservicio)
- PowerShell (scripts de inicio en Windows)
- `pip` / entornos virtuales (`venv`)