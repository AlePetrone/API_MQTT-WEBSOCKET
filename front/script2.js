document.addEventListener('DOMContentLoaded', () => {
    // --- CONFIGURACIÓN ---
    const API_WS_URL = 'ws://localhost:6600';    // El WebSocket que habla con la API
    const CLIENT_WS_URL = 'ws://localhost:7600'; // El WebSocket para los clientes finales

    // --- ELEMENTOS DEL DOM ---
    const tokenInput = document.getElementById('tokenInput');
    const usernameInput = document.getElementById('usernameInput');
    const registerTokenBtn = document.getElementById('registerTokenBtn');
    const connectClientBtn = document.getElementById('connectClientBtn');
    const logoutBtn = document.getElementById('logoutBtn');
    const logOutput = document.getElementById('logOutput');

    let api_ws = null;
    let client_ws = null;

    // --- FUNCIÓN PARA LOGS ---
    function logMessage(message, source = 'system') {
        const messageElement = document.createElement('div');
        messageElement.className = `log-message ${source}`;
        const timestamp = new Date().toLocaleTimeString();
        messageElement.textContent = `[${timestamp}] [${source.toUpperCase()}]: ${message}`;
        logOutput.appendChild(messageElement);
        logOutput.scrollTop = logOutput.scrollHeight;
    }

    // --- CONEXIONES A WEBSOCKETS ---
    function connect(url, name) {
        logMessage(`Intentando conectar a ${name} en ${url}...`);
        const ws = new WebSocket(url);
        ws.onopen = () => logMessage(`Conectado a ${name}.`, name);
        ws.onmessage = (event) => logMessage(event.data, name);
        ws.onerror = () => logMessage(`Error en la conexión con ${name}.`, 'error');
        ws.onclose = () => logMessage(`Desconectado de ${name}.`, 'error');
        return ws;
    }

    api_ws = connect(API_WS_URL, 'API_WS');
    
    // --- LÓGICA DE LOS BOTONES ---

    // 1. Botón para simular que la API registra un nuevo token
    registerTokenBtn.addEventListener('click', () => {
        const token = tokenInput.value.trim();
        const user = usernameInput.value.trim();
        if (!token || !user) {
            logMessage('El token y el usuario son requeridos.', 'error');
            return;
        }
        
        const message = {
            MESSAGE_TYPE: 'NEW_CONNECTION',
            token: token,
            user: user
        };
        const jsonMessage = JSON.stringify(message);
        
        if (api_ws && api_ws.readyState === WebSocket.OPEN) {
            api_ws.send(jsonMessage);
            logMessage(jsonMessage, 'client');
        } else {
            logMessage('No se pudo enviar: API_WS no está conectado.', 'error');
        }
    });

    // 2. Botón para simular que un cliente se conecta con un token
    connectClientBtn.addEventListener('click', () => {
        const token = tokenInput.value.trim();
        if (!token) {
            logMessage('El token es requerido.', 'error');
            return;
        }

        // Si ya hay una conexión de cliente, la cerramos antes de abrir una nueva
        if(client_ws && client_ws.readyState === WebSocket.OPEN) {
            client_ws.close();
        }
        
        // Conectamos el cliente final
        client_ws = connect(CLIENT_WS_URL, 'CLIENT_WS');

        // El cliente necesita esperar a que la conexión se abra para poder enviar el token
        client_ws.onopen = () => {
            logMessage('Conectado a CLIENT_WS.', 'CLIENT_WS');
            const authMessage = { token: token };
            const jsonAuthMessage = JSON.stringify(authMessage);
            client_ws.send(jsonAuthMessage);
            logMessage(jsonAuthMessage, 'client');
        };
    });

    // 3. Botón para enviar la orden de LOGOUT a la API
    logoutBtn.addEventListener('click', () => {
        const token = tokenInput.value.trim();
        if (!token) {
            logMessage('El token es requerido para el logout.', 'error');
            return;
        }
        
        const message = {
            MESSAGE_TYPE: 'LOGOUT',
            token: token
        };
        const jsonMessage = JSON.stringify(message);

        if (api_ws && api_ws.readyState === WebSocket.OPEN) {
            api_ws.send(jsonMessage);
            logMessage(jsonMessage, 'client');
        } else {
            logMessage('No se pudo enviar: API_WS no está conectado.', 'error');
        }
    });
});