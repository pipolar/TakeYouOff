from flask import Flask, jsonify, render_template
import requests
import time
import os
import logging
from flask import Flask, jsonify, render_template, request
from wolframclient.evaluation import WolframLanguageSession
from wolframclient.language import wl

import os
import requests
import random
import json
import logging
import time
import re
import uuid
from threading import Lock
from pathlib import Path

try:
    from flask_cors import CORS
    _HAS_CORS = True
except Exception:
    _HAS_CORS = False

from elevenlabs import ElevenLabs
import base64


from google import genai


app = Flask(
    __name__,
    template_folder=str(Path(__file__).resolve().parent / 'templates'),
    static_folder=str(Path(__file__).resolve().parent / 'static'),
    static_url_path='/static'
)

# Crear carpeta de audios si no existe
AUDIO_FOLDER = Path('static/audio')
AUDIO_FOLDER.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno desde un archivo .env (si existe)
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info(".env cargado (si estaba presente).")
except Exception:
    logger.debug("python-dotenv no está disponible; usando variables de entorno del sistema.")


# A. Wolfram Kernel Path (La ruta que encontraste y te funcionó)
KERNEL_PATH = os.environ.get("WOLFRAM_KERNEL_PATH", r"C:\Program Files\Wolfram Research\Wolfram\14.3\WolframKernel.exe")

# B. APIs Externas (Se recuperan de las variables de entorno)
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
# Leer la clave de ElevenLabs correctamente desde la variable de entorno
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")

# C. Configuración de OpenRouter
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Modo de desarrollo: si se activa, el endpoint devuelve rutas mock sin necesitar Wolfram
DEV_MOCK = os.environ.get("DEV_MOCK", "0") == "1"

# OpenSky credentials (opcional)
OPENSKY_CLIENT_ID = os.environ.get("OPENSKY_CLIENT_ID")
OPENSKY_CLIENT_SECRET = os.environ.get("OPENSKY_CLIENT_SECRET")


# ===================================================================
# 2. CONEXIÓN AL MOTOR DE WOLFRAM
# ===================================================================

# ===================================================================
# 2. CONEXIÓN AL MOTOR DE WOLFRAM (usando implementación Python puro)
# ===================================================================

from math import radians, cos, sin, asin, sqrt

