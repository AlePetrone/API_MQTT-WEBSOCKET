import asyncio
import websockets
import json
from datetime import datetime

# --- CONFIGURACIÓN Y ESTADO GLOBAL ---

# Usamos el diccionario para obtener la respuesta correcta para cada tipo de mensaje
MESSAGE_TYPES = {
    'NEW_CONNECTION': 'VALIDATE_CONNECTION',
    'LOGOUT': 'USER_LOGGED_OUT',
    'GET_ACTIVE_USERS': 'ACTIVE_USERS'
}

Token_Activos = {}      # {token: {username: 'pepito', ...}}
active_connections = {} # {token: websocket_object}

# --- HANDLER PARA LA API (PUERTO 6600) ---
async def websocket_api(websocket):
    """Maneja órdenes de la API de control (ej: login, logout)."""
    print("API: Conexión establecida.")
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                tipo = data.get("MESSAGE_TYPE")
            except Exception as e:
                print(f"API: Error al procesar mensaje: {e}")
                continue

            if tipo == 'NEW_CONNECTION':
                token = data.get("token")
                username = data.get("user")
                if not token or not username:
                    # Validar que los datos necesarios están presentes
                    continue

                Token_Activos[token] = {"token": token, "username": username}
                print(f"API: Nuevo token añadido para el usuario '{username}'.")
                
                response = {'MESSAGE_TYPE': MESSAGE_TYPES.get(tipo), 'user': username}
                await websocket.send(json.dumps(response))

            elif tipo == 'LOGOUT':
                token = data.get("token")
                if not token:
                    continue

                # Cierra la conexión del cliente si está activa
                ws_client = active_connections.pop(token, None) # .pop() elimina y devuelve el valor
                if ws_client:
                    try:
                        await ws_client.close(code=1000, reason="Logout by API")
                        print(f"API: Conexión del cliente para token {token} cerrada.")
                    except Exception as e:
                        print(f"API: Error al cerrar el websocket del cliente: {e}")
                
                if Token_Activos.pop(token, None):
                    print(f"API: Token {token} eliminado de la lista de activos.")
                
                response = {"MESSAGE_TYPE": MESSAGE_TYPES.get(tipo), "token": token}
                await websocket.send(json.dumps(response))
            
            else:
                print(f"API: Tipo de mensaje no reconocido: {tipo}")
                
    except websockets.ConnectionClosed:
        print("API: Conexión cerrada.")

# --- HANDLER PARA CLIENTES (PUERTO 7600) ---
async def handler_client_connection(websocket):
    """Maneja la conexión de los clientes finales y valida su token al inicio."""
    token = None
    try:
        auth_message = await websocket.recv()
        data = json.loads(auth_message)
        
        token_value = data.get("token", "")
        token = token_value.replace("Bearer ", "").strip()

        if token and token in Token_Activos:
            # El token es válido, aceptamos la conexión
            active_connections[token] = websocket
            username = Token_Activos[token].get('username', 'desconocido')
            print(f"CLIENTE: Usuario '{username}' conectado exitosamente con token {token}.")
            
            # Enviamos confirmación al cliente
            response = {"status": "success", "message": "Conexión establecida y autenticada."}
            await websocket.send(json.dumps(response))
            
            # Mantenemos la conexión abierta para futuros mensajes (broadcasts, etc.)
            async for message in websocket:
                # Aquí puedes añadir la lógica para cuando el cliente envía más mensajes
                print(f"CLIENTE: Mensaje recibido de '{username}': {message}")
        else:
            # Si el token no es válido, cerramos la conexión inmediatamente
            print(f"CLIENTE: Intento de conexión con token inválido o no provisto: '{token}'")
            response = {"status": "error", "message": "Token inválido."}
            await websocket.send(json.dumps(response))
            await websocket.close(code=1011, reason="Token inválido")

    except websockets.ConnectionClosed:
        # Limpieza cuando un cliente se desconecta
        if token and token in active_connections:
            del active_connections[token]
        print(f"CLIENTE: Conexión con token {token} cerrada.")
    except Exception as e:
        print(f"CLIENTE: Error inesperado en la conexión: {e}")
        if websocket.open:
            await websocket.close()

async def main():
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