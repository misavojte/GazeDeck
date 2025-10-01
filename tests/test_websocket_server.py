#!/usr/bin/env python3
"""
Test WebSocket server functionality.

Tests the class-based WebSocket server to ensure proper state management
and eliminate global state issues.
"""

import unittest
import asyncio
import websockets
import json
from unittest.mock import AsyncMock, MagicMock

from gazedeck.core.websocket_server import WebSocketServer


class TestWebSocketServer(unittest.TestCase):
    """Test WebSocket server class functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.server = WebSocketServer(host="127.0.0.1", port=8766)
    
    def test_initial_state(self):
        """Test that server starts with clean state."""
        self.assertFalse(self.server.is_running)
        self.assertEqual(self.server.client_count, 0)
    
    def test_server_lifecycle(self):
        """Test server start/stop lifecycle."""
        async def test_lifecycle():
            # Test start
            await self.server.start()
            self.assertTrue(self.server.is_running)
            
            # Test stop
            await self.server.stop()
            self.assertFalse(self.server.is_running)
            self.assertEqual(self.server.client_count, 0)
        
        asyncio.run(test_lifecycle())
    
    def test_multiple_instances(self):
        """Test that multiple server instances are independent."""
        server1 = WebSocketServer(host="127.0.0.1", port=8767)
        server2 = WebSocketServer(host="127.0.0.1", port=8768)
        
        async def test_independence():
            # Start both servers
            await server1.start()
            await server2.start()
            
            # They should be independent
            self.assertTrue(server1.is_running)
            self.assertTrue(server2.is_running)
            
            # Stop one, other should still run
            await server1.stop()
            self.assertFalse(server1.is_running)
            self.assertTrue(server2.is_running)
            
            # Clean up
            await server2.stop()
        
        asyncio.run(test_independence())
    
    def test_broadcast_when_not_running(self):
        """Test that broadcast does nothing when server is not running."""
        # Should not raise exception
        self.server.broadcast_gaze_data(1, 2, 0.5, 0.5, 1234567890.0)
        self.server.broadcast_nowait(b"test message")
    
    def test_gaze_data_serialization(self):
        """Test that gaze data is properly serialized."""
        # Mock the serialize_gaze_message function
        with unittest.mock.patch('gazedeck.core.websocket_server.serialize_gaze_message') as mock_serialize:
            mock_serialize.return_value = b"serialized_data"
            
            # Test broadcast
            self.server.broadcast_gaze_data(1, 2, 0.5, 0.5, 1234567890.0)
            
            # Verify serialization was called
            mock_serialize.assert_called_once_with(1, 2, 0.5, 0.5, 1234567890.0)


if __name__ == '__main__':
    unittest.main()
