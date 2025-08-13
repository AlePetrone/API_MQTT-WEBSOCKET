# version update 2025/03/17

import asyncio
import json
import logging
import websockets
import paho.mqtt.client as mqtt
import time
#from dotenv import load_dotenv
import os

print("Control de Fuentes Iniciado")
logging.basicConfig()

USERS = set()
Token_Activos = {}       # {"token123": {"token": "token123", "username": "user1"}}
active_connections = {}  # {"token123": websocket_object}

# Cargar variables desde el archivo .env
# load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))
# MQTT_BROKER = os.getenv("MQTT_HOST") 
# MQTT_PORT = int(os.getenv("MQTT_PORT"))
# MQTT_TIMEOUT = int(os.getenv("MQTT_TIMEOUT"))
# WS_API_HOST = os.getenv("WS1_HOST")
# WS_API_PORT = int(os.getenv("WS1_PORT"))
# WS_FRONT_HOST = os.getenv("WS2_HOST")
# WS_FRONT_PORT = int(os.getenv("WS2_PORT"))

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TIMEOUT = 60
WS_API_HOST = "localhost"
WS_API_PORT = 6700
WS_FRONT_HOST = "localhost"
WS_FRONT_PORT = 6600

# ----- CLASE DE CONFIGURACIÓN -----
class Configuracion(object):
    def __init__(self):
        super(Configuracion, self).__init__()
        self.vacio = True
        self.Fuentes = {}
        self.diccionario_set = {}
        self.diccionario_get = {}

    def restart(self):
        self.vacio = True
        self.Fuentes = {}
        self.diccionario_set = {}
        self.diccionario_get = {}

    def template(self, back):
        self.backup = back

    def len_fuentes(self):
        print(len(self.diccionario_get))

    def actualizar_seteos(self, topic_set, sms):
        fuente = self.diccionario_set[topic_set]["Fuente"]
        if "ENCENDIDO" in sms:
            self.Fuentes[fuente]["On"] = {1: True, -1: False}[sms["ENCENDIDO"]]
        for na in self.Fuentes[fuente]["SetNames"]:
            self.Fuentes[fuente]["Set"].update({na: sms[self.Fuentes[fuente]["SetNames"][na]]})

    def actualizar_parametro(self, fuente, valores):
        self.Fuentes[fuente].update(valores)
    
    def leer_fuente(self, fuente):
        return self.Fuentes[fuente]

    def leer_fuentes(self):
        return self.Fuentes

    def leer_parametro(self, fuente, parametro):
        return self.Fuentes[fuente][parametro]

    def leer_diccionario(self):
        return self.diccionario_get

    def agregar_fuente(self, fuente, valores):
        self.vacio = False
        self.Fuentes.update({fuente: valores})
        self.diccionario_get.update({valores["GetTopic"]: {"Fuente": fuente, "Nombres": valores["GetNames"]}})
        self.diccionario_set.update({valores["SetTopic"]: {"Fuente": fuente, "Nombres": valores["SetNames"]}})
        
    def reporte(self):
        for f in self.Fuentes:
            print(self.Fuentes[f]["Name"],
                  self.Fuentes[f]["Set"],
                  self.Fuentes[f]["On"],
                  self.Fuentes[f]["Read"])

    def actualizar_backup(self):
        for f in self.Fuentes:
            self.backup[f]["Datos"]["Set"] = self.Fuentes[f]["Set"]
            self.backup[f]["Datos"]["Read"] = self.Fuentes[f]["Read"]
            self.backup[f]["Datos"]["On"] = self.Fuentes[f]["On"]

configuracion = Configuracion()
# --------------------------------------------------------

