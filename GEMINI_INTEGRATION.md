# Integración y Mejora del Análisis con Gemini

Este documento explica cómo integrar, mejorar y operar el componente de análisis IA usando *Gemini* (Google Generative AI), con ejemplos, buenas prácticas, gestión de claves, control de costes y estrategias para reducir al mínimo los errores y alucinaciones. No modifica `app.py`; presenta una ruta de integración recomendada (nuevo módulo/service) y ejemplos listos para copiar.

IMPORTANTE SOBRE SEGURIDAD
- Nunca pegues claves/API keys en repositorios públicos ni en chats. Si ya pegaste una clave accidentalmente, rótala (revócala y crea una nueva). No incluyas claves en este archivo.

Resumen ejecutivo
- Crear un servicio/ módulo independiente: `services/gemini_service.py`.
- Exponer una función estable y testeable: `call_gemini_analysis(prompt: str, *, max_tokens=800) -> str`.
- Implementar: manejo de errores, reintentos exponenciales, límites de tasa, caching de respuestas, y validación+post-procesado del output.
- Implementar fallbacks (modo DEV_MOCK o heurísticos locales) para disponibilidad.

1) Requisitos y setup
- Añade la librería oficial del cliente de Google Generative AI (según la versión disponible). Ejemplo con pip:

```pwsh
pip install google-generativeai
```

- Configura la variable de entorno con la clave API proporcionada por Google Cloud: `GOOGLE_API_KEY` o usa autenticación con cuenta de servicio (`GOOGLE_APPLICATION_CREDENTIALS`) según la biblioteca. Nunca incluyas la clave en texto plano.

2) Organización recomendada del código
- Crear un nuevo archivo `services/gemini_service.py` con la responsabilidad de:
  - construir el prompt (plantillas y few-shot)
  - llamar a la API de Gemini
  - normalizar y limpiar la respuesta
  - aplicar comprobaciones de seguridad y verificación básica
  - exponer una interfaz simple para `app.py` u otros módulos

3) Ejemplo de implementación (esqueleto)
Nota: el ejemplo es ilustrativo; adapta nombres de funciones si la librería real difiere.

```python
import os
import time
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

if not GOOGLE_API_KEY:
    logger.warning('GOOGLE_API_KEY no definida; Gemini estará deshabilitado en producción.')

def _make_system_message():
    return (
        "Eres un asistente experto en análisis de rutas aéreas. Devuelve un resumen corto "
        "seguido de puntos clave numerados. Siempre incluye una recomendación final." 
    )

def call_gemini_analysis(prompt: str, *, model: str = 'gemini-1.0', max_tokens: int = 512, temperature: float = 0.2):
    """Llama a Gemini y devuelve texto simple.

    Implementa: validación de entrada, reintentos, logging y saneamiento de salida.
    """
    if not GOOGLE_API_KEY:
        logger.info('Modo mock: retornando análisis simulado (no hay API key).')
        return 'Modo MOCK: análisis no disponible (clave faltante).'

    # Construir mensajes / prompt
    system_msg = _make_system_message()
    full_prompt = f"SYSTEM:\n{system_msg}\n\nUSER:\n{prompt}"

    # Lógica de reintentos simples
    attempts = 0
    while attempts < 3:
        attempts += 1
        try:
            # Llamada ejemplo (ajusta según SDK):
            # from google import genai
            # genai.configure(api_key=GOOGLE_API_KEY)
            # resp = genai.generate_text(model=model, prompt=full_prompt, max_output_tokens=max_tokens, temperature=temperature)
            # text = resp.text

            # Simulación hasta que añadas el cliente real
            text = '<respuesta simulada de Gemini>'

            # Post-procesado: limpiar y truncar
            text = text.strip()
            if not text:
                raise ValueError('Respuesta vacía')

            # Validación básica: limitar longitud, eliminar caracteres no imprimibles
            return text
        except Exception as e:
            logger.warning('Error llamando a Gemini (intento %d): %s', attempts, e)
            time.sleep(2 ** attempts)

    logger.error('Gemini no respondió después de reintentos.')
    return 'Error: el servicio de análisis no está disponible temporalmente.'

```

4) Prompt engineering y plantillas
- Usa plantillas con campos claros, por ejemplo:

```
SYSTEM: (instrucciones del asistente)
CONTEXT: (datos resumidos sobre la ruta)
TASK: "Resume en máximo 3 líneas y da 3 recomendaciones prácticas numeradas."
```

- Ejemplo de plantilla para el caso de rutas:

