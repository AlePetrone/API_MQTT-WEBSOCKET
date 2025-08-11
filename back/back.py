import asyncio
import websockets
import json
from datetime import datetime
from websocket import websocket_api, handler_client_connection



MESSAGE_TYPES = {
    #// Mensajes de conexión
    'NEW_CONNECTION': 'VALIDATE_CONNECTION' ,         
    'LOGOUT':'USER_LOGGED_OUT',                         
    'GET_ACTIVE_USERS': 'ACTIVE_USERS'
};

# Diccionario para almacenar tokens y sus datos asociados.
# En un sistema real, esto debería estar en una base de datos o un caché como Redis.
Token_Activos = {}       # {"token123": {"token": "token123", "username": "user1"}}
active_connections = {}  # {"token123": websocket_object}


async def main():
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    PORT_API = 6600
    PORT_CLIENT = 7600

    server_api = await websockets.serve(websocket_api, "localhost", PORT_API)
    server_client = await websockets.serve(handler_client_connection, "localhost", PORT_CLIENT)
    
    print(f"✅ Servidor API corriendo en ws://localhost:{PORT_API}")
    print(f"✅ Servidor de Clientes corriendo en ws://localhost:{PORT_CLIENT}")
    print("Ambos servidores se ejecutan de forma concurrente. Presiona Ctrl+C para detener.")

    await asyncio.gather(server_api.wait_closed(), server_client.wait_closed())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServidores detenidos.")