def cut_fun(init):
    # Desuscribir topics viejos si hay
    if not configuracion.vacio:
        for f in configuracion.backup:
            client.unsubscribe(configuracion.backup[f]["GET_TOPIC"])
    # Eliminar configuración vieja y suscribir topics nuevos
    configuracion.restart()
    configuracion.template(init)
    client.subscribe("RAMPA_HV1/LOG")
    for f in init:
        client.subscribe(init[f]["GET_TOPIC"])
        configuracion.agregar_fuente(f, {
            "Name": init[f]["Visual"]["Name"],
            "SetTopic": init[f]["SET_TOPIC"],
            "GetTopic": init[f]["GET_TOPIC"],
            "Set": init[f]["Datos"]["Set"],
            "Read": init[f]["Datos"]["Read"],
            "SetNames": init[f]["SET_NAME"],
            "GetNames": init[f]["GET_NAME"],
            "On": init[f]["Datos"]["On"]
        })

# --------------------------------------------------------
# Handler2: Maneja el WebSocket que interactúa con MQTT y con el frontend
async def counter(websocket):
    print("Conectado a counter")
    token = None
    try:
        # Se espera un mensaje inicial que contenga el token
        init_msg = await websocket.recv()
        data = json.loads(init_msg)
        token = data.get("token", "").replace("Bearer ", "")
        if token:
            active_connections[token] = websocket
            if token not in Token_Activos:
                Token_Activos[token] = {"token": token}
        USERS.add(websocket)
        print("WebSocket Frontenend activo")
        async for message in websocket:
            data = json.loads(message)
            if "TOP" in data:  # Recibe datos para enviar por MQTT
                if not configuracion.vacio:
                    fuente = configuracion.diccionario_set[data['TOP']]["Fuente"]
                    configuracion.actualizar_seteos(data['TOP'], data['SMS'])
                    client.publish(data['TOP'], json.dumps(data['SMS']))
                    for ws in active_connections.values():
                        if u != websocket:
                            await u.send(json.dumps({
                                "SET": True,
                                "Fuente": fuente,
                                "Set": configuracion.Fuentes[fuente]["Set"],
                                "On": configuracion.Fuentes[fuente]["On"]
                            }))
                else:
                    await websocket.send(json.dumps({"GET_INI": True}))
            elif "DIS" in data:  # Datos para deshabilitar fuentes de otros clientes
                for u in USERS:
                    if u != websocket:
                        await u.send(json.dumps({
                            "DIS": True,
                            "Fuente": data.get("fuente"),
                            "Disabled": data.get("disabled")
                        }))
            elif "RAM" in data:  # Enviar datos de Rampa a NodeRed
                client.publish(data['RAM'], json.dumps(data['SMS']))
            elif "GET" in data:  # Preguntar estado y enviar config
                if not configuracion.vacio:
                    await websocket.send(json.dumps({"GET": True, "CONFIG": configuracion.backup}))
            elif "INI" in data:  # Inicio: establecer o actualizar configuración y enviarla
                if configuracion.vacio:
                    cut_fun(data["INI"])
                    print("Configuración Inicial Realizada")
                else:
                    configuracion.actualizar_backup()
                await websocket.send(json.dumps({"INI": True, "CONFIG": configuracion.backup}))
                print("Envío de configuración Inicial")
            elif "FOR" in data:  # Inicio forzado: establecer config y enviarla
                cut_fun(data["FOR"])
                configuracion.len_fuentes()
                await websocket.send(json.dumps({"INI": True, "CONFIG": configuracion.backup}))
                print("Configuración realizada a la fuerza")
    except websockets.ConnectionClosed:
        print("Cliente desconectado de handler2")
    finally:
        USERS.discard(websocket)
        if token and token in active_connections:
            active_connections.pop(token, None)

# --------------------------------------------------------
# Handler1: Maneja las conexiones con la API