```
CONTEXT: Distancia total: {km} km. Número de restricciones: {n_restrictions}.
TASK: Evalúa riesgos y da una recomendación corta (1 línea) y 3 acciones concretas.
```

- Pistas:
  - Mantén `temperature` bajo (0.0–0.3) para respuestas más deterministas.
  - Usa `max_tokens` suficiente (300–800) para permitir explicaciones.
  - Emplea few-shot (2–3 ejemplos) si quieres respuestas en un formato exacto.

5) Control de costes y límites
- Pide solo lo necesario: reduce `max_tokens` cuando solo necesitas un resumen.
- Cachea respuestas frecuentes (por ejemplo, para rutas idénticas) con LRU caches o Redis.
- Implementa throttling y backoff exponencial para manejar límites de QPS.

6) Manejo de alucinaciones y validación
- Post-proceso: siempre valida hechos críticos con lógica determinista. Por ejemplo:
  - Si Gemini menciona distancias o tiempos, recomputa con tu propio código y compara (si difieren, marca como "verificar").
  - Si Gemini propone acciones de seguridad, añádeles una etiqueta "revisar por humano".

7) Streaming y UX
- Para respuestas largas, usa streaming (si el SDK lo soporta) y muestra progreso parcial en la UI.
- En la UI, indica claramente cuando el contenido es "sugerido por IA" y añade un botón "verificar".

8) Telemetría, logs y pruebas
- Registra métricas: latencia de la llamada, tamaño de la respuesta, tokens usados, coste estimado.
- Pruebas: crea ejemplos en `tests/gemini` con prompts conocidos y salidas esperadas o checks básicos (p.ej. formato del resultado).

9) Seguridad y privacidad
- Filtra o anonimiza datos sensibles antes de enviarlos a la API.
- Cumple con la política de datos de Google y la legislación local sobre datos personales.

10) Fallbacks y alta disponibilidad
- Prepara un fallback local: heurísticos, reglas simples o un modelo open-source local (por ejemplo, llama.cpp/llama2 mini) para degradación suave.
- Implementa un circuito breaker: si Gemini vuelve a fallar repetidamente, cambia a modo mock y notifica a los operadores.

11) Ejemplo de plantilla de prompt (formato final)

```
SYSTEM: Eres un asistente conciso y técnico, especializado en análisis de rutas aéreas.
CONTEXT:
- Distancia total: {RutaTotalKM} km
- Número de restricciones: {NumeroRestricciones}
- Origen: {PuntoOrigen}
- Destino: {PuntoDestino}
TASK: 1) Resume en 1-2 frases el riesgo principal.
2) Provee 3 acciones concretas priorizadas (máx. 50 caracteres cada una).
3) Opcional: Si el riesgo es crítico, agrega "URGENTE: revisar protocolo".
FORMAT: Devuélvelo como JSON con llaves: summary, actions (array), severity.
```

Esto permite parsear la respuesta automáticamente y reducir ambigüedades.

12) Integración con la aplicación actual (sin modificar `app.py`)
- Crea `services/gemini_service.py` con la función `call_gemini_analysis(prompt)` y prueba el módulo por separado.
- Para integrar en `app.py` más tarde, simplemente importa tu servicio y reemplaza la implementación actual de `call_gemini_analysis` por la nueva función. Si no quieres tocar `app.py`, puedes:
  - Exponer un microservicio HTTP local (por ejemplo, `localhost:6000/analyze`) que `app.py` llame (menor cambio en app, solo URL configurada), o
  - Exportar la función y hacer patch dinámico en runtime (avanzado; normalmente no recomendado para producción).

13) Checklist previo a producción
- Rotar claves y asegurarlas en secrets manager.
- Añadir límites de petición y circuit breaker.
- Añadir pruebas end-to-end con datos sanitizados.
- Revisar coste estimado por mes.

14) Recursos y enlaces útiles
- Documentación oficial de Google Generative AI (consulta la versión vigente de la librería y ejemplos de autenticación).
- Guías de prompt engineering (few-shot, chain-of-thought, system messages).

---

Si quieres, puedo:
- Generar el archivo `services/gemini_service.py` con una implementación base (no activa, requiere tu API key), o
- Crear un microservicio Docker para el análisis IA que `app.py` pueda llamar via HTTP (sin tocar `app.py`).

También: si lo deseas, revoco cualquier clave que hayas pegado aquí (no puedo revocar claves externas, pero te recuerdo rotarla inmediatamente). No incluyas claves en mensajes futuros.
