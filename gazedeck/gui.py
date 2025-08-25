"""Simple HTML GUI for GazeDeck using pywebview"""

import webview
import os
import random
from pathlib import Path
from .websocket_server import websocket_server
from .config import config


class GazedeckAPI:
    """Backend API for the GUI"""
    
    def get_config(self):
        """Get current configuration"""
        return {
            "host": config.websocket_host,
            "port": config.websocket_port,
            "fixation_duration_ms": config.fixation_duration_ms,
            "server_running": websocket_server.is_running
        }
    
    def update_config(self, host, port):
        """Update WebSocket configuration"""
        try:
            port = int(port)
            config.set('websocket.host', host)
            config.set('websocket.port', port)
            websocket_server.host = host
            websocket_server.port = port
            return {"success": True, "message": "Configuration updated"}
        except ValueError:
            return {"success": False, "message": "Invalid port number"}
    
    def start_server(self):
        """Start the WebSocket server"""
        try:
            websocket_server.start_server()
            return {"success": True, "message": "Server starting..."}
        except Exception as e:
            return {"success": False, "message": f"Failed to start server: {str(e)}"}
    
    def stop_server(self):
        """Stop the WebSocket server"""
        try:
            websocket_server.stop_server()
            return {"success": True, "message": "Server stopped"}
        except Exception as e:
            return {"success": False, "message": f"Failed to stop server: {str(e)}"}
    
    def trigger_fixation(self):
        """Trigger a random fixation sequence"""
        try:
            # Generate random coordinates
            x = random.uniform(0.0, 1.0)
            y = random.uniform(0.0, 1.0)
            
            websocket_server.trigger_fixation_sequence(x, y)
            return {
                "success": True, 
                "message": f"Fixation triggered at ({x:.3f}, {y:.3f})"
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to trigger fixation: {str(e)}"}


def get_html_content():
    """Return the HTML content for the GUI window"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GazeDeck Control Panel</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
            }
            
            .container {
                max-width: 600px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            h1 {
                margin: 0 0 10px 0;
                font-size: 2.5em;
                font-weight: 300;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
                text-align: center;
            }
            
            .subtitle {
                font-size: 1.1em;
                opacity: 0.8;
                margin-bottom: 30px;
                text-align: center;
            }
            
            .section {
                margin-bottom: 25px;
                padding: 20px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            .section h3 {
                margin: 0 0 15px 0;
                font-size: 1.3em;
                color: #fff;
            }
            
            .form-group {
                margin-bottom: 15px;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .form-group label {
                min-width: 60px;
                font-size: 0.95em;
            }
            
            .form-group input {
                flex: 1;
                padding: 8px 12px;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 5px;
                background: rgba(255, 255, 255, 0.1);
                color: white;
                font-size: 0.95em;
            }
            
            .form-group input::placeholder {
                color: rgba(255, 255, 255, 0.6);
            }
            
            .button {
                background: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.3);
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 0.95em;
                transition: all 0.3s ease;
                margin: 5px;
            }
            
            .button:hover {
                background: rgba(255, 255, 255, 0.3);
                transform: translateY(-1px);
            }
            
            .button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
                transform: none;
            }
            
            .button.primary {
                background: rgba(76, 175, 80, 0.8);
                border-color: rgba(76, 175, 80, 1);
            }
            
            .button.danger {
                background: rgba(244, 67, 54, 0.8);
                border-color: rgba(244, 67, 54, 1);
            }
            
            .button.warning {
                background: rgba(255, 152, 0, 0.8);
                border-color: rgba(255, 152, 0, 1);
            }
            
            .status {
                background: rgba(255, 255, 255, 0.15);
                padding: 10px 15px;
                border-radius: 8px;
                margin: 10px 0;
                font-size: 0.9em;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            .status.success {
                background: rgba(76, 175, 80, 0.3);
                border-color: rgba(76, 175, 80, 0.5);
            }
            
            .status.error {
                background: rgba(244, 67, 54, 0.3);
                border-color: rgba(244, 67, 54, 0.5);
            }
            
            .controls {
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
                justify-content: center;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>GazeDeck</h1>
            <div class="subtitle">Plane-relative gaze bridge control panel</div>
            
            <div class="section">
                <h3>WebSocket Server Configuration</h3>
                <div class="form-group">
                    <label>Host:</label>
                    <input type="text" id="host" placeholder="localhost">
                </div>
                <div class="form-group">
                    <label>Port:</label>
                    <input type="number" id="port" placeholder="8765">
                </div>
                <button class="button" onclick="updateConfig()">Update Config</button>
            </div>
            
            <div class="section">
                <h3>Server Control</h3>
                <div class="controls">
                    <button class="button primary" id="startBtn" onclick="startServer()">Start Server</button>
                    <button class="button danger" id="stopBtn" onclick="stopServer()" disabled>Stop Server</button>
                </div>
                <div id="serverStatus" class="status">Server stopped</div>
            </div>
            
            <div class="section">
                <h3>Fixation Testing</h3>
                <div class="controls">
                    <button class="button warning" id="fixationBtn" onclick="triggerFixation()">Trigger Random Fixation</button>
                </div>
                <div id="fixationStatus" class="status">Ready to test fixations</div>
            </div>
        </div>
        
        <script>
            let config = {};
            
            // Load initial configuration on page load
            window.addEventListener('DOMContentLoaded', async function() {
                await loadConfig();
                updateUI();
            });
            
            async function loadConfig() {
                try {
                    config = await window.pywebview.api.get_config();
                    document.getElementById('host').value = config.host;
                    document.getElementById('port').value = config.port;
                } catch (error) {
                    console.error('Failed to load config:', error);
                    // Fallback to defaults
                    config = {
                        host: 'localhost',
                        port: 8765,
                        server_running: false
                    };
                    document.getElementById('host').value = config.host;
                    document.getElementById('port').value = config.port;
                }
            }
            
            function updateUI() {
                const startBtn = document.getElementById('startBtn');
                const stopBtn = document.getElementById('stopBtn');
                const fixationBtn = document.getElementById('fixationBtn');
                const serverStatus = document.getElementById('serverStatus');
                
                if (config.server_running) {
                    startBtn.disabled = true;
                    stopBtn.disabled = false;
                    fixationBtn.disabled = false;
                    serverStatus.textContent = `Server running on ${config.host}:${config.port}`;
                    serverStatus.className = 'status success';
                } else {
                    startBtn.disabled = false;
                    stopBtn.disabled = true;
                    fixationBtn.disabled = true;
                    serverStatus.textContent = 'Server stopped';
                    serverStatus.className = 'status';
                }
            }
            
            async function updateConfig() {
                const host = document.getElementById('host').value;
                const port = document.getElementById('port').value;
                
                try {
                    const result = await window.pywebview.api.update_config(host, port);
                    showMessage('serverStatus', result.message, result.success);
                    if (result.success) {
                        config.host = host;
                        config.port = parseInt(port);
                    }
                } catch (error) {
                    console.error('Update config error:', error);
                    showMessage('serverStatus', 'Failed to update config', false);
                }
            }
            
            async function startServer() {
                try {
                    const result = await window.pywebview.api.start_server();
                    showMessage('serverStatus', result.message, result.success);
                    
                    if (result.success) {
                        // Wait a bit for server to start, then update UI
                        setTimeout(async () => {
                            await loadConfig();
                            updateUI();
                        }, 1000);
                    }
                } catch (error) {
                    console.error('Start server error:', error);
                    showMessage('serverStatus', 'Failed to start server', false);
                }
            }
            
            async function stopServer() {
                try {
                    const result = await window.pywebview.api.stop_server();
                    showMessage('serverStatus', result.message, result.success);
                    
                    if (result.success) {
                        config.server_running = false;
                        updateUI();
                    }
                } catch (error) {
                    console.error('Stop server error:', error);
                    showMessage('serverStatus', 'Failed to stop server', false);
                }
            }
            
            async function triggerFixation() {
                try {
                    const result = await window.pywebview.api.trigger_fixation();
                    showMessage('fixationStatus', result.message, result.success);
                } catch (error) {
                    console.error('Trigger fixation error:', error);
                    showMessage('fixationStatus', 'Failed to trigger fixation', false);
                }
            }
            
            function showMessage(elementId, message, success) {
                const element = document.getElementById(elementId);
                element.textContent = message;
                element.className = success ? 'status success' : 'status error';
            }
        </script>
    </body>
    </html>
    """


def create_gui():
    """Create and show the GUI window"""
    html_content = get_html_content()
    
    # Create API instance
    api = GazedeckAPI()
    
    # Create the webview window with js_api
    webview.create_window(
        title="GazeDeck Control Panel",
        html=html_content,
        width=800,
        height=700,
        min_size=(600, 500),
        resizable=True,
        shadow=True,
        on_top=False,
        js_api=api
    )
    
    # Start webview
    webview.start(debug=False)


if __name__ == "__main__":
    create_gui()
