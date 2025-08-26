"""Simple HTML GUI for GazeDeck using pywebview"""

import webview
import os
import random
import base64
import logging
import json
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, Union
from .websocket_server import websocket_server
from .config import config
from .pupil_integration import pupil_integration

# Set up logging for GUI module
logger = logging.getLogger(__name__)

class APIResponse:
    """Standardized API response format"""
    
    @staticmethod
    def success(message: str = "", data: Any = None) -> Dict[str, Any]:
        """Create a success response"""
        response = {"success": True, "message": message}
        if data is not None:
            response["data"] = data
        return response
    
    @staticmethod
    def error(message: str, error_code: str = None, details: Any = None) -> Dict[str, Any]:
        """Create an error response"""
        response = {"success": False, "message": message}
        if error_code:
            response["error_code"] = error_code
        if details:
            response["details"] = details
        return response


class GazedeckAPI:
    """Backend API for the GUI"""
    
    def __init__(self):
        """Initialize the API with logging"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.debug_mode = config.get('gui.debug_mode', False)
        
    def _log_api_call(self, method_name: str, **kwargs):
        """Log API method calls for debugging"""
        if self.debug_mode:
            self.logger.debug(f"API call: {method_name} with args: {kwargs}")
    
    def _handle_api_error(self, method_name: str, error: Exception) -> Dict[str, Any]:
        """Centralized error handling for API methods"""
        error_msg = str(error)
        self.logger.error(f"API error in {method_name}: {error_msg}")
        self.logger.error(f"Traceback: {traceback.format_exc()}")
        
        return APIResponse.error(
            message=f"Error in {method_name}: {error_msg}",
            error_code="API_ERROR",
            details={"method": method_name, "traceback": traceback.format_exc() if self.debug_mode else None}
        )
    
    def log_js_error(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """Log JavaScript errors from the frontend"""
        try:
            self._log_api_call("log_js_error", error_info=error_info)
            
            error_message = error_info.get('message', 'Unknown JS error')
            error_source = error_info.get('source', 'Unknown')
            error_line = error_info.get('lineno', 'Unknown')
            error_stack = error_info.get('stack', 'No stack trace')
            
            self.logger.error(f"JavaScript Error: {error_message}")
            self.logger.error(f"Source: {error_source}, Line: {error_line}")
            if error_stack and error_stack != 'No stack trace':
                self.logger.error(f"Stack trace: {error_stack}")
            
            return APIResponse.success("JavaScript error logged successfully")
            
        except Exception as e:
            return self._handle_api_error("log_js_error", e)
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        try:
            self._log_api_call("get_config")
            
            config_data = {
                "host": config.websocket_host,
                "port": config.websocket_port,
                "fixation_duration_ms": config.fixation_duration_ms,
                "server_running": websocket_server.is_running,
                "debug_mode": self.debug_mode
            }
            
            return APIResponse.success("Configuration retrieved", config_data)
            
        except Exception as e:
            return self._handle_api_error("get_config", e)
    
    def update_config(self, host: str, port: Union[str, int]) -> Dict[str, Any]:
        """Update WebSocket configuration"""
        try:
            self._log_api_call("update_config", host=host, port=port)
            
            # Validate inputs
            if not host or not isinstance(host, str):
                return APIResponse.error("Invalid host: must be a non-empty string", "INVALID_INPUT")
            
            try:
                port_int = int(port)
                if not (1 <= port_int <= 65535):
                    return APIResponse.error("Invalid port: must be between 1 and 65535", "INVALID_PORT")
            except (ValueError, TypeError):
                return APIResponse.error("Invalid port: must be a valid integer", "INVALID_PORT")
            
            # Update configuration
            config.set('websocket.host', host)
            config.set('websocket.port', port_int)
            websocket_server.host = host
            websocket_server.port = port_int
            
            self.logger.info(f"Configuration updated - Host: {host}, Port: {port_int}")
            return APIResponse.success("Configuration updated successfully")
            
        except Exception as e:
            return self._handle_api_error("update_config", e)
    
    def start_server(self) -> Dict[str, Any]:
        """Start the WebSocket server"""
        try:
            self._log_api_call("start_server")
            
            websocket_server.start_server()
            self.logger.info("WebSocket server started successfully")
            return APIResponse.success("Server starting...")
            
        except Exception as e:
            return self._handle_api_error("start_server", e)
    
    def stop_server(self) -> Dict[str, Any]:
        """Stop the WebSocket server"""
        try:
            self._log_api_call("stop_server")
            
            websocket_server.stop_server()
            self.logger.info("WebSocket server stopped successfully")
            return APIResponse.success("Server stopped")
            
        except Exception as e:
            return self._handle_api_error("stop_server", e)
    
    def trigger_fixation(self, x: Optional[float] = None, y: Optional[float] = None) -> Dict[str, Any]:
        """Trigger a fixation sequence at specified or random coordinates"""
        try:
            self._log_api_call("trigger_fixation", x=x, y=y)
            
            # Generate random coordinates if not provided
            if x is None:
                x = random.uniform(0.0, 1.0)
            if y is None:
                y = random.uniform(0.0, 1.0)
            
            # Validate coordinates
            if not (0.0 <= x <= 1.0) or not (0.0 <= y <= 1.0):
                return APIResponse.error("Coordinates must be between 0.0 and 1.0", "INVALID_COORDINATES")
            
            websocket_server.trigger_fixation_sequence(x, y)
            
            message = f"Fixation triggered at ({x:.3f}, {y:.3f})"
            self.logger.info(message)
            return APIResponse.success(message, {"x": x, "y": y})
            
        except Exception as e:
            return self._handle_api_error("trigger_fixation", e)
    
    # Pupil Labs Integration Methods
    
    def check_pupil_availability(self) -> Dict[str, Any]:
        """Check if Pupil Labs libraries are available"""
        try:
            self._log_api_call("check_pupil_availability")

            result = pupil_integration.check_pupil_availability()
            self.logger.info(f"Pupil availability check: {result}")
            return APIResponse.success(result["message"], result)

        except Exception as e:
            return self._handle_api_error("check_pupil_availability", e)
    
    def discover_pupil_device(self, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Discover and connect to Pupil Labs device"""
        try:
            if timeout is None:
                timeout = config.get('pupil.device_timeout', 10)

            self._log_api_call("discover_pupil_device", timeout=timeout)

            # Validate timeout
            if not isinstance(timeout, int) or timeout <= 0:
                return APIResponse.error("Timeout must be a positive integer", "INVALID_TIMEOUT")

            result = pupil_integration.discover_device(timeout)
            self.logger.info(f"Device discovery result: {result.get('success', False)}")

            if result.get("success", False):
                return APIResponse.success(result["message"], result.get("device_info", {}))
            else:
                return APIResponse.error(result.get("message", "Device discovery failed"))

        except Exception as e:
            return self._handle_api_error("discover_pupil_device", e)
    
    def get_pupil_device_status(self) -> Dict[str, Any]:
        """Get current Pupil Labs device status"""
        try:
            self._log_api_call("get_pupil_device_status")
            
            result = pupil_integration.get_device_status()
            self.logger.info(f"Device status result: {result.get('success', False)}")

            if result.get("success", False):
                return APIResponse.success("Device status retrieved", result.get("status", {}))
            else:
                return APIResponse.error(result.get("message", "Failed to get device status"))

        except Exception as e:
            return self._handle_api_error("get_pupil_device_status", e)
    
    def setup_gaze_mapper(self) -> Dict[str, Any]:
        """Setup gaze mapper with device calibration"""
        try:
            self._log_api_call("setup_gaze_mapper")

            result = pupil_integration.setup_gaze_mapper()
            self.logger.info(f"Gaze mapper setup result: {result.get('success', False)}")

            if result.get("success", False):
                return APIResponse.success(result["message"])
            else:
                return APIResponse.error(result.get("message", "Gaze mapper setup failed"))

        except Exception as e:
            return self._handle_api_error("setup_gaze_mapper", e)
    
    def get_marker_info(self) -> Dict[str, Any]:
        """Get information about AprilTag markers"""
        try:
            self._log_api_call("get_marker_info")
            
            markers = pupil_integration.get_marker_info()
            self.logger.debug(f"Retrieved {len(markers) if markers else 0} markers")
            return APIResponse.success("Marker info retrieved", markers)
            
        except Exception as e:
            return self._handle_api_error("get_marker_info", e)
    
    def generate_marker_image(self, marker_id: int) -> Dict[str, Any]:
        """Generate AprilTag marker image as base64 data URL"""
        try:
            self._log_api_call("generate_marker_image", marker_id=marker_id)
            
            # Validate marker_id
            if not isinstance(marker_id, int) or marker_id < 0:
                return APIResponse.error("Marker ID must be a non-negative integer", "INVALID_MARKER_ID")
            
            marker_bytes = pupil_integration.generate_marker_image(marker_id)
            if marker_bytes:
                # Convert to base64 data URL
                b64_data = base64.b64encode(marker_bytes).decode('utf-8')
                data_url = f"data:image/png;base64,{b64_data}"
                
                self.logger.debug(f"Generated marker image for ID {marker_id}")
                return APIResponse.success("Marker image generated", {"data_url": data_url})
            else:
                return APIResponse.error("Failed to generate marker image", "GENERATION_FAILED")
                
        except Exception as e:
            return self._handle_api_error("generate_marker_image", e)
    
    def save_marker_to_file(self, marker_id):
        """Save AprilTag marker directly to Downloads folder"""
        try:
            from pathlib import Path
            from .apriltag_generator import apriltag_generator
            
            # Get marker bytes using new high-res generator
            marker_bytes = apriltag_generator.generate_marker_image(marker_id, high_res=True)
            if not marker_bytes:
                return {"success": False, "message": "Failed to generate marker image"}
            
            # Get marker info for filename
            markers = pupil_integration.get_marker_info()
            marker_info = next((m for m in markers if m["id"] == marker_id), None)
            if not marker_info:
                return {"success": False, "message": f"Marker {marker_id} not found"}
            
            # Create filename
            filename = f"apriltag_{marker_id}_{marker_info['position']}_highres.png"
            
            # Try to save to Downloads folder
            downloads_path = Path.home() / "Downloads"
            if not downloads_path.exists():
                # Fallback to desktop
                downloads_path = Path.home() / "Desktop"
            
            file_path = downloads_path / filename
            
            # Save the file
            with open(file_path, 'wb') as f:
                f.write(marker_bytes)
            
            return {
                "success": True,
                "message": f"High-res marker saved to {file_path}",
                "file_path": str(file_path)
            }
            
        except Exception as e:
            return {"success": False, "message": f"Error saving marker: {str(e)}"}
    
    def save_all_markers_png_only(self):
        """Save all markers as PNGs only (no PDF)"""
        try:
            from pathlib import Path
            from .apriltag_generator import apriltag_generator
            
            # Create output directory
            downloads_path = Path.home() / "Downloads"
            if not downloads_path.exists():
                downloads_path = Path.home() / "Desktop"
            
            output_dir = downloads_path / "GazeDeck_AprilTags_PNG"
            
            # Save all markers without PDF
            result = apriltag_generator.save_all_markers(output_dir, create_pdf=False)
            
            return result
            
        except Exception as e:
            return {"success": False, "message": f"Error saving PNG markers: {str(e)}"}
    
    def save_all_markers_with_pdf(self):
        """Create PDF sheet for printing (no individual PNGs)"""
        try:
            from pathlib import Path
            from .apriltag_generator import apriltag_generator
            
            # Create output directory
            downloads_path = Path.home() / "Downloads"
            if not downloads_path.exists():
                downloads_path = Path.home() / "Desktop"
            
            output_dir = downloads_path / "GazeDeck_AprilTags_Print"
            
            # Create PDF only (no individual PNGs)
            result = apriltag_generator.create_pdf_only(output_dir)
            
            return result
            
        except Exception as e:
            return {"success": False, "message": f"Error creating PDF: {str(e)}"}
    
    def disconnect_pupil_device(self):
        """Disconnect from Pupil Labs device"""
        try:
            pupil_integration.disconnect()
            return {"success": True, "message": "Disconnected from Pupil Labs device"}
        except Exception as e:
            return {"success": False, "message": f"Error disconnecting: {str(e)}"}
    
    def get_pupil_status(self):
        """Get current Pupil Labs connection status"""
        return {
            "connected": pupil_integration.is_connected,
            "device_info": pupil_integration.device_info.__dict__ if pupil_integration.device_info else None
        }


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
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 14px;
                line-height: 1.5;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #333;
                min-height: 100vh;
            }

            .container {
                max-width: 700px;
                margin: 0 auto;
                padding: 24px;
            }

                        h1 {
                margin: 0 0 8px 0;
                font-size: 2em;
                font-weight: 600;
                color: white;
                text-align: center;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
            }

            .subtitle {
                font-size: 1em;
                color: rgba(255, 255, 255, 0.9);
                margin-bottom: 32px;
                text-align: center;
            }

            .section {
                margin-bottom: 24px;
                padding: 24px;
                background: #f8f9fa;
                border-radius: 8px;
                border: 1px solid #e9ecef;
            }

            .section h3 {
                margin: 0 0 16px 0;
                font-size: 1.25em;
                font-weight: 600;
                color: #1a1a1a;
            }
            
            .form-group {
                margin-bottom: 16px;
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .form-group label {
                min-width: 60px;
                font-size: 1em;
                font-weight: 500;
                color: #1a1a1a;
            }

            .form-group input {
                flex: 1;
                padding: 10px 12px;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background: white;
                color: #1a1a1a;
                font-size: 1em;
                transition: border-color 0.2s ease;
            }

            .form-group input:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
            }

            .form-group input::placeholder {
                color: #6c757d;
            }

            .button {
                background: #6c757d;
                border: 1px solid #6c757d;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 1em;
                font-weight: 500;
                transition: all 0.2s ease;
                margin: 4px;
                text-decoration: none;
                display: inline-block;
                text-align: center;
            }

            .button:hover:not(:disabled) {
                background: #5a6268;
                border-color: #5a6268;
                transform: translateY(-1px);
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }

            .button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }

            .button.primary {
                background: #667eea;
                border-color: #667eea;
            }

            .button.primary:hover:not(:disabled) {
                background: #5a6fd8;
                border-color: #5a6fd8;
            }

            .button.danger {
                background: #dc3545;
                border-color: #dc3545;
            }

            .button.danger:hover:not(:disabled) {
                background: #c82333;
                border-color: #c82333;
            }

            .button.warning {
                background: #ffc107;
                border-color: #ffc107;
                color: #1a1a1a;
            }

            .button.warning:hover:not(:disabled) {
                background: #e0a800;
                border-color: #e0a800;
            }
            
            .status {
                background: #f8f9fa;
                padding: 12px 16px;
                border-radius: 6px;
                margin: 12px 0;
                font-size: 0.9em;
                border: 1px solid #dee2e6;
                color: #666;
            }

            .status.success {
                background: #d4edda;
                border-color: #c3e6cb;
                color: #155724;
            }

            .status.error {
                background: #f8d7da;
                border-color: #f5c6cb;
                color: #721c24;
            }

            .controls {
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
                justify-content: center;
                margin-top: 16px;
            }

            .step-content {
                padding: 8px 0;
            }

            .instruction {
                margin: 16px 0;
                font-style: italic;
                color: #666;
                font-size: 0.95em;
            }
            
            .markers-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 16px;
                margin: 20px 0;
            }

            .marker-card {
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 20px;
                text-align: center;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            }

            .marker-card h4 {
                margin: 0 0 12px 0;
                color: #1a1a1a;
                font-size: 1.1em;
                font-weight: 600;
            }

            .marker-card .marker-description {
                font-size: 0.9em;
                margin: 12px 0;
                color: #666;
            }

            .marker-image {
                width: 140px;
                height: 140px;
                margin: 12px auto;
                background: #f8f9fa;
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                border: 2px solid #dee2e6;
            }

            .marker-image img {
                max-width: 100%;
                max-height: 100%;
            }

            .download-btn {
                background: #28a745;
                border: 1px solid #28a745;
                color: white;
                padding: 10px 16px;
                border-radius: 6px;
                cursor: pointer;
                display: inline-block;
                margin: 4px;
                font-size: 0.9em;
                font-weight: 500;
                transition: all 0.2s ease;
                text-decoration: none;
            }

            .download-btn:hover {
                background: #218838;
                border-color: #218838;
                transform: translateY(-1px);
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }
            
            .device-info {
                background: #d4edda;
                border: 1px solid #c3e6cb;
                border-radius: 8px;
                padding: 16px;
                margin: 16px 0;
            }

            .device-info h4 {
                margin: 0 0 12px 0;
                color: #155724;
                font-size: 1.1em;
                font-weight: 600;
            }

            .device-info .info-item {
                margin: 6px 0;
                font-size: 0.9em;
                color: #155724;
            }

            .gaze-display {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 16px;
                margin: 16px 0;
            }

            .gaze-display h4 {
                margin: 0 0 12px 0;
                color: #1a1a1a;
                font-size: 1.1em;
                font-weight: 600;
            }

            #gazeCoords {
                font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', 'Droid Sans Mono', 'Source Code Pro', monospace;
                font-size: 1.1em;
                color: #667eea;
                font-weight: 500;
                background: #f1f3f4;
                padding: 8px 12px;
                border-radius: 4px;
                border: 1px solid #e9ecef;
            }

            /* Loading Screen Styles */
            .loading-screen {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
            }

            .loading-content {
                text-align: center;
                color: white;
            }

            .loading-content h1 {
                font-size: 3em;
                margin-bottom: 30px;
                font-weight: 600;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
            }

            .loading-spinner {
                width: 60px;
                height: 60px;
                border: 4px solid rgba(255, 255, 255, 0.3);
                border-top: 4px solid white;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 20px auto;
            }

            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }

            .loading-message {
                font-size: 1.4em;
                margin: 20px 0 10px 0;
                font-weight: 500;
            }

            .loading-details {
                font-size: 1em;
                opacity: 0.8;
                margin-bottom: 20px;
            }

            /* Fade animation for transitions */
            .fade-out {
                opacity: 0;
                transition: opacity 0.5s ease-out;
            }

            .fade-in {
                opacity: 1;
                transition: opacity 0.5s ease-in;
            }
        </style>
    </head>
    <body>
        <!-- Loading Screen -->
        <div id="loadingScreen" class="loading-screen">
            <div class="loading-content">
                <h1>GazeDeck</h1>
                <div class="loading-spinner"></div>
                <div id="loadingMessage" class="loading-message">Initializing application...</div>
                <div id="loadingDetails" class="loading-details">Please wait while we set up the interface</div>
            </div>
        </div>

        <!-- Main Application -->
        <div id="mainApp" class="container" style="display: none;">
            <h1>GazeDeck</h1>
            <div class="subtitle">Plane-relative gaze bridge control panel</div>
            
            <!-- Step 1: AprilTag Markers -->
            <div class="section" id="markersSection">
                <h3>🏷️ Step 1: AprilTag Markers Setup</h3>
                <div class="step-content">
                    <div id="markersStatus" class="status">Download the markers and place them on your screen corners</div>
                    <p class="instruction">Download and place these AprilTag markers on your screen corners:</p>
                    <div id="markersList" class="markers-grid"></div>
                    <div class="controls">
                        <button class="button primary" onclick="saveAllMarkersAsPNG()">💾 Download as PNGs for Digital</button>
                        <button class="button primary" onclick="saveAllMarkersWithPDF()">📄 Download as PDF for Print</button>
                        <button class="button primary" id="markersReadyBtn" onclick="markersReady()">✅ Markers Placed - Continue to Device Setup</button>
                    </div>
                </div>
            </div>

            <!-- Step 2: Pupil Labs Connection -->
            <div class="section" id="pupilSection" style="display: none;">
                <h3>📋 Step 2: Pupil Labs Connection</h3>
                <div class="step-content">
                    <div id="pupilAvailabilityStatus" class="status">Checking Pupil Labs libraries...</div>
                    <div class="controls" id="pupilConnectionControls" style="display: none;">
                        <button class="button primary" id="discoverBtn" onclick="discoverPupilDevice()">🔍 Discover Pupil Device</button>
                        <button class="button danger" id="disconnectBtn" onclick="disconnectPupilDevice()" disabled>❌ Disconnect</button>
                    </div>
                    <div id="pupilDeviceInfo" class="device-info" style="display: none;"></div>
                </div>
            </div>

            <!-- Step 3: Gaze Mapping Setup -->
            <div class="section" id="gazeMapperSection" style="display: none;">
                <h3>🎯 Step 3: Initialize Gaze Mapping</h3>
                <div class="step-content">
                    <p class="instruction">Initialize gaze mapping with your Pupil Labs device and AprilTag markers:</p>
                    <div class="controls">
                        <button class="button primary" id="setupGazeMapperBtn" onclick="setupGazeMapper()">✅ Initialize Gaze Mapping</button>
                    </div>
                    <div id="gazeMapperStatus" class="status">Ready to initialize gaze mapping</div>
                </div>
            </div>

            <!-- Step 4: WebSocket Server -->
            <div class="section" id="serverSection" style="display: none;">
                <h3>🌐 Step 4: WebSocket Server Configuration</h3>
                <div class="form-group">
                    <label>Host:</label>
                    <input type="text" id="host" placeholder="localhost">
                </div>
                <div class="form-group">
                    <label>Port:</label>
                    <input type="number" id="port" placeholder="8765">
                </div>
                <button class="button" onclick="updateConfig()">Update Config</button>
                <div class="controls">
                    <button class="button primary" id="startBtn" onclick="startServer()">🚀 Start Server</button>
                    <button class="button danger" id="stopBtn" onclick="stopServer()" disabled>⏹️ Stop Server</button>
                </div>
                <div id="serverStatus" class="status">Server stopped</div>
            </div>
            
            <!-- Step 5: Live Gaze Tracking -->
            <div class="section" id="gazeSection" style="display: none;">
                <h3>👁️ Step 5: Live Gaze Tracking</h3>
                <div class="controls">
                    <button class="button warning" id="fixationBtn" onclick="triggerFixation()">🎯 Trigger Test Fixation</button>
                    <button class="button primary" id="startGazeBtn" onclick="startGazeTracking()" disabled>▶️ Start Live Gaze</button>
                    <button class="button danger" id="stopGazeBtn" onclick="stopGazeTracking()" disabled>⏸️ Stop Live Gaze</button>
                </div>
                <div id="gazeStatus" class="status">Ready for gaze tracking</div>
                <div id="gazeDisplay" class="gaze-display" style="display: none;">
                    <h4>Live Gaze Coordinates:</h4>
                    <div id="gazeCoords">Waiting for gaze data...</div>
                </div>
            </div>
        </div>
        
        <script>
            // Global error handler for JavaScript errors
            window.addEventListener('error', function(event) {
                const errorInfo = {
                    message: event.message,
                    source: event.filename,
                    lineno: event.lineno,
                    colno: event.colno,
                    stack: event.error ? event.error.stack : 'No stack trace available'
                };
                
                console.error('JavaScript Error:', errorInfo);
                
                // Log to Python backend if available
                if (window.pywebview && window.pywebview.api && window.pywebview.api.log_js_error) {
                    window.pywebview.api.log_js_error(errorInfo).catch(err => {
                        console.error('Failed to log error to backend:', err);
                    });
                }
            });
            
            // Handle unhandled promise rejections
            window.addEventListener('unhandledrejection', function(event) {
                const errorInfo = {
                    message: 'Unhandled Promise Rejection: ' + (event.reason ? event.reason.toString() : 'Unknown'),
                    source: 'Promise',
                    lineno: 'N/A',
                    colno: 'N/A',
                    stack: event.reason && event.reason.stack ? event.reason.stack : 'No stack trace available'
                };
                
                console.error('Unhandled Promise Rejection:', errorInfo);
                
                // Log to Python backend if available
                if (window.pywebview && window.pywebview.api && window.pywebview.api.log_js_error) {
                    window.pywebview.api.log_js_error(errorInfo).catch(err => {
                        console.error('Failed to log promise rejection to backend:', err);
                    });
                }
            });

            // Application state
            let config = {};
            let pupilConnected = false;
            let gazeMapperReady = false;
            let gazeTrackingActive = false;
            let debugMode = false;
            let appInitialized = false;

            // Loading screen management
            const LoadingManager = {
                updateMessage: function(message, details = null) {
                    try {
                        const messageEl = document.getElementById('loadingMessage');
                        const detailsEl = document.getElementById('loadingDetails');
                        
                        if (messageEl) {
                            messageEl.textContent = message;
                        } else {
                            // Fallback if elements don't exist yet
                            const loadingMessageEl = document.querySelector('.loading-message');
                            const loadingDetailsEl = document.querySelector('.loading-details');
                            if (loadingMessageEl) loadingMessageEl.textContent = message;
                            if (loadingDetailsEl && details) loadingDetailsEl.textContent = details;
                        }
                        
                        if (details && detailsEl) {
                            detailsEl.textContent = details;
                        }
                        
                        console.log(`Loading: ${message}${details ? ' - ' + details : ''}`);
                    } catch (error) {
                        console.error('Error updating loading message:', error);
                    }
                },

                hideLoading: function() {
                    try {
                        const loadingScreen = document.getElementById('loadingScreen');
                        const mainApp = document.getElementById('mainApp');
                        
                        if (loadingScreen && mainApp) {
                            // Fade out loading screen
                            loadingScreen.classList.add('fade-out');
                            
                            setTimeout(() => {
                                loadingScreen.style.display = 'none';
                                mainApp.style.display = 'block';
                                mainApp.classList.add('fade-in');
                                appInitialized = true;
                                console.log('Application fully initialized and visible');
                            }, 500);
                        }
                    } catch (error) {
                        console.error('Error hiding loading screen:', error);
                        // Fallback - just hide loading and show main app
                        const loadingScreen = document.getElementById('loadingScreen');
                        const mainApp = document.getElementById('mainApp');
                        if (loadingScreen) loadingScreen.style.display = 'none';
                        if (mainApp) mainApp.style.display = 'block';
                        appInitialized = true;
                    }
                },

                showError: function(message, details = null) {
                    try {
                        const loadingContent = document.querySelector('.loading-content');
                        if (loadingContent) {
                            loadingContent.innerHTML = `
                                <h1>GazeDeck</h1>
                                <div style="color: #ff6b6b; font-size: 1.5em; margin: 20px 0;">⚠️ Initialization Error</div>
                                <div style="font-size: 1.2em; margin-bottom: 10px;">${message}</div>
                                ${details ? `<div style="font-size: 0.9em; opacity: 0.8;">${details}</div>` : ''}
                                <button onclick="location.reload()" style="margin-top: 20px; padding: 10px 20px; background: white; color: #667eea; border: none; border-radius: 6px; cursor: pointer; font-size: 1em;">
                                    🔄 Retry
                                </button>
                            `;
                        }
                    } catch (error) {
                        console.error('Error showing loading error:', error);
                    }
                }
            };
            
            // Utility function for safe API calls
            async function safeApiCall(methodName, ...args) {
                try {
                    if (!window.pywebview || !window.pywebview.api) {
                        throw new Error('PyWebView API not available');
                    }
                    
                    const method = window.pywebview.api[methodName];
                    if (typeof method !== 'function') {
                        throw new Error(`API method '${methodName}' not found`);
                    }
                    
                    if (debugMode) {
                        console.log(`API Call: ${methodName}`, args);
                    }
                    
                    const result = await method(...args);
                    
                    if (debugMode) {
                        console.log(`API Result: ${methodName}`, result);
                    }
                    
                    return result;
                    
                } catch (error) {
                    console.error(`API call failed: ${methodName}`, error);
                    
                    // Return a standardized error response
                    return {
                        success: false,
                        message: `API call failed: ${error.message}`,
                        error_code: 'API_CALL_FAILED'
                    };
                }
            }
            
            // Utility function to safely show messages
            function showMessage(elementId, message, success = true) {
                try {
                    const element = document.getElementById(elementId);
                    if (element) {
                        element.textContent = message;
                        element.className = success ? 'status success' : 'status error';
                    } else {
                        console.warn(`Element with ID '${elementId}' not found`);
                    }
                } catch (error) {
                    console.error('Error showing message:', error);
                }
            }
            
            // Utility function for safe DOM manipulation
            function safeSetElementProperty(elementId, property, value) {
                try {
                    const element = document.getElementById(elementId);
                    if (element && property in element) {
                        element[property] = value;
                        return true;
                    } else {
                        console.warn(`Element '${elementId}' not found or property '${property}' not available`);
                        return false;
                    }
                } catch (error) {
                    console.error(`Error setting ${property} on element ${elementId}:`, error);
                    return false;
                }
            }
            
            // Utility function for safe event listener addition
            function safeAddEventListener(elementId, event, handler) {
                try {
                    const element = document.getElementById(elementId);
                    if (element) {
                        element.addEventListener(event, handler);
                        return true;
                    } else {
                        console.warn(`Element '${elementId}' not found for event '${event}'`);
                        return false;
                    }
                } catch (error) {
                    console.error(`Error adding ${event} listener to element ${elementId}:`, error);
                    return false;
                }
            }
            
            // Button state management utilities
            const ButtonUtils = {
                disable: function(buttonId, loadingText = null) {
                    try {
                        const btn = document.getElementById(buttonId);
                        if (btn) {
                            btn.disabled = true;
                            if (loadingText) {
                                btn.dataset.originalText = btn.textContent;
                                btn.textContent = loadingText;
                            }
                        }
                    } catch (error) {
                        console.error(`Error disabling button ${buttonId}:`, error);
                    }
                },
                
                enable: function(buttonId, restoreText = false) {
                    try {
                        const btn = document.getElementById(buttonId);
                        if (btn) {
                            btn.disabled = false;
                            if (restoreText && btn.dataset.originalText) {
                                btn.textContent = btn.dataset.originalText;
                                delete btn.dataset.originalText;
                            }
                        }
                    } catch (error) {
                        console.error(`Error enabling button ${buttonId}:`, error);
                    }
                },
                
                setLoading: function(buttonId, loadingText) {
                    this.disable(buttonId, loadingText);
                },
                
                clearLoading: function(buttonId) {
                    this.enable(buttonId, true);
                }
            };
            
            // Load initial setup on page load
            window.addEventListener('DOMContentLoaded', async function() {
                try {
                    await initializeApp();
                } catch (error) {
                    console.error('Failed to initialize app:', error);
                    LoadingManager.showError('Failed to initialize application', error.message);
                }
            });
            
            async function waitForPyWebViewAPI(maxAttempts = 20, delayMs = 500) {
                LoadingManager.updateMessage('Connecting to backend...', 'Waiting for PyWebView API');
                
                for (let attempt = 1; attempt <= maxAttempts; attempt++) {
                    if (window.pywebview && window.pywebview.api) {
                        LoadingManager.updateMessage('Backend connected!', 'PyWebView API ready');
                        return true;
                    }
                    
                    if (attempt < maxAttempts) {
                        LoadingManager.updateMessage('Connecting to backend...', `Attempt ${attempt}/${maxAttempts}`);
                        await new Promise(resolve => setTimeout(resolve, delayMs));
                    }
                }
                
                throw new Error('PyWebView API not available after maximum attempts');
            }
            
            async function initializeApp() {
                try {
                    LoadingManager.updateMessage('Starting GazeDeck...', 'Initializing application components');
                    
                    // Step 1: Wait for PyWebView API to be ready
                    await waitForPyWebViewAPI();
                    
                    // Step 2: Load configuration
                    LoadingManager.updateMessage('Loading configuration...', 'Retrieving app settings');
                    await loadConfig();
                    
                    // Step 3: Load AprilTag markers
                    LoadingManager.updateMessage('Loading markers...', 'Generating AprilTag markers');
                    await loadMarkers();
                    
                    // Step 4: Finalize initialization
                    LoadingManager.updateMessage('Finalizing setup...', 'Almost ready!');
                    
                    // Small delay to show the final message
                    await new Promise(resolve => setTimeout(resolve, 500));
                    
                    // Hide loading screen and show main app
                    LoadingManager.hideLoading();
                    
                    console.log('Application initialized successfully');
                    
                } catch (error) {
                    console.error('Error during app initialization:', error);
                    LoadingManager.showError('Application initialization failed', error.message);
                }
            }
            
            async function checkPupilAvailability() {
                const statusEl = document.getElementById('pupilAvailabilityStatus');
                
                // Check if pywebview API is available
                if (!window.pywebview || !window.pywebview.api) {
                    console.log('PyWebView API not ready, retrying in 500ms...');
                    showMessage('pupilAvailabilityStatus', '⏳ Initializing...', true);
                    setTimeout(checkPupilAvailability, 500);
                    return;
                }
                
                try {
                    const result = await safeApiCall('check_pupil_availability');
                    
                    if (result.success) {
                        if (result.data && result.data.available) {
                            showMessage('pupilAvailabilityStatus', '✅ ' + result.message, true);
                            document.getElementById('pupilConnectionControls').style.display = 'block';
                        } else {
                            showMessage('pupilAvailabilityStatus', '❌ ' + result.message, false);
                        }
                    } else {
                        showMessage('pupilAvailabilityStatus', '❌ ' + result.message, false);
                    }
                } catch (error) {
                    console.error('Error checking Pupil availability:', error);
                    showMessage('pupilAvailabilityStatus', '❌ Error checking Pupil Labs libraries', false);
                }
            }
            
            async function discoverPupilDevice() {
                const discoverBtn = document.getElementById('discoverBtn');
                const disconnectBtn = document.getElementById('disconnectBtn');
                
                discoverBtn.disabled = true;
                discoverBtn.textContent = '🔍 Searching...';
                
                try {
                    const result = await window.pywebview.api.discover_pupil_device();
                    
                    if (result.success) {
                        pupilConnected = true;
                        discoverBtn.disabled = true;
                        disconnectBtn.disabled = false;

                        // Show device info
                        showDeviceInfo(result.data);

                        // Show Step 3: Gaze Mapping Setup
                        document.getElementById('gazeMapperSection').style.display = 'block';

                        showMessage('pupilAvailabilityStatus', '✅ ' + result.message, true);
                    } else {
                        discoverBtn.disabled = false;
                        discoverBtn.textContent = '🔍 Discover Pupil Device';
                        showMessage('pupilAvailabilityStatus', '❌ ' + result.message, false);
                    }
                } catch (error) {
                    console.error('Error discovering device:', error);
                    discoverBtn.disabled = false;
                    discoverBtn.textContent = '🔍 Discover Pupil Device';
                    showMessage('pupilAvailabilityStatus', '❌ Error discovering device', false);
                }
            }
            
            async function disconnectPupilDevice() {
                try {
                    const result = await window.pywebview.api.disconnect_pupil_device();
                    
                    pupilConnected = false;
                    gazeMapperReady = false;
                    gazeTrackingActive = false;
                    
                    document.getElementById('discoverBtn').disabled = false;
                    document.getElementById('disconnectBtn').disabled = true;
                    document.getElementById('pupilDeviceInfo').style.display = 'none';
                    document.getElementById('gazeMapperSection').style.display = 'none';
                    document.getElementById('serverSection').style.display = 'none';
                    document.getElementById('gazeSection').style.display = 'none';
                    
                    showMessage('pupilAvailabilityStatus', '🔌 Disconnected from device', false);
                } catch (error) {
                    console.error('Error disconnecting:', error);
                }
            }
            
            function showDeviceInfo(deviceInfo) {
                const infoEl = document.getElementById('pupilDeviceInfo');
                infoEl.innerHTML = `
                    <h4>📱 Connected Device</h4>
                    <div class="info-item"><strong>Type:</strong> ${deviceInfo.type}</div>
                    <div class="info-item"><strong>Name:</strong> ${deviceInfo.name}</div>
                    <div class="info-item"><strong>Serial:</strong> ${deviceInfo.serial}</div>
                    ${deviceInfo.battery !== null ? `<div class="info-item"><strong>Battery:</strong> ${deviceInfo.battery}%</div>` : ''}
                `;
                infoEl.style.display = 'block';
            }
            
            async function loadMarkers() {
                try {
                    // Get marker info first
                    const markerInfoResult = await safeApiCall('get_marker_info');
                    
                    if (!markerInfoResult.success) {
                        throw new Error(markerInfoResult.message || 'Failed to get marker info');
                    }
                    
                    const markers = markerInfoResult.data;
                    if (!markers || !Array.isArray(markers)) {
                        throw new Error('Invalid marker data received');
                    }
                    
                    const markersListEl = document.getElementById('markersList');
                    if (!markersListEl) {
                        throw new Error('Markers list element not found');
                    }
                    
                    markersListEl.innerHTML = '';
                    
                    // Arrange markers in logical screen positions (2x2 grid)
                    const markerOrder = [0, 1, 3, 2]; // top-left, top-right, bottom-left, bottom-right
                    
                    for (const markerId of markerOrder) {
                        const marker = markers.find(m => m.id === markerId);
                        if (!marker) {
                            console.warn(`Marker with ID ${markerId} not found`);
                            continue;
                        }
                        
                        const markerCard = document.createElement('div');
                        markerCard.className = 'marker-card';
                        
                        // Generate marker image
                        if (debugMode) {
                            console.log(`Generating marker image for marker ${marker.id}`);
                        }
                        
                        const imageResult = await safeApiCall('generate_marker_image', marker.id);
                        
                        if (debugMode) {
                            console.log(`Marker ${marker.id} generation result:`, { 
                                success: imageResult.success, 
                                hasDataUrl: !!(imageResult.data && imageResult.data.data_url),
                                dataUrlStart: (imageResult.data && imageResult.data.data_url) ? 
                                    imageResult.data.data_url.substring(0, 50) : 'N/A'
                            });
                        }
                        
                        const imageUrl = (imageResult.success && imageResult.data && imageResult.data.data_url) ? 
                            imageResult.data.data_url : null;
                        
                        markerCard.innerHTML = `
                            <h4>ID ${marker.id} - ${marker.position.replace('-', ' ').toUpperCase()}</h4>
                            <div class="marker-image">
                                ${imageUrl ? 
                                    `<img src="${imageUrl}" alt="Marker ${marker.id}">` : 
                                    '<div style="color: #666; padding: 20px;">Preview will be available after download</div>'
                                }
                            </div>
                            <div class="marker-description">${marker.description}</div>
                        `;
                        
                        markersListEl.appendChild(markerCard);
                    }
                    
                    showMessage('markersStatus', '✅ Markers ready - download and place them on your screen', true);
                    
                } catch (error) {
                    console.error('Error loading markers:', error);
                    showMessage('markersStatus', '❌ Error loading markers: ' + error.message, false);
                    throw error; // Re-throw to be caught by initialization
                }
            }
            

            

            
            async function saveAllMarkersAsPNG() {
                console.log('Saving all markers as PNGs...');
                
                const btnId = event.target.id || 'saveAllPngBtn';
                
                try {
                    // Show loading state
                    ButtonUtils.setLoading(btnId, '⏳ Creating PNGs...');
                    
                    const result = await safeApiCall('save_all_markers_png_only');
                    
                    if (result.success) {
                        const fileCount = result.data && result.data.files ? result.data.files.length : 0;
                        alert(`✅ ${result.message}\\n\\nSaved ${fileCount} PNG files for digital use!`);
                        console.log('All PNG markers saved successfully:', result);
                    } else {
                        alert(`❌ Failed to save PNG markers: ${result.message}`);
                        console.error('Failed to save PNG markers:', result);
                    }
                } catch (error) {
                    console.error('Error saving PNG markers:', error);
                    alert(`❌ Error saving PNG markers: ${error.message}`);
                } finally {
                    // Restore button state
                    ButtonUtils.clearLoading(btnId);
                }
            }
            
            async function saveAllMarkersWithPDF() {
                console.log('Saving PDF for printing...');
                
                // Show loading state
                const btn = event.target;
                const originalText = btn.textContent;
                btn.textContent = '⏳ Creating PDF...';
                btn.disabled = true;
                
                try {
                    const result = await window.pywebview.api.save_all_markers_with_pdf();
                    
                    if (result.success) {
                        alert(`✅ PDF created for printing!\\n\\n${result.message}`);
                        console.log('PDF saved successfully:', result);
                    } else {
                        alert(`❌ Failed to create PDF: ${result.message}`);
                        console.error('Failed to create PDF:', result);
                    }
                } catch (error) {
                    console.error('Error creating PDF:', error);
                    alert(`❌ Error creating PDF: ${error.message}`);
                } finally {
                    // Restore button state
                    btn.textContent = originalText;
                    btn.disabled = false;
                }
            }
            
            function downloadMarker(dataUrl, filename) {
                console.log('downloadMarker called with:', { dataUrl: dataUrl.substring(0, 50) + '...', filename });
                
                try {
                    // Debug: Check if dataUrl is valid
                    if (!dataUrl || !dataUrl.startsWith('data:')) {
                        console.error('Invalid dataUrl:', dataUrl);
                        alert('Invalid image data for download');
                        return;
                    }
                    
                    // Method 1: Try direct link download
                    console.log('Attempting Method 1: Direct link download');
                    const link = document.createElement('a');
                    link.href = dataUrl;
                    link.download = filename;
                    link.style.display = 'none';
                    
                    // Append to document, click, and remove
                    document.body.appendChild(link);
                    console.log('Link created and appended, attempting click...');
                    link.click();
                    document.body.removeChild(link);
                    
                    console.log(`Method 1 completed for: ${filename}`);
                    
                    // Show success message
                    alert(`Download initiated for ${filename}. Check your Downloads folder.`);
                    
                } catch (error) {
                    console.error('Method 1 failed, trying Method 2:', error);
                    
                    try {
                        // Method 2: Try using URL.createObjectURL with blob
                        console.log('Attempting Method 2: Blob download');
                        
                        // Convert base64 to blob
                        const base64Data = dataUrl.split(',')[1];
                        const byteCharacters = atob(base64Data);
                        const byteNumbers = new Array(byteCharacters.length);
                        
                        for (let i = 0; i < byteCharacters.length; i++) {
                            byteNumbers[i] = byteCharacters.charCodeAt(i);
                        }
                        
                        const byteArray = new Uint8Array(byteNumbers);
                        const blob = new Blob([byteArray], {type: 'image/png'});
                        
                        const url = URL.createObjectURL(blob);
                        const link = document.createElement('a');
                        link.href = url;
                        link.download = filename;
                        link.style.display = 'none';
                        
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                        
                        // Clean up the object URL
                        URL.revokeObjectURL(url);
                        
                        console.log(`Method 2 completed for: ${filename}`);
                        alert(`Download completed using Method 2 for ${filename}`);
                        
                    } catch (error2) {
                        console.error('Both methods failed:', error2);
                        alert(`Download failed for ${filename}. Error: ${error2.message}`);
                        
                        // Method 3: Fallback - open in new tab
                        console.log('Attempting Method 3: Open in new tab');
                        window.open(dataUrl, '_blank');
                    }
                }
            }
            
            function markersReady() {
                // Show Step 2: Pupil Labs Connection
                document.getElementById('pupilSection').style.display = 'block';
                
                // Check Pupil Labs availability
                checkPupilAvailability();
                
                showMessage('markersStatus', '✅ Proceeding to device connection...', true);
            }
            
            async function setupGazeMapper() {
                const setupBtn = document.getElementById('setupGazeMapperBtn');
                setupBtn.disabled = true;
                setupBtn.textContent = '⏳ Setting up gaze mapping...';
                
                try {
                    const result = await window.pywebview.api.setup_gaze_mapper();
                    
                    if (result.success) {
                        gazeMapperReady = true;
                        showMessage('gazeMapperStatus', '✅ ' + result.message, true);
                        
                        // Show Step 4: Server
                        document.getElementById('serverSection').style.display = 'block';
                        
                        setupBtn.textContent = '✅ Gaze Mapping Ready';
                    } else {
                        setupBtn.disabled = false;
                        setupBtn.textContent = '✅ Setup Complete - Initialize Gaze Mapping';
                        showMessage('gazeMapperStatus', '❌ ' + result.message, false);
                    }
                } catch (error) {
                    console.error('Error setting up gaze mapper:', error);
                    setupBtn.disabled = false;
                    setupBtn.textContent = '✅ Setup Complete - Initialize Gaze Mapping';
                    showMessage('gazeMapperStatus', '❌ Error setting up gaze mapping', false);
                }
            }
            
            async function loadConfig() {
                try {
                    // Wait for pywebview API to be ready
                    if (!window.pywebview || !window.pywebview.api) {
                        console.log('PyWebView API not ready for config, using defaults...');
                        config = {
                            host: 'localhost',
                            port: 8765,
                            server_running: false,
                            debug_mode: false
                        };
                        return;
                    }
                    
                    const result = await safeApiCall('get_config');
                    
                    if (result.success && result.data) {
                        config = result.data;
                        debugMode = config.debug_mode || false;
                        
                        // Update UI elements if they exist
                        const hostEl = document.getElementById('host');
                        const portEl = document.getElementById('port');
                        if (hostEl) hostEl.value = config.host;
                        if (portEl) portEl.value = config.port;
                        
                        if (debugMode) {
                            console.log('Debug mode enabled');
                        }
                    } else {
                        console.warn('Failed to load config, using defaults');
                        config = {
                            host: 'localhost',
                            port: 8765,
                            server_running: false,
                            debug_mode: false
                        };
                    }
                } catch (error) {
                    console.error('Error loading config:', error);
                    config = {
                        host: 'localhost',
                        port: 8765,
                        server_running: false,
                        debug_mode: false
                    };
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
                        document.getElementById('startBtn').disabled = true;
                        document.getElementById('stopBtn').disabled = false;
                        
                        // Show Step 5: Gaze Tracking
                        document.getElementById('gazeSection').style.display = 'block';
                        document.getElementById('startGazeBtn').disabled = false;
                        
                        setTimeout(async () => {
                            await loadConfig();
                            showMessage('serverStatus', `✅ Server running on ${config.host}:${config.port}`, true);
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
                        document.getElementById('startBtn').disabled = false;
                        document.getElementById('stopBtn').disabled = true;
                        document.getElementById('startGazeBtn').disabled = true;
                        document.getElementById('stopGazeBtn').disabled = true;
                        
                        if (gazeTrackingActive) {
                            stopGazeTracking();
                        }
                    }
                } catch (error) {
                    console.error('Stop server error:', error);
                    showMessage('serverStatus', 'Failed to stop server', false);
                }
            }
            
            async function triggerFixation() {
                try {
                    const result = await window.pywebview.api.trigger_fixation();
                    showMessage('gazeStatus', result.message, result.success);
                } catch (error) {
                    console.error('Trigger fixation error:', error);
                    showMessage('gazeStatus', 'Failed to trigger fixation', false);
                }
            }
            
            function startGazeTracking() {
                // TODO: Implement live gaze tracking
                gazeTrackingActive = true;
                document.getElementById('startGazeBtn').disabled = true;
                document.getElementById('stopGazeBtn').disabled = false;
                document.getElementById('gazeDisplay').style.display = 'block';
                
                showMessage('gazeStatus', '▶️ Live gaze tracking started', true);
                document.getElementById('gazeCoords').textContent = 'Live gaze tracking - implementation pending...';
            }
            
            function stopGazeTracking() {
                gazeTrackingActive = false;
                document.getElementById('startGazeBtn').disabled = false;
                document.getElementById('stopGazeBtn').disabled = true;
                document.getElementById('gazeDisplay').style.display = 'none';
                
                showMessage('gazeStatus', '⏸️ Live gaze tracking stopped', false);
            }
            
            function showMessage(elementId, message, success) {
                const element = document.getElementById(elementId);
                if (element) {
                    element.textContent = message;
                    element.className = success ? 'status success' : 'status error';
                }
            }
        </script>
    </body>
    </html>
    """


class GUIManager:
    """Manager for the GUI window and lifecycle"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.api = None
        self.window = None
        
    def setup_logging(self):
        """Setup logging configuration for GUI"""
        # Configure logging for GUI if not already configured
        if not logging.getLogger().handlers:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.StreamHandler(),
                    logging.FileHandler('gazedeck_gui.log', encoding='utf-8')
                ]
            )
        
        # Set debug level based on config
        debug_mode = config.get('gui.debug_mode', False)
        if debug_mode:
            logging.getLogger(__name__).setLevel(logging.DEBUG)
            self.logger.debug("Debug mode enabled for GUI")
    
    def create_api(self) -> GazedeckAPI:
        """Create and configure the API instance"""
        try:
            self.api = GazedeckAPI()
            self.logger.info("API instance created successfully")
            return self.api
        except Exception as e:
            self.logger.error(f"Failed to create API instance: {e}")
            raise
    
    def get_window_config(self) -> Dict[str, Any]:
        """Get window configuration from config or defaults"""
        return {
            'title': config.get('gui.window_title', 'GazeDeck Control Panel'),
            'width': config.get('gui.window_width', 800),
            'height': config.get('gui.window_height', 700),
            'min_size': tuple(config.get('gui.min_size', [600, 500])),
            'resizable': config.get('gui.resizable', True),
            'shadow': config.get('gui.shadow', True),
            'on_top': config.get('gui.on_top', False),
            'maximized': config.get('gui.maximized', False),
            'fullscreen': config.get('gui.fullscreen', False)
        }
    
    def create_window(self):
        """Create the webview window"""
        try:
            html_content = get_html_content()
            window_config = self.get_window_config()
            
            self.logger.info(f"Creating window with config: {window_config}")
            
            # Create the webview window with js_api
            self.window = webview.create_window(
                html=html_content,
                js_api=self.api,
                **window_config
            )
            
            self.logger.info("Window created successfully")
            return self.window
            
        except Exception as e:
            self.logger.error(f"Failed to create window: {e}")
            raise
    
    def start_gui(self):
        """Start the GUI application"""
        try:
            self.setup_logging()
            self.logger.info("Starting GazeDeck GUI...")
            
            # Create API instance
            self.create_api()
            
            # Create window
            self.create_window()
            
            # Start webview with appropriate debug setting
            debug_mode = config.get('gui.debug_mode', False)
            self.logger.info(f"Starting webview (debug={debug_mode})")
            
            webview.start(debug=debug_mode)
            
        except Exception as e:
            self.logger.error(f"Failed to start GUI: {e}")
            raise


def create_gui():
    """Create and show the GUI window"""
    gui_manager = GUIManager()
    gui_manager.start_gui()


if __name__ == "__main__":
    create_gui()
