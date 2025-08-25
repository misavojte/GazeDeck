"""WebSocket server implementation for GazeDeck"""

import asyncio
import websockets
import json
import logging
from typing import Set, Optional, Dict, Any
from datetime import datetime
import threading
from .config import config


class WebSocketServer:
    """Singleton WebSocket server for GazeDeck"""
    
    _instance: Optional['WebSocketServer'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'WebSocketServer':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.server = None
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.is_running = False
        self.host = config.websocket_host
        self.port = config.websocket_port
        self.loop = None
        self.server_task = None
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
    
    async def register_client(self, websocket: websockets.WebSocketServerProtocol):
        """Register a new WebSocket client"""
        self.clients.add(websocket)
        self.logger.info(f"Client connected. Total clients: {len(self.clients)}")
        
        try:
            await websocket.wait_closed()
        finally:
            self.clients.remove(websocket)
            self.logger.info(f"Client disconnected. Total clients: {len(self.clients)}")
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients"""
        if not self.clients:
            self.logger.info("No clients connected to broadcast to")
            return
        
        message_str = json.dumps(message)
        self.logger.info(f"Broadcasting to {len(self.clients)} clients: {message_str}")
        
        # Create a copy of clients set to avoid modification during iteration
        clients_copy = self.clients.copy()
        
        for client in clients_copy:
            try:
                await client.send(message_str)
            except websockets.exceptions.ConnectionClosed:
                # Client disconnected, remove from set
                self.clients.discard(client)
            except Exception as e:
                self.logger.error(f"Error sending message to client: {e}")
                self.clients.discard(client)
    
    async def send_fixation_start(self, x: float = 0.5, y: float = 0.5):
        """Send fixation start message"""
        message = {
            "type": "fixationStart",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "x": x,
                "y": y
            }
        }
        await self.broadcast_message(message)
    
    async def send_fixation_end(self):
        """Send fixation end message"""
        message = {
            "type": "fixationEnd",
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast_message(message)
    
    async def send_fixation_sequence(self, x: float = 0.5, y: float = 0.5, duration_ms: int = None):
        """Send fixation start followed by fixation end after specified duration"""
        if duration_ms is None:
            duration_ms = config.fixation_duration_ms
        
        await self.send_fixation_start(x, y)
        await asyncio.sleep(duration_ms / 1000.0)  # Convert ms to seconds
        await self.send_fixation_end()
    
    async def _start_server(self):
        """Start the WebSocket server"""
        try:
            self.server = await websockets.serve(
                self.register_client,
                self.host,
                self.port
            )
            self.is_running = True
            self.logger.info(f"WebSocket server started on {self.host}:{self.port}")
            
            # Keep the server running
            await self.server.wait_closed()
            
        except Exception as e:
            self.logger.error(f"Error starting WebSocket server: {e}")
            self.is_running = False
            raise
    
    def start_server(self, host: str = None, port: int = None):
        """Start the WebSocket server in a background thread"""
        if self.is_running:
            self.logger.warning("Server is already running")
            return
        
        if host:
            self.host = host
        if port:
            self.port = port
        
        # Start server in a new thread with its own event loop
        def run_server():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            try:
                self.loop.run_until_complete(self._start_server())
            except Exception as e:
                self.logger.error(f"Server error: {e}")
            finally:
                self.is_running = False
                self.loop.close()
        
        self.server_task = threading.Thread(target=run_server, daemon=True)
        self.server_task.start()
    
    def stop_server(self):
        """Stop the WebSocket server"""
        if not self.is_running:
            self.logger.warning("Server is not running")
            return
        
        if self.server and self.loop:
            # Schedule server closure in the server's event loop
            asyncio.run_coroutine_threadsafe(self._stop_server(), self.loop)
    
    async def _stop_server(self):
        """Internal method to stop the server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.logger.info("WebSocket server stopped")
        
        self.is_running = False
    
    def trigger_fixation_sequence(self, x: float = 0.5, y: float = 0.5):
        """Trigger a fixation sequence from the main thread"""
        if not self.is_running or not self.loop:
            self.logger.warning("Server is not running, cannot send fixation sequence")
            return
        
        # Schedule the fixation sequence in the server's event loop
        asyncio.run_coroutine_threadsafe(
            self.send_fixation_sequence(x, y), 
            self.loop
        )


# Global server instance
websocket_server = WebSocketServer()