def haversine_distance(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = 6371 * c
    return km


def find_shortest_tour(points):
    if not points or len(points) <= 1:
        return [0, points]
    n = len(points)
    tour = [0]
    unvisited = set(range(1, n))
    while unvisited:
        current = tour[-1]
        nearest = min(unvisited, key=lambda j: haversine_distance(points[current][0], points[current][1], points[j][0], points[j][1]))
        tour.append(nearest)
        unvisited.remove(nearest)
    total_distance = 0
    for i in range(len(tour) - 1):
        current = tour[i]
        next_point = tour[i + 1]
        total_distance += haversine_distance(points[current][0], points[current][1], points[next_point][0], points[next_point][1])
    improved = True
    iterations = 0
    max_iterations = 100
    while improved and iterations < max_iterations:
        improved = False
        iterations += 1
        for i in range(n - 1):
            for j in range(i + 2, n):
                if j - i == 1:
                    continue
                curr_dist = (
                    haversine_distance(points[tour[i]][0], points[tour[i]][1], points[tour[i+1]][0], points[tour[i+1]][1]) +
                    haversine_distance(points[tour[j]][0], points[tour[j]][1], points[tour[(j+1) % n]][0], points[tour[(j+1) % n]][1])
                )
                new_dist = (
                    haversine_distance(points[tour[i]][0], points[tour[i]][1], points[tour[j]][0], points[tour[j]][1]) +
                    haversine_distance(points[tour[i+1]][0], points[tour[i+1]][1], points[tour[(j+1) % n]][0], points[tour[(j+1) % n]][1])
                )
                if new_dist < curr_dist:
                    tour[i+1:j+1] = reversed(tour[i+1:j+1])
                    total_distance = total_distance - curr_dist + new_dist
                    improved = True
                    break
            if improved:
                break
    ruta_optimizada = [points[i] for i in tour]
    total_distance = 0
    for i in range(len(tour) - 1):
        a = tour[i]
        b = tour[i + 1]
        total_distance += haversine_distance(points[a][0], points[a][1], points[b][0], points[b][1])
    return [total_distance, ruta_optimizada]


def optimize_route_wolfram(origen, destino, restricciones):
    try:
        puntos_de_control = [origen] + restricciones + [destino]
        logger.info("Calculando ruta óptima para %d puntos", len(puntos_de_control))
        distancia_total, ruta_final = find_shortest_tour(puntos_de_control)
        logger.info("Ruta calculada: %.2f km", distancia_total)
        return {
            "Status": "Optimizado con Éxito",
            "RutaTotalKM": round(distancia_total, 2),
            "RutaOptimizada": ruta_final,
            "Mensaje": "Ruta calculada con éxito. Listo para el análisis de IA."
        }
    except Exception as e:
        logger.error("ERROR calculando ruta: %s", e)
        return None


# ===================================================================
# 3. SISTEMA DE MONITOREO OPENSKY (Simulador + API Real)
# ===================================================================

class FlightMonitor:
    def __init__(self):
        self.flights = []
        self.conflict_zones = [
            {"lat": 19.5, "lon": -99.5, "radius": 15, "name": "CDMX Centro"},
            {"lat": 19.4, "lon": -99.3, "radius": 10, "name": "Zona Este"}
        ]
        self.known_conflicts = set()
        self._generate_mock_flights()
    def _generate_mock_flights(self):
        self.flights = [
            {"icao24": "a0a1b2c3", "callsign": "AM456", "lat": 19.45, "lon": -99.25, "alt": 2500, "velocity": 450, "heading": 90, "type": "pasajero", "origin": "BENITO JUÁREZ", "destination": "QUERÉTARO"},
            {"icao24": "d4e5f6g7", "callsign": "AM789", "lat": 19.55, "lon": -99.35, "alt": 3000, "velocity": 420, "heading": 180, "type": "carga", "origin": "CDMX", "destination": "GUADALAJARA"},
            {"icao24": "h8i9j0k1", "callsign": "AM123", "lat": 19.48, "lon": -99.28, "alt": 2800, "velocity": 410, "heading": 270, "type": "pasajero", "origin": "TLAXCALA", "destination": "CDMX"},
            {"icao24": "l2m3n4o5", "callsign": "CARGO-01", "lat": 19.52, "lon": -99.50, "alt": 3500, "velocity": 480, "heading": 45, "type": "carga", "origin": "CDMX", "destination": "TOLUCA"}
        ]
    def fetch_opensky_data(self):
        try:
            bounds = os.environ.get("OPENSKY_BOUNDS", "18.0,-100.0,21.0,-98.0").split(",")
            if len(bounds) == 4:
                lat_min = float(bounds[0]); lon_min = float(bounds[1]); lat_max = float(bounds[2]); lon_max = float(bounds[3])
            else:
                lat_min, lon_min, lat_max, lon_max = 18.0, -100.0, 21.0, -98.0
            if os.environ.get("OPENSKY_CLIENT_ID") and os.environ.get("OPENSKY_CLIENT_SECRET"):
                try:
                    import importlib
                    import importlib.util
                    spec = importlib.util.find_spec("services.opensky_api")
                    if spec is not None:
                        mod = importlib.import_module("services.opensky_api")
                        OpenSkyApi = getattr(mod, "OpenSkyApi", None)
                        if OpenSkyApi:
                            client = OpenSkyApi(username=os.environ.get("OPENSKY_CLIENT_ID"), password=os.environ.get("OPENSKY_CLIENT_SECRET"))
                            states_obj = client.get_states(time_secs=0, bbox=(lat_min, lat_max, lon_min, lon_max))
                            flights = []
                            if states_obj and getattr(states_obj, 'states', None):
                                for sv in states_obj.states:
                                    try:
                                        lat = getattr(sv, 'latitude', None)
                                        lon = getattr(sv, 'longitude', None)
                                        alt = getattr(sv, 'geo_altitude', None) or getattr(sv, 'baro_altitude', None)
                                        velocity = getattr(sv, 'velocity', None)
                                        flights.append({"icao24": getattr(sv, 'icao24', None), "callsign": getattr(sv, 'callsign', None), "lat": lat, "lon": lon, "alt": alt, "velocity": velocity, "heading": getattr(sv, 'true_track', None), "type": "desconocido", "origin": getattr(sv, 'origin_country', None), "destination": None})
                                    except Exception:
                                        continue
                            if flights:
                                self.flights = flights
                                logger.info("OpenSky (client) fetched %d flights", len(self.flights))
                                return self.flights
                        else:
                            logger.warning("OpenSky client class 'OpenSkyApi' not found in module 'services.opensky_api'.")
                    else:
                        logger.info("services.opensky_api not installed; skipping client fetch.")
                except Exception as e:
                    logger.warning("OpenSky real fetch failed (client), will try HTTP endpoint fallback: %s", e)
            try:
                http_flights = obtener_vuelos_opensky(lat_min, lon_min, lat_max, lon_max)
                if http_flights:
                    self.flights = http_flights
                    logger.info("OpenSky (HTTP) fetched %d flights", len(self.flights))
                    return self.flights
            except Exception as e:
                logger.warning("OpenSky HTTP fetch failed: %s", e)
            for flight in self.flights:
                flight["lat"] += random.uniform(-0.02, 0.02)
                flight["lon"] += random.uniform(-0.02, 0.02)
                try:
                    flight["alt"] = (flight.get("alt") or 3000) + random.randint(-100, 100)
                except Exception:
                    flight["alt"] = flight.get("alt", 3000)
            logger.info(f"Monitoreo (mock): {len(self.flights)} vuelos activos en CDMX")
            return self.flights
        except Exception as e:
            logger.error("Error fetching OpenSky (general): %s", e)
            return []
    def detect_conflicts(self):
        conflicts = []
        alerts = []
        for i in range(len(self.flights)):
            for j in range(i + 1, len(self.flights)):
                f1, f2 = self.flights[i], self.flights[j]
                # Skip if coordinates are missing
                lat1 = f1.get('lat')
                lon1 = f1.get('lon')
                lat2 = f2.get('lat')
                lon2 = f2.get('lon')
                if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
                    continue
                try:
                    dist_horizontal = haversine_distance(lat1, lon1, lat2, lon2)
                except Exception:
                    continue
                # Use a safe default altitude when missing (meters)
                alt1 = f1.get('alt') if f1.get('alt') is not None else 3000
                alt2 = f2.get('alt') if f2.get('alt') is not None else 3000
                try:
                    dist_vertical = abs(float(alt1) - float(alt2)) / 1000.0
                except Exception:
                    dist_vertical = 0.0
                dist_3d = (dist_horizontal**2 + dist_vertical**2)**0.5
                if dist_3d < 5:
                    # Build a stable conflict id even if icao24 missing
                    icao1 = f1.get('icao24') or f1.get('callsign') or str(i)
                    icao2 = f2.get('icao24') or f2.get('callsign') or str(j)
                    conflict_id = f"{icao1}-{icao2}"
                    if conflict_id not in self.known_conflicts:
                        self.known_conflicts.add(conflict_id)
                        conflicts.append({"type": "proximitad", "flight1": f1.get('callsign'), "flight2": f2.get('callsign'), "distance_km": round(dist_3d, 2), "severity": "crítica" if dist_3d < 2 else "alta"})
                        alerts.append({"title": "⚠️ Conflicto de Proximidad", "message": f"{f1.get('callsign')} y {f2.get('callsign')} a {dist_3d:.1f} km", "severity": "danger"})
        for flight in self.flights:
            # Skip flights without coordinates
            f_lat = flight.get('lat')
            f_lon = flight.get('lon')
            if f_lat is None or f_lon is None:
                continue
            for zone in self.conflict_zones:
                try:
                    dist = haversine_distance(f_lat, f_lon, zone['lat'], zone['lon'])
                except Exception:
                    continue
                if dist < zone['radius']:
                    zone_id = f"{flight.get('icao24') or flight.get('callsign')}-{zone['name']}"
                    if zone_id not in self.known_conflicts:
                        self.known_conflicts.add(zone_id)
                        severity_level = "crítica" if dist < zone['radius']/2 else "alta"
                        alerts.append({"title": f"⚡ Zona Restringida: {zone['name']}", "message": f"{flight.get('callsign')} en zona de restricción", "severity": "warning" if severity_level == "alta" else "danger"})
        return conflicts, alerts


# Instancia global del monitor
flight_monitor = FlightMonitor()


# -----------------------------
# OpenSky HTTP helper (from app_min.py)
# -----------------------------
_opensky_token_cache = {"access_token": None, "expires_at": 0}

def obtener_token_opensky():
    if not OPENSKY_CLIENT_ID or not OPENSKY_CLIENT_SECRET:
        return None
    if _opensky_token_cache["access_token"] and _opensky_token_cache["expires_at"] > time.time():
        return _opensky_token_cache["access_token"]
    try:
        url = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
        data = {"grant_type": "client_credentials", "client_id": OPENSKY_CLIENT_ID, "client_secret": OPENSKY_CLIENT_SECRET}
        r = requests.post(url, data=data, timeout=10)
        r.raise_for_status()
        j = r.json()
        _opensky_token_cache["access_token"] = j.get("access_token")
        _opensky_token_cache["expires_at"] = time.time() + j.get("expires_in", 1800)
        return _opensky_token_cache["access_token"]
    except Exception as e:
        logger.warning("OpenSky token request failed: %s", e)
        return None


def obtener_vuelos_opensky(lamin, lomin, lamax, lomax):
    url = "https://opensky-network.org/api/states/all"
    token = obtener_token_opensky()
    headers = {"User-Agent": "TakeYouOff/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    params = {"lamin": lamin, "lomin": lomin, "lamax": lamax, "lomax": lomax}
    r = requests.get(url, headers=headers, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    vuelos = []
    now_ts = int(time.time())
    for s in data.get("states", []):
        lat = s[6] if len(s) > 6 else None
        lon = s[5] if len(s) > 5 else None
        # Require coordinates
        if lat is None or lon is None:
            continue
        # Coerce to float and skip if invalid
        try:
            lat = float(lat)
            lon = float(lon)
        except Exception:
            continue
        # Altitude (may be None)
        alt = None
        if len(s) > 7 and s[7] is not None:
            try:
                alt = float(s[7])
            except Exception:
                alt = None
        # Velocity
        velocity = None
        if len(s) > 9 and s[9] is not None:
            try:
                velocity = float(s[9])
            except Exception:
                velocity = None
        # Heading / true_track
        heading = None
        if len(s) > 10 and s[10] is not None:
            try:
                heading = float(s[10])
            except Exception:
                heading = None
        callsign = (s[1] or "").strip() if len(s) > 1 else ""
        vuelos.append({
            "icao24": s[0] if len(s) > 0 else None,
            "callsign": callsign,
            "origin_country": s[2] if len(s) > 2 else None,
            "lat": lat,
            "lon": lon,
            "alt": alt,
            "velocity": velocity,
            "heading": heading,
            "type": "desconocido",
            "destination": None,
            "fetched_at": now_ts
        })
    return vuelos



# ===================================================================
# 4. CONEXIÓN AL CLIENTE ELEVENLABS
# ===================================================================

ELEVENLABS_CLIENT = None
if ELEVENLABS_API_KEY:
    try:
        ELEVENLABS_CLIENT = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        logger.info("SERVERS: ElevenLabs Client Inicializado.")
    except Exception as e:
        logger.error("ERROR: Falló al inicializar ElevenLabs. %s", e)

if _HAS_CORS:
    CORS(app)
    logger.info("CORS habilitado (flask_cors detected).")


def call_gemini_analysis(route_data_str):
    if not OPENROUTER_API_KEY:
        return "OpenRouter Desconectado. (Clave API no configurada)"
    if isinstance(route_data_str, dict):
        prompt_text = f"Eres un experto en seguridad aérea y optimización de rutas. Analiza este escenario de tráfico aéreo:\n\n{json.dumps(route_data_str, indent=2)}\n\nProporciona:\n1. EVALUACIÓN DE RIESGO (Crítico/Alto/Medio/Bajo)\n2. FACTORES CLAVE que afectan la seguridad\n3. RECOMENDACIONES ACCIONABLES para el controlador\n4. CONFIANZA DEL MODELO (0-100%)"
    else:
        prompt_text = (
            f"Eres un analista de seguridad aérea y modelador de riesgos. Analiza los siguientes datos numéricos de cálculo de ruta geodésica (Wolfram): {route_data_str}. "
            "Tu tarea es generar un informe contextual y accionable. "
            "1. RESUMEN CRÍTICO (Tono urgente, máximo 3 oraciones): Identifica la principal causa de riesgo (ej: 'ruta excesivamente larga' o 'múltiples restricciones'). "
            "2. RECOMENDACIONES DE MITIGACIÓN (Lista de 3 puntos): Ofrece acciones concretas y verificables para el piloto que minimicen el riesgo. "
            "3. CONFIANZA DEL ANÁLISIS: % de confianza en la recomendación basado en datos disponibles. "
            "Formatea tu respuesta en un solo bloque de texto claro y profesional."
        )
    try:
        headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": "google/gemini-2.5-pro", "messages": [{"role": "user", "content": prompt_text}]}
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        try:
            return data['choices'][0]['message']['content']
        except Exception:
            logger.error("Respuesta inesperada de OpenRouter: %s", data)
            return "Error en la llamada a OpenRouter: respuesta inesperada."
    except requests.exceptions.RequestException as e:
        logger.error("Error en la llamada a OpenRouter: %s", e)
        return "Error en la llamada a OpenRouter: No se pudo obtener el análisis."


def call_geocode_address(address):
    if not OPENROUTER_API_KEY:
        logger.warning("Geocoding: OpenRouter API key no configurada.")
        return None
    content = None
    if OPENROUTER_API_KEY:
        prompt = ("Devuelve SOLO un JSON válido con las claves 'lat' y 'lon' (valores numéricos).\n" "Respuesta ejemplo: ```{\"lat\": 19.4326, \"lon\": -99.1332}```\n" f"Dirección a geocodificar: {address}\n\nSi no puedes geocodificar, responde `null`." )
        try:
            headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
            payload = {"model": "google/gemini-2.5-pro", "messages": [{"role": "user", "content": prompt}]}
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=15)
            resp.raise_for_status()
            try:
                data = resp.json()
                if isinstance(data, dict) and data.get('choices'):
                    content = data['choices'][0]['message'].get('content', '')
                else:
                    content = json.dumps(data)
            except Exception:
                content = resp.text
            m = re.search(r"\{[^}]*\}", content)
            if m:
                try:
                    parsed = json.loads(m.group(0))
                    if 'lat' in parsed and 'lon' in parsed:
                        return float(parsed['lat']), float(parsed['lon'])
                except Exception:
                    pass
            floats = re.findall(r"-?\d+\.\d+", content or "")
            if len(floats) >= 2:
                try:
                    return float(floats[0]), float(floats[1])
                except Exception:
                    pass
            logger.warning("OpenRouter no pudo geocodificar '%s'. Respuesta: %s", address, (content or '')[:300])
        except requests.exceptions.RequestException as e:
            logger.warning("OpenRouter geocoding request failed: %s", e)
    try:
        nominatim_url = "https://nominatim.openstreetmap.org/search"
        params = { 'q': address, 'format': 'json', 'limit': 1 }
        headers = { 'User-Agent': 'TakeYouOff/1.0 (+https://example.org)' }
        r = requests.get(nominatim_url, params=params, headers=headers, timeout=8)
        r.raise_for_status()
        results = r.json()
        if results and isinstance(results, list) and len(results) > 0:
            lat = float(results[0].get('lat'))
            lon = float(results[0].get('lon'))
            logger.info("Geocoding Nominatim OK para '%s' -> %s,%s", address, lat, lon)
            return lat, lon
    except Exception as e:
        logger.warning("Nominatim geocoding failed for '%s': %s", address, e)
    logger.warning("Geocoding falló para '%s' con ambos servicios.", address)
    return None


def call_elevenlabs_alert(message, save_to_file=False):
    if not ELEVENLABS_CLIENT:
        logger.warning("ALERTA: Cliente ElevenLabs no inicializado. No se generará audio.")
        return None
    try:
        logger.info("ALERTA: Generando audio de voz con ElevenLabs...")
        audio_iter = ELEVENLABS_CLIENT.text_to_speech.convert(text=message, voice_id="EXAVITQu4vr4xnSDxMaL", model_id="eleven_multilingual_v2", output_format="mp3_22050_32")
        try:
            audio_bytes = b"".join(audio_iter)
        except TypeError:
            audio_bytes = b""
            for chunk in audio_iter:
                if isinstance(chunk, (bytes, bytearray)):
                    audio_bytes += bytes(chunk)
                else:
                    audio_bytes += str(chunk).encode('utf-8')
        if save_to_file:
            audio_filename = f"alert_{uuid.uuid4().hex[:8]}.mp3"
            audio_path = AUDIO_FOLDER / audio_filename
            with open(audio_path, 'wb') as f:
                f.write(audio_bytes)
            audio_url = f"/static/audio/{audio_filename}"
            logger.info("ALERTA: Audio guardado en %s", audio_url)
            return audio_url
        b64 = base64.b64encode(audio_bytes).decode('ascii')
        data_url = f"data:audio/mpeg;base64,{b64}"
        return data_url
    except Exception as e:
        logger.error("Error al generar audio con ElevenLabs: %s", e)
        logger.error("Detalles:", exc_info=True)
        return None


# ===================================================================
# 5. RUTAS WEB Y API (El Cerebro)
# ===================================================================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/optimize-route', methods=['POST'])
def optimize_route():
    data = request.json or {}
    origen_list = data.get('origen')
    destino_list = data.get('destino')
    restricciones = data.get('restricciones', [])
    def resolve_location(val):
        try:
            if isinstance(val, (list, tuple)) and len(val) == 2:
                return [float(val[0]), float(val[1])]
        except Exception:
            pass
        try:
            if isinstance(val, dict) and 'lat' in val and 'lon' in val:
                return [float(val['lat']), float(val['lon'])]
        except Exception:
            pass
        if isinstance(val, str) and val.strip():
            coords = call_geocode_address(val.strip())
            if coords:
                return [coords[0], coords[1]]
        return None
    if DEV_MOCK:
        try:
            lat1, lon1 = float(origen_list[0]), float(origen_list[1])
            lat2, lon2 = float(destino_list[0]), float(destino_list[1])
        except Exception:
            return jsonify({"error": "Formato inválido en origen/destino para modo mock."}), 400
        mock_coords = [{"lat": lat1, "lon": lon1}, {"lat": (lat1+lat2)/2, "lon": (lon1+lon2)/2}, {"lat": lat2, "lon": lon2}]
        mock_km = round(random.uniform(30, 600))
        return jsonify({"status": "success", "ruta_km": mock_km, "ruta_coordenadas": mock_coords, "is_critical_alert": (mock_km > 500 or len(restricciones) >= 3), "analisis_ia_texto": "Modo MOCK: análisis simulado.", "audio_alert_url": None, "analisis_simulacion": {"riesgo_alto": round(10 + len(restricciones) * 5 + mock_km / 100), "riesgo_exito": round(90 - len(restricciones) * 5 - mock_km / 100)}})
    try:
        def valid_coord(c):
            try:
                return isinstance(c, (list, tuple)) and len(c) == 2 and all(isinstance(float(x), float) for x in c)
            except Exception:
                return False
        origen_coords = resolve_location(origen_list)
        destino_coords = resolve_location(destino_list)
        if not origen_coords or not destino_coords:
            return jsonify({"error": "No se pudieron resolver 'origen' o 'destino' a coordenadas válidas. Pueden ser listas [lat, lon] o direcciones."}), 400
        logger.info("Llamando a optimize_route_wolfram...")
        resolved_restrictions = []
        if isinstance(restricciones, (list, tuple)):
            for r in restricciones:
                rc = resolve_location(r)
                if rc:
                    resolved_restrictions.append(rc)
        wolfram_result = optimize_route_wolfram(origen_coords, destino_coords, resolved_restrictions)
        if wolfram_result is None:
            return jsonify({"error": "Motor Wolfram no respondió. Contacte al Modelador."}), 503
        ruta_km = 0
        wolfram_result_dict = wolfram_result
        if isinstance(wolfram_result_dict, dict):
            if 'RutaTotalKM' in wolfram_result_dict:
                try:
                    ruta_km = float(wolfram_result_dict['RutaTotalKM'])
                except (ValueError, TypeError):
                    ruta_km = 0
        wolfram_coords = wolfram_result_dict.get('RutaOptimizada', [])
        ruta_coordenadas_normalizadas = []
        if isinstance(wolfram_coords, list):
            for p in wolfram_coords:
                if isinstance(p, (list, tuple)) and len(p) == 2:
                    try:
                        ruta_coordenadas_normalizadas.append({"lat": float(p[0]), "lon": float(p[1])})
                    except (ValueError, TypeError):
                        logger.warning("Advertencia: Coordenadas de Wolfram no son numéricas.")
                        pass
        datos_para_gemini = {"RutaTotalKM": round(ruta_km, 2), "NumeroRestricciones": len(restricciones), "PuntoOrigen": origen_list, "PuntoDestino": destino_list, "RutaTienePuntosIntermedios": len(ruta_coordenadas_normalizadas) > 2}
        wolfram_result_str = json.dumps(datos_para_gemini)
        is_critical = (ruta_km > 500 or len(restricciones) >= 3)
        gemini_analysis = call_gemini_analysis(wolfram_result_str)
        audio_alert_url = None
        audio_alert_data = None
        force_audio = bool(data.get('force_audio', False))
        should_generate_audio = is_critical or force_audio
        if should_generate_audio:
            if is_critical:
                alert_message = f"ALERTA CRÍTICA: La ruta óptima excede los {int(ruta_km)} kilómetros y presenta alto riesgo. Verifique el análisis de Gemini."
            else:
                short_analysis = None
                try:
                    if isinstance(gemini_analysis, str) and len(gemini_analysis) > 0:
                        short_analysis = gemini_analysis.split('\n')[0]
                except Exception:
                    short_analysis = None
                if short_analysis:
                    alert_message = f"ALERTA: Riesgo detectado en la ruta. Resumen: {short_analysis}"
                else:
                    alert_message = f"ALERTA: Riesgo detectado en la ruta. Revisa el informe de IA en pantalla."
            logger.info("Generando audio de alerta (force_audio=%s, is_critical=%s)", force_audio, is_critical)
            audio_alert_data = call_elevenlabs_alert(alert_message, save_to_file=False)
        return jsonify({"status": "success", "ruta_km": int(ruta_km), "ruta_coordenadas": ruta_coordenadas_normalizadas, "is_critical_alert": is_critical, "analisis_ia_texto": gemini_analysis, "audio_alert_url": audio_alert_url, "audio_alert_data": audio_alert_data, "analisis_simulacion": {"riesgo_alto": round(10 + len(restricciones) * 5 + ruta_km / 100), "riesgo_exito": round(90 - len(restricciones) * 5 - ruta_km / 100)}})
    except Exception as e:
        logger.exception("Error en el endpoint optimize-route: %s", e)
        return jsonify({"error": f"Error interno del servidor: {e}"}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "dev_mock": DEV_MOCK})


# ===================================================================
# 6. NUEVOS ENDPOINTS PARA OPTI-RUTA SKY (OpenSky Monitoring)
# ===================================================================

@app.route('/api/vuelos', methods=['GET'])
def get_vuelos():
    try:
        flight_monitor.fetch_opensky_data()
        conflicts, alerts = flight_monitor.detect_conflicts()
        return jsonify({"status": "ok", "vuelos": flight_monitor.flights, "conflictos": conflicts, "alerts": alerts, "total_vuelos": len(flight_monitor.flights), "total_conflictos": len(conflicts)})
    except Exception as e:
        logger.error(f"Error en endpoint vuelos: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/conflict-analysis', methods=['POST'])
def analyze_conflict():
    try:
        data = request.json or {}
        flight1 = data.get('flight1', {})
        flight2 = data.get('flight2', {})
        if not flight1 or not flight2:
            return jsonify({"error": "Vuelos requeridos"}), 400
        context = {"vuelo1": {"callsign": flight1.get('callsign'), "alt": flight1.get('alt'), "heading": flight1.get('heading'), "velocity": flight1.get('velocity'), "origin": flight1.get('origin')}, "vuelo2": {"callsign": flight2.get('callsign'), "alt": flight2.get('alt'), "heading": flight2.get('heading'), "velocity": flight2.get('velocity'), "origin": flight2.get('origin')}}
        prompt = (f"Eres un controlador aéreo experto. Analiza este conflicto de tráfico aéreo:\n\n" f"Vuelo 1 ({context['vuelo1']['callsign']}): Altitud {context['vuelo1']['alt']}ft, " f"Rumbo {context['vuelo1']['heading']}°, Velocidad {context['vuelo1']['velocity']}km/h\n" f"Vuelo 2 ({context['vuelo2']['callsign']}): Altitud {context['vuelo2']['alt']}ft, " f"Rumbo {context['vuelo2']['heading']}°, Velocidad {context['vuelo2']['velocity']}km/h\n\n" f"Proporciona:\n" f"1. RIESGO INMEDIATO: Evaluación rápida (Alto/Medio/Bajo)\n" f"2. ACCIÓN RECOMENDADA: Qué debe hacer cada vuelo\n" f"3. JUSTIFICACIÓN MATEMÁTICA: Por qué esta solución es óptima\n")
        analysis = call_gemini_analysis(prompt)
        return jsonify({"status": "ok", "conflict_analysis": analysis, "context": context})
    except Exception as e:
        logger.error(f"Error en conflict-analysis: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/emergency-route', methods=['POST'])
def emergency_route():
    try:
        data = request.json or {}
        flight_position = data.get('flight_position')
        destination = data.get('destination')
        restricted_zones = data.get('restricted_zones', [])
        if not flight_position or not destination:
            return jsonify({"error": "flight_position y destination requeridos"}), 400
        def _resolve(val):
            try:
                if isinstance(val, (list, tuple)) and len(val) == 2:
                    return [float(val[0]), float(val[1])]
            except Exception:
                pass
            if isinstance(val, str):
                coords = call_geocode_address(val)
                if coords:
                    return [coords[0], coords[1]]
            return None
        fp_coords = _resolve(flight_position)
        dst_coords = _resolve(destination)
        if not fp_coords or not dst_coords:
            return jsonify({"error": "No se pudieron resolver flight_position o destination a coordenadas válidas."}), 400
        resolved_restrictions = []
        if isinstance(restricted_zones, (list, tuple)):
            for r in restricted_zones:
                rc = _resolve(r)
                if rc:
                    resolved_restrictions.append(rc)
        result = optimize_route_wolfram(fp_coords, dst_coords, resolved_restrictions)
        if result is None:
            return jsonify({"error": "No se pudo calcular ruta de emergencia"}), 503
        alert_msg = f"Ruta de emergencia calculada: {result['RutaTotalKM']} kilómetros. Siga las coordenadas en pantalla."
        audio_data = call_elevenlabs_alert(alert_msg, save_to_file=False)
        return jsonify({"status": "success", "emergency_route": result['RutaOptimizada'], "total_km": result['RutaTotalKM'], "audio_alert": None, "audio_alert_data": audio_data, "timestamp": str(__import__('datetime').datetime.now())})
    except Exception as e:
        logger.error(f"Error en emergency-route: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    try:
        total_flights = len(flight_monitor.flights)
        cargo_flights = len([f for f in flight_monitor.flights if f['type'] == 'carga'])
        passenger_flights = total_flights - cargo_flights
        avg_alt = sum(f['alt'] for f in flight_monitor.flights) / total_flights if total_flights > 0 else 0
        return jsonify({"status": "ok", "total_flights": total_flights, "cargo_flights": cargo_flights, "passenger_flights": passenger_flights, "average_altitude": round(avg_alt, 0), "conflict_zones": len(flight_monitor.conflict_zones), "active_monitoring": True})
    except Exception as e:
        logger.error(f"Error en statistics: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    logger.info("🚀 OPTI-RUTA SKY iniciando...")
    logger.info(f"📍 Modo desarrollo: DEV_MOCK={DEV_MOCK}")
    logger.info("✈️ Sistema de monitoreo OpenSky activo")
    app.run(debug=True, port=5000)
def chat():
    return "Hello, how can I assist you today?"
