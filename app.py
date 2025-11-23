from flask import Flask, jsonify, render_template
import requests
import time

app = Flask(__name__)

# --- CONFIGURACIÓN ---

# Coordenadas aproximadas para México (Bounding Box)
LAT_MIN = 14.0
LAT_MAX = 33.0
LON_MIN = -118.0
LON_MAX = -86.0

# Credenciales OAuth2 para OpenSky
# NOTA: En producción, usa variables de entorno para esto.
CLIENT_ID = "kevinisrael-api-client"
CLIENT_SECRET = "3uNURtGOqcco14gBndRUmPpPSjCdA3RU"

# Cache para token y expiración
token_cache = {
    "access_token": None,
    "expires_at": 0
}

# --- FUNCIONES AUXILIARES ---

def obtener_token():
    """Obtiene o renueva el token de acceso OAuth2 de OpenSky."""
    if token_cache["access_token"] and token_cache["expires_at"] > time.time():
        return token_cache["access_token"]
    url = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID.strip(),
        "client_secret": CLIENT_SECRET.strip()
    }

    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        json_data = response.json()

        token_cache["access_token"] = json_data.get("access_token")
        expires_in = json_data.get("expires_in", 1800)
        token_cache["expires_at"] = time.time() + expires_in

        return token_cache["access_token"]

    except requests.RequestException as e:
        # No forzamos una excepción aquí: devolvemos None y dejamos que
        # las rutas que usan la API intenten la llamada sin token.
        try:
            # Si es HTTPError con respuesta, intenta dar más detalle
            if hasattr(e, 'response') and e.response is not None:
                print(f"Error al obtener token OAuth2: {e.response.status_code} - {e.response.text}")
            else:
                print(f"Error al obtener token OAuth2: {e}")
        except Exception:
            print(f"Error al obtener token OAuth2: {e}")
        return None

# --- RUTAS ---

@app.route("/")
def index():
    """Página principal que sirve el mapa."""
    return render_template("index.html")


