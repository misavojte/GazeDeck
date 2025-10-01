#!/usr/bin/env python3
"""
Integration test for WebSocket server state management.

Tests that the WebSocket server properly handles multiple start/stop cycles
without global state pollution - the core issue that was causing CV restart problems.
"""

import unittest
import asyncio
import websockets
import json
from unittest.mock import AsyncMock, MagicMock

from gazedeck.core.websocket_server import WebSocketServer


class TestWebSocketIntegration(unittest.TestCase):
    """Test WebSocket server integration and state management."""
    
    def test_multiple_start_stop_cycles(self):
        """
        Test that multiple start/stop cycles work without state pollution.
        
        This test simulates the exact scenario that was causing the CV restart issue:
        1. Start server (first execution)
        2. Stop server (Ctrl+C)
        3. Start server again (second execution)
        4. Verify server works correctly
        """
        async def test_cycles():
            # First cycle - simulate first execution
            server1 = WebSocketServer(host="127.0.0.1", port=8769)
            await server1.start()
            self.assertTrue(server1.is_running)
            
            # Simulate some usage
            server1.broadcast_gaze_data(1, 2, 0.5, 0.5, 1234567890.0)
            
            # Stop server - simulate Ctrl+C
            await server1.stop()
            self.assertFalse(server1.is_running)
            self.assertEqual(server1.client_count, 0)
            
            # Second cycle - simulate restart without CV
            server2 = WebSocketServer(host="127.0.0.1", port=8770)
            await server2.start()
            self.assertTrue(server2.is_running)
            self.assertEqual(server2.client_count, 0)
            
            # Verify server2 works independently
            server2.broadcast_gaze_data(2, 3, 0.7, 0.3, 1234567891.0)
            
            # Clean up
            await server2.stop()
            self.assertFalse(server2.is_running)
        
        asyncio.run(test_cycles())
    
    def test_concurrent_servers(self):
        """
        Test that multiple servers can run concurrently on different ports.
        
        This verifies that the class-based design eliminates global state conflicts.
        """
        async def test_concurrent():
            # Create multiple servers
            servers = []
            for i in range(3):
                server = WebSocketServer(host="127.0.0.1", port=8771 + i)
                await server.start()
                servers.append(server)
            
            # All should be running independently
            for server in servers:
                self.assertTrue(server.is_running)
                self.assertEqual(server.client_count, 0)
            
            # Test broadcasting to each server
            for i, server in enumerate(servers):
                server.broadcast_gaze_data(i, i+1, 0.1 * i, 0.2 * i, 1234567890.0 + i)
            
            # Clean up all servers
            for server in servers:
                await server.stop()
                self.assertFalse(server.is_running)
        
        asyncio.run(test_concurrent())
    
    def test_state_reset_after_stop(self):
        """
        Test that server state is properly reset after stop.
        
        This ensures that stopping and restarting a server gives you a clean state.
        """
        async def test_reset():
            server = WebSocketServer(host="127.0.0.1", port=8774)
            
            # Start server
            await server.start()
            self.assertTrue(server.is_running)
            
            # Simulate some state changes
            server.broadcast_gaze_data(1, 2, 0.5, 0.5, 1234567890.0)
            
            # Stop server
            await server.stop()
            self.assertFalse(server.is_running)
            self.assertEqual(server.client_count, 0)
            
            # Restart server - should have clean state
            await server.start()
            self.assertTrue(server.is_running)
            self.assertEqual(server.client_count, 0)
            
            # Should work normally
            server.broadcast_gaze_data(3, 4, 0.8, 0.2, 1234567891.0)
            
            # Clean up
            await server.stop()
        
        asyncio.run(test_reset())


if __name__ == '__main__':
    unittest.main()