async def handler1(websocket):
    print("Conexión API establecida.")
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
            except Exception as e:
                print("Error al parsear el mensaje:", e)
                continue

            msg_type = data.get("type")
            # --- Nuevo Log In ---
            if msg_type == "NEW_CONNECTION":
                # Se espera que el mensaje incluya: token, username y timestamp
                token = data.get("token", "")
                username = data.get("username", "")
                timestamp = data.get("timestamp", 0)
                nuevo_token = {"token": token, "username": username, "timestamp": timestamp}
                Token_Activos[token] = nuevo_token
                print("Nuevo token añadido:", nuevo_token)
                print("Tokens activos:", Token_Activos)
                # Responder con VALIDATE_CONNECTION
                response = {"type": "VALIDATE_CONNECTION"}
                await websocket.send(json.dumps(response))

            # --- Log Out ---
            elif msg_type == "LOGOUT":
                token = data.get("token", "").replace("Bearer ", "")
                # Intentar cerrar la conexión de handler2 si existe
                ws2 = active_connections.get(token)
                if ws2:
                    try:
                        await ws2.close(code=1000)  # Cierre normal
                        print(f"WebSocket 2 cerrado para el token {token}")
                    except Exception as e:
                        print(f"Error al cerrar WebSocket 2 para token {token}: {e}")
                    finally:
                        active_connections.pop(token, None)
                        # Remover el token de la lista
                        Token_Activos.pop(token, None)
                else:
                    print(f"No se encontró conexión activa para el token {token}")
                # Responder con LOGOUT_OK
                response = {"type": "LOGOUT_OK", "token": token}
                await websocket.send(json.dumps(response))

            # --- Obtener cantidad de usuarios activos ---
            elif msg_type == "GET_ACTIVE_USERS":
                active_users = len(Token_Activos)
                response = {"type": "ACTIVE_USERS", "active_users": active_users}
                await websocket.send(json.dumps(response))

            else:
                print("Tipo de mensaje no reconocido:", msg_type)
    except websockets.ConnectionClosed:
        print("Conexión API (handler1) cerrada.")



# --------------------------------------------------------
# MQTT: Configuración y callbacks
def on_message(client, userdata, msg):
    TOPIC_py = msg.topic
    SMS_py = json.loads(msg.payload)
    if TOPIC_py != "RAMPA_HV1/LOG":
        try:
            fuente = configuracion.leer_diccionario()[TOPIC_py]["Fuente"]
            dic_na = configuracion.leer_diccionario()[TOPIC_py]["Nombres"]
            TSMS = {dic_na[na]: SMS_py[na] for na in dic_na}
            time.sleep(0.00000001)
            websockets.broadcast(USERS, json.dumps({"LEC": True, "Fuente": fuente, "Read": TSMS}))
        except Exception as e:
            print("Error en on_message:", e)
    else:
        try:
            SMS_py["RAM"] = True
            websockets.broadcast(USERS, json.dumps(SMS_py))
        except Exception as e:
            print("Error en on_message (RAM):", e)

broker_address = MQTT_BROKER
broker_port = MQTT_PORT
broker_timeout = MQTT_TIMEOUT
client = mqtt.Client()
client.connect(broker_address, broker_port, broker_timeout)

def on_connect(client, userdata, flags, rc, properties=None):
    print("MQTT Conectado")
    
client.on_message = on_message
client.on_connect = on_connect

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("MQTT Desconectado")
client.on_disconnect = on_disconnect
client.reconnect_delay_set(min_delay=1, max_delay=120)
client.loop_start()

print("go")

# --------------------------------------------------------
# Main: Levanta ambos servidores de WebSocket en puertos distintos
async def main():

    #CLIENT.LOOP_START()  # CORRE EL LOOP MQTT EN SEGUNDO PLANO

    server_handler1 = await websockets.serve(handler1, WS_API_HOST, WS_API_PORT)
    server_handler2 = await websockets.serve(counter, WS_FRONT_HOST, WS_FRONT_PORT)
    await asyncio.gather(server_handler1.wait_closed(), server_handler2.wait_closed())
    print("go2")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print("Error al ejecutar main:", e)