@app.route("/vuelos")
def vuelos():
    """Obtiene los vuelos actuales dentro del área de México."""
    url = "https://opensky-network.org/api/states/all"
    params = {
        "lamin": LAT_MIN,
        "lomin": LON_MIN,
        "lamax": LAT_MAX,
        "lomax": LON_MAX
    }

    try:
        # Intentamos obtener token, pero si no está disponible hacemos la
        # llamada sin Authorization (la API pública a veces lo permite).
        token = obtener_token()
        headers = {
            "User-Agent": "MiAppDeVuelos/1.0"
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        lista_vuelos = []
        # 'states' contiene la lista de aviones. Si es None, usamos lista vacía.
        for estado in data.get("states", []):
            lat = estado[6]
            lon = estado[5]
            
            # Filtramos si no tiene posición válida
            if lat is None or lon is None:
                continue
            
            vuelo = {
                "icao24": estado[0],
                "callsign": estado[1].strip() if estado[1] else "N/A",
                "origin_country": estado[2],
                "latitude": lat,
                "longitude": lon,
                "altitude": estado[7],
                "velocity": estado[9],
                "heading": estado[10],
                "color": "blue" # Color para el marcador en el mapa
            }
            lista_vuelos.append(vuelo)
            
        return jsonify(lista_vuelos)

    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 429:
            return jsonify({"error": "Límite de peticiones alcanzado. Intenta más tarde."}), 429
        print(f"Error HTTP al consultar OpenSky: {e}")
        return jsonify({"error": "Error al consultar OpenSky"}), 500
        
    except Exception as e:
        print(f"Error general: {e}")
        return jsonify({"error": "Error interno"}), 500


@app.route("/ruta_vuelo/<string:icao24>")
def ruta_vuelo(icao24):
    """Busca el historial de un avión específico y sus coordenadas de origen/destino."""
    now = int(time.time())
    begin = now - 24 * 3600  # Últimas 24 horas

    # Lista de aeropuertos mexicanos (diccionario para traducir código ICAO a coords)
    aeropuertos = {
        "MMMX": {"lat": 19.4361, "lng": -99.0719},  # Ciudad de México - AICM
        "MMGL": {"lat": 20.5218, "lng": -103.3104}, # Guadalajara
        "MMUN": {"lat": 25.9066, "lng": -97.4251},  # Monterrey
        "MMMY": {"lat": 21.0365, "lng": -86.8771},  # Cancún
        "MMQT": {"lat": 19.8517, "lng": -90.5131},  # Chetumal
        "MMCB": {"lat": 18.5042, "lng": -88.3267},  # Chetumal (alternativo)
        "MMTO": {"lat": 20.5833, "lng": -100.3833}, # Toluca
        "MMHO": {"lat": 16.8517, "lng": -99.8233},  # Huatulco
        "MMPR": {"lat": 17.9897, "lng": -92.9361},  # Palenque
        "MMSP": {"lat": 16.5805, "lng": -93.0538},  # Tapachula
        "MMMD": {"lat": 25.7833, "lng": -100.1},    # Ciudad Victoria
        "MMMT": {"lat": 24.5611, "lng": -104.5911}, # Mazatlán
        "MMES": {"lat": 20.7036, "lng": -103.3531}, # Aguascalientes
        "MMLO": {"lat": 18.1122, "lng": -96.8728},  # Loreto
        "MMZL": {"lat": 19.9847, "lng": -102.2833}, # Zamora
        "MMCS": {"lat": 20.6533, "lng": -103.325},  # Colima
        "MMVA": {"lat": 18.7758, "lng": -99.1017},  # Valle de Bravo
        "MMOX": {"lat": 17.0667, "lng": -96.7167},  # Oaxaca
        "MMSD": {"lat": 20.9167, "lng": -89.6167},  # Mérida
        "MMTB": {"lat": 16.7567, "lng": -93.1294},  # Tapachula (Base)
        "MMZC": {"lat": 21.0333, "lng": -86.8667},  # Cozumel
        "MMTM": {"lat": 16.75, "lng": -93.1167},   # Tapachula (Alterno)
        "MMTX": {"lat": 18.45, "lng": -95.2333},    # Tuxtepec
        "MMAN": {"lat": 19.0833, "lng": -98.2833},  # San Luis Potosí
        "MMBJ": {"lat": 19.3333, "lng": -99.15},    # Bajío
        # "MMMY" estaba repetido al final de la imagen, ya está arriba
    }

    try:
        token = obtener_token()
        headers = {
            "User-Agent": "MiAppDeVuelos/1.0"
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        url = "https://opensky-network.org/api/flights/aircraft"
        params = {
            "icao24": icao24.lower(),
            "begin": begin,
            "end": now
        }

        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        vuelos_historial = resp.json()

        if not vuelos_historial:
            return jsonify({"error": "No hay vuelos recientes"}), 404

        # Tomamos el último vuelo registrado (el más reciente)
        vuelo = vuelos_historial[-1]
        origen = vuelo.get("estDepartureAirport")
        destino = vuelo.get("estArrivalAirport")

        # Imprime para verificar en consola
        print(f"Origen: {origen}, Destino: {destino}")

        # Busca las coordenadas en nuestro diccionario local
        origen_coords = aeropuertos.get(origen)
        destino_coords = aeropuertos.get(destino)

        return jsonify({
            "origen": origen_coords,
            "destino": destino_coords,
            "callsign": vuelo.get("callsign", "N/A"),
            "estDepartureAirport": origen,
            "estArrivalAirport": destino
        })

    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
             return jsonify({"error": "Ruta no encontrada"}), 404
        print(f"Error HTTP al consultar ruta: {e}")
        return jsonify({"error": "Error al consultar ruta"}), 500
        
    except Exception as e:
        print(f"Error general en ruta_vuelo: {e}")
        return jsonify({"error": "Error interno"}), 500

if __name__ == "__main__":
    app.run(debug=True)