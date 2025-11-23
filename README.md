
## ✈️ TakeYouOff: Monitoreo y Soporte de Vuelos Impulsado por IA

TakeYouOff es una aplicación web prototipo diseñada para el **monitoreo en tiempo real, la planificación optimizada de rutas y la emisión de alertas de voz** en el tráfico aéreo. Este proyecto sirve como un *sandbox* extensible para la integración de modelos generativos (Gemini / Google Generative AI) y servicios de Texto-a-Voz (ElevenLabs).

### 🌟 Características Principales

| Característica | Descripción | Tecnologías Clave |
| :--- | :--- | :--- |
| **🗺️ Visualización de Tráfico** | Monitoreo de vuelos activos en una zona geográfica específica (usando datos simulados o la API de OpenSky). | OpenSky API, Leaflet |
| **📐 Optimización de Rutas** | Cálculo de la ruta de vuelo más eficiente entre origen y destino, considerando restricciones. | Python/Flask |
| **🚨 Alertas en Tiempo Real** | Detección de conflictos, zonas restringidas y generación inmediata de notificaciones. | Python/Flask |
| **🔊 Alertas de Voz (TTS)** | Generación de audio de alerta dinámico usando Texto-a-Voz de ElevenLabs y reproducción en la interfaz. | ElevenLabs SDK |
| **🧠 Análisis de Vuelo con IA** | Soporte flexible para análisis complejos y resúmenes de incidentes utilizando Gemini. | Google Generative AI (Gemini) |

### 🛠️ Implementaciones Recientes (v0.2.x)

Hemos enfocado las últimas actualizaciones en la robustez del audio y la flexibilidad de la integración de la IA:

* **🤖 Integración de Gemini Flexible:**
    * **Prioridad 1:** Llamada directa al cliente de Gemini (`google-generativeai` SDK) desde `app.py` si la `GOOGLE_API_KEY` está configurada.
    * **Prioridad 2 (Fallback):** Si la clave no existe o falla el SDK, la aplicación recurre a un microservicio auxiliar (`ai_gemini_microservice/`).
    * **Prioridad 3 (Fallback Final):** Si todo lo anterior falla, se genera un resumen humano legible.
* **🔊 Parche de Reproducción de Audio:** Se corrigió un error crítico en `templates/index.html`. El *frontend* ahora invoca correctamente la función `playAlertAudio(...)` al recibir `audio_alert_data` o `audio_alert_url` en la respuesta del servidor, permitiendo la reproducción de las alertas (sujeto a restricciones de *autoplay* del navegador).
* **📄 Documentación Mejorada:** Se añadió `GEMINI_INTEGRATION.md` con guías sobre prompts, fallbacks y límites. El `README` principal ahora es más descriptivo y claro.

### ⚙️ Arquitectura del Proyecto

| Archivo/Directorio | Propósito |
| :--- | :--- |
| `app.py` | Servidor principal (Flask). Contiene la lógica central de optimización, TTS y la función `call_gemini_analysis()`. |
| `templates/index.html` | Interfaz de usuario (frontend) con el mapa Leaflet, lógica de alerta y reproducción de audio. |
| `services/` | Contiene wrappers para APIs externas, como `elevenlabs_service.py`. |
| `ai_gemini_microservice/` | Microservicio opcional (Flask) que expone endpoints `/analyze` y `/health` para el análisis IA en modo *fallback*. |
| `GEMINI_INTEGRATION.md` | Guía técnica para desarrolladores sobre la integración del modelo Gemini. |

### 🔑 Configuración de Variables de Entorno

Para ejecutar el proyecto con todas las funcionalidades, son necesarias las siguientes variables de entorno:

| Variable | Descripción | Uso |
| :--- | :--- | :--- |
| `ELEVENLABS_API_KEY` | Clave para el servicio de Texto-a-Voz (TTS) de ElevenLabs. | `services/elevenlabs_service.py` |
| `GOOGLE_API_KEY` | Clave para el SDK de Google Generative AI (Gemini). | `app.py` (Llamada directa) |
| `DEV_MOCK` | Activa respuestas simuladas para vuelos y análisis IA, útil para pruebas locales sin consumir APIs. | Lógica de `app.py` |

### ✨ Próximos Pasos e Ideas

1.  **💾 Persistencia de Datos:** Integrar una base de datos ligera (ej. SQLite) para el registro de logs, trazas de alertas e historial de vuelos analizados.
2.  **🔒 Seguridad:** Implementar autenticación y control de accesos en la UI y la API principal.
3.  **🔊 Experiencia de Audio:** Mejorar la UX del audio con *pre-caching* y añadir una indicación visual clara cuando la reproducción automática es bloqueada por el navegador.

### 🌐 Tecnologías Utilizadas

* **Backend:** Python 3.10+, Flask, Requests.
* **IA/TTS:** Google Generative AI (`google-generativeai`), ElevenLabs SDK (`elevenlabs`).
* **Frontend:** JavaScript, HTML, CSS, Bootstrap, Leaflet (mapa), Chart.js (gráficos).
* **Fuentes de Datos:** OpenSky API, Nominatim (geocoding).
* **Despliegue:** Docker (opcional para microservicio).

---

¿Qué te parece? ¿Hay alguna sección que te gustaría expandir o cambiar el enfoque?
