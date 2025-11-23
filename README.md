# TakeYouOff — Qué hace

TakeYouOff es una aplicación para monitorizar tráfico aéreo, optimizar rutas y generar alertas de voz.

Resumen de funcionalidades:
- Monitoriza vuelos en una zona (modo mock o usando OpenSky API).
- Calcula rutas optimizadas entre origen y destino considerando restricciones.
- Detecta conflictos y zonas restringidas y genera alertas.
- Produce audio de alerta usando ElevenLabs TTS.
- Provee una interfaz web interactiva con mapa (Leaflet) y endpoints REST para integrar análisis y TTS.
---


> Nota: La integración con OpenRouter fue removida del proyecto. Las llamadas a OpenRouter se han eliminado y las funciones relacionadas devuelven mensajes por defecto o usan alternativas (por ejemplo, geocoding mediante Nominatim). Si necesitas volver a integrar otro proveedor de IA, actualiza `app.py` con la nueva implementación.

> Nota: La integración con Wolfram (wolframclient / WolframKernel) también fue removida. La lógica de optimización en `app.py` ahora utiliza una implementación en Python puro. Se eliminó el script de configuración de Wolfram (`setup_wolfram.py`) y se actualizaron las plantillas y mensajes para no mencionar Wolfram.

> Nota: La integración con MongoDB fue eliminada. Cualquier código que antes persistía datos en MongoDB ha sido modificado para eliminar dependencias (`pymongo`) y ya no intenta conectarse a una base de datos. Si quieres restaurar persistencia, ofrece una alternativa (archivo local, SQLite, o volver a integrar MongoDB) y puedo implementarla.