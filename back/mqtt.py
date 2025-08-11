import paho.mqtt.client as mqtt
import time
import json

# --- Parámetros de Configuración ---
BROKER_ADDRESS = "localhost"  # Broker público para pruebas
BROKER_PORT = 1883
TOPIC_SUSCRIPCION = {"topic1": "TOPIC_UNO", "topic2":"TOPIC_DOS"}  
TOPIC_PUBLICACION = "mi/dispositivo/telemetria"  # Tópico para enviar datos

# --- Funciones Callback ---

def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print("✅ ¡Conectado exitosamente al Broker!")
        for topic_name in TOPIC_SUSCRIPCION.values():
            client.subscribe(topic_name)
    else:
        print(f"❌ Fallo al conectar, código de retorno: {rc}\n")

def on_subscribe(client, userdata, mid, granted_qos, properties):
    """Callback para cuando la suscripción es exitosa."""
    print(f"📡 Suscrito exitosamente al tópico: '{TOPIC_SUSCRIPCION}'")

def on_message(client, userdata, msg):
    """Callback para cuando se recibe un mensaje en un tópico suscrito."""
    print(f"📩 Mensaje recibido -> Tópico: '{msg.topic}'")
    try:
        # Intentar decodificar el payload como JSON
        payload = json.loads(msg.payload.decode('utf-8'))
        print(f"   Payload: {payload}")
        # Aquí iría la lógica para procesar el comando, por ejemplo:
        if 'comando' in payload and payload['comando'] == 'REINICIAR':
            print("   -> ¡Comando de reinicio recibido!")
    except json.JSONDecodeError:
        # Si no es JSON, mostrarlo como texto plano
        print(f"   Payload (raw): {msg.payload.decode('utf-8')}")

# --- Script Principal ---
if __name__ == "__main__":
    # 1. Crear una instancia del cliente
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    # 2. Asignar las funciones callback
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message

    try:
        # 3. Conectarse al broker
        print(f"🔌 Conectando al broker en {BROKER_ADDRESS}...")
        client.connect(BROKER_ADDRESS, BROKER_PORT, 60)

        # 4. Iniciar el bucle de red en un hilo separado
        # loop_start() es no bloqueante y maneja la reconexión automáticamente.
        client.loop_start()

        # 5. Bucle principal para publicar mensajes periódicamente
        contador_mensajes = 0
        while True:
            # Crear un payload de telemetría (ej. en formato JSON)
            telemetria = {
                "id_mensaje": contador_mensajes,
                "temperatura": 25.5,
                "humedad": 60
            }
            payload_json = json.dumps(telemetria)

            # Publicar el mensaje
            client.publish(TOPIC_PUBLICACION, payload_json)
            print(f"🚀 Mensaje N°{contador_mensajes} publicado en '{TOPIC_PUBLICACION}'")
            
            contador_mensajes += 1
            time.sleep(1)  # Esperar 10 segundos antes de la siguiente publicación

    except KeyboardInterrupt:
        # Se ejecuta cuando el usuario presiona Ctrl+C
        print("\n🛑 Programa detenido por el usuario.")
    except Exception as e:
        print(f"🚨 Ocurrió un error inesperado: {e}")
    finally:
        # 6. Detener el bucle de red y desconectar limpiamente
        print("Desconectando del broker...")
        client.loop_stop()
        client.disconnect()
        print("Cliente desconectado.")