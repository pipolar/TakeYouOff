# AI Gemini Microservice

Microservicio ligero que expone un endpoint HTTP para realizar análisis con Gemini (Google Generative AI). Está diseñado para funcionar en modo `DEV_MOCK` sin claves externas, y puede habilitarse para llamadas reales si instalas el cliente oficial y defines `GOOGLE_API_KEY`.

Endpoints
- `GET /health` — devuelve `status` y `mode` (`mock` o `gemini`).
- `POST /analyze` — cuerpo JSON: `{ "prompt": "...", "max_tokens": 512, "temperature": 0.2 }`. Respuesta: `{ "analysis": "..." }` o `{ "error": ... }`.

Variables de entorno
- `GOOGLE_API_KEY` — (opcional) clave para usar Gemini.
- `DEV_MOCK` — `1` para forzar modo mock (útil en desarrollo).
- `GEMINI_MODEL` — nombre del modelo (por defecto `gemini-1.0`).
- `GEMINI_MAX_RETRIES` — reintentos para la llamada a Gemini (por defecto `3`).
- `PORT` — puerto a exponer (por defecto `6000`).

Ejecutar localmente sin Docker (mock mode)

```pwsh
# Activar venv y luego:
pip install -r ai_gemini_microservice/requirements.txt
$env:DEV_MOCK = '1'
python ai_gemini_microservice/app.py
```

Ejecutar con Docker

```pwsh
cd ai_gemini_microservice
docker build -t ai-gemini-service:latest .
docker run -p 6000:6000 -e DEV_MOCK=1 ai-gemini-service:latest
```

Habilitar Gemini real

1. Instala el cliente oficial (según la versión vigente): `pip install google-generativeai`.
2. Define `GOOGLE_API_KEY` en el entorno o monta `GOOGLE_APPLICATION_CREDENTIALS` con tu cuenta de servicio.
3. Ejecuta el contenedor con `-e GOOGLE_API_KEY=...` (o instala el cliente y ejecuta localmente).

Ejemplo de llamada desde PowerShell

```pwsh
$body = @{ prompt = "Analiza la ruta: Distancia 900 km, 2 restricciones" } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:6000/analyze -Method POST -Body $body -ContentType 'application/json'
```

Notas
- El microservicio intenta usar la librería `google.genai` si está instalada y `GOOGLE_API_KEY` está presente. Si no es así, responde en modo mock para permitir pruebas offline.
- Ajusta `requirements.txt` si quieres que el contenedor tenga el cliente oficial (ten en cuenta que puede requerir paquetes adicionales).
