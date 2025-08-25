"""Simple HTML GUI for GazeDeck using pywebview"""

import webview
import os
import random
import base64
from pathlib import Path
from .websocket_server import websocket_server
from .config import config
from .pupil_integration import pupil_integration


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
    
    # Pupil Labs Integration Methods
    
    def check_pupil_availability(self):
        """Check if Pupil Labs libraries are available"""
        return pupil_integration.check_pupil_availability()
    
    def discover_pupil_device(self):
        """Discover and connect to Pupil Labs device"""
        timeout = config.get('pupil.device_timeout', 10)
        return pupil_integration.discover_device(timeout)
    
    def setup_gaze_mapper(self):
        """Setup gaze mapper with device calibration"""
        return pupil_integration.setup_gaze_mapper()
    
    def get_marker_info(self):
        """Get information about AprilTag markers"""
        return pupil_integration.get_marker_info()
    
    def generate_marker_image(self, marker_id):
        """Generate AprilTag marker image as base64 data URL"""
        try:
            marker_bytes = pupil_integration.generate_marker_image(marker_id)
            if marker_bytes:
                # Convert to base64 data URL
                b64_data = base64.b64encode(marker_bytes).decode('utf-8')
                return {
                    "success": True,
                    "data_url": f"data:image/png;base64,{b64_data}"
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to generate marker image"
                }
        except Exception as e:
            return {"success": False, "message": f"Error generating marker: {str(e)}"}
    
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
        """Save all markers as PNGs and create a PDF sheet for printing"""
        try:
            from pathlib import Path
            from .apriltag_generator import apriltag_generator
            
            # Create output directory
            downloads_path = Path.home() / "Downloads"
            if not downloads_path.exists():
                downloads_path = Path.home() / "Desktop"
            
            output_dir = downloads_path / "GazeDeck_AprilTags_Print"
            
            # Save all markers and create PDF
            result = apriltag_generator.save_all_markers(output_dir, create_pdf=True)
            
            return result
            
        except Exception as e:
            return {"success": False, "message": f"Error saving markers with PDF: {str(e)}"}
    
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
            
            .step-content {
                padding: 10px 0;
            }
            
            .instruction {
                margin: 15px 0;
                font-style: italic;
                color: rgba(255, 255, 255, 0.9);
            }
            
            .markers-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }
            
            .marker-card {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 15px;
                text-align: center;
            }
            
            .marker-card h4 {
                margin: 0 0 10px 0;
                color: #fff;
            }
            
            .marker-card .marker-description {
                font-size: 0.9em;
                margin: 10px 0;
                opacity: 0.8;
            }
            
            .marker-image {
                width: 120px;
                height: 120px;
                margin: 10px auto;
                background: white;
                border-radius: 4px;
                display: flex;
                align-items: center;
                justify-content: center;
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
            
            .marker-image img {
                max-width: 100%;
                max-height: 100%;
            }
            
            .download-btn {
                background: rgba(33, 150, 243, 0.8);
                border: 1px solid rgba(33, 150, 243, 1);
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                display: inline-block;
                margin: 5px;
                font-size: 0.9em;
                transition: all 0.3s ease;
            }
            
            .download-btn:hover {
                background: rgba(33, 150, 243, 1);
                transform: translateY(-1px);
            }
            
            .device-info {
                background: rgba(76, 175, 80, 0.2);
                border: 1px solid rgba(76, 175, 80, 0.5);
                border-radius: 8px;
                padding: 15px;
                margin: 15px 0;
            }
            
            .device-info h4 {
                margin: 0 0 10px 0;
                color: #4CAF50;
            }
            
            .device-info .info-item {
                margin: 5px 0;
                font-size: 0.95em;
            }
            
            .gaze-display {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 15px;
                margin: 15px 0;
            }
            
            .gaze-display h4 {
                margin: 0 0 10px 0;
                color: #fff;
            }
            
            #gazeCoords {
                font-family: 'Courier New', monospace;
                font-size: 1.1em;
                color: #4CAF50;
            }
        </style>
    </head>
    <body>
        <div class="container">
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
                        <button class="button" onclick="saveAllMarkersAsPNG()" style="background: rgba(33, 150, 243, 0.8);">💾 Download as PNGs for Digital</button>
                        <button class="button" onclick="saveAllMarkersWithPDF()" style="background: rgba(156, 39, 176, 0.8);">📄 Download as PDF for Print</button>
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
            let config = {};
            let pupilConnected = false;
            let gazeMapperReady = false;
            let gazeTrackingActive = false;
            
            // Load initial setup on page load
            window.addEventListener('DOMContentLoaded', async function() {
                await initializeApp();
            });
            
            async function initializeApp() {
                // Step 1: Load AprilTag markers immediately
                await loadMarkers();
                
                // Load basic config
                await loadConfig();
            }
            
            async function checkPupilAvailability() {
                const statusEl = document.getElementById('pupilAvailabilityStatus');
                
                // Check if pywebview API is available
                if (!window.pywebview || !window.pywebview.api) {
                    console.log('PyWebView API not ready, retrying in 500ms...');
                    statusEl.textContent = '⏳ Initializing...';
                    statusEl.className = 'status';
                    setTimeout(checkPupilAvailability, 500);
                    return;
                }
                
                try {
                    const result = await window.pywebview.api.check_pupil_availability();
                    
                    if (result.available) {
                        statusEl.textContent = '✅ ' + result.message;
                        statusEl.className = 'status success';
                        document.getElementById('pupilConnectionControls').style.display = 'block';
                    } else {
                        statusEl.textContent = '❌ ' + result.message;
                        statusEl.className = 'status error';
                    }
                } catch (error) {
                    console.error('Error checking Pupil availability:', error);
                    statusEl.textContent = '❌ Error checking Pupil Labs libraries: ' + error.message;
                    statusEl.className = 'status error';
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
                        showDeviceInfo(result.device_info);
                        
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
                // Wait for pywebview API to be ready
                if (!window.pywebview || !window.pywebview.api) {
                    console.log('PyWebView API not ready for markers, retrying in 500ms...');
                    showMessage('markersStatus', '⏳ Loading markers...', false);
                    setTimeout(loadMarkers, 500);
                    return;
                }
                
                try {
                    const markers = await window.pywebview.api.get_marker_info();
                    const markersListEl = document.getElementById('markersList');
                    
                    markersListEl.innerHTML = '';
                    
                    // Arrange markers in logical screen positions (2x2 grid)
                    const markerOrder = [0, 1, 3, 2]; // top-left, top-right, bottom-left, bottom-right
                    
                    for (const markerId of markerOrder) {
                        const marker = markers.find(m => m.id === markerId);
                        if (!marker) continue;
                        
                        const markerCard = document.createElement('div');
                        markerCard.className = 'marker-card';
                        
                        // Generate marker image
                        console.log(`Generating marker image for marker ${marker.id}`);
                        const imageResult = await window.pywebview.api.generate_marker_image(marker.id);
                        console.log(`Marker ${marker.id} generation result:`, { 
                            success: imageResult.success, 
                            hasDataUrl: !!imageResult.data_url,
                            dataUrlStart: imageResult.data_url ? imageResult.data_url.substring(0, 50) : 'N/A'
                        });
                        
                        markerCard.innerHTML = `
                            <h4>ID ${marker.id} - ${marker.position.replace('-', ' ').toUpperCase()}</h4>
                            <div class="marker-image">
                                ${imageResult.success ? 
                                    `<img src="${imageResult.data_url}" alt="Marker ${marker.id}">` : 
                                    'Failed to generate'
                                }
                            </div>
                            <div class="marker-description">${marker.description}</div>
                        `;
                        
                        markersListEl.appendChild(markerCard);
                    }
                    
                    showMessage('markersStatus', '✅ Markers ready - download and place them on your screen', true);
                } catch (error) {
                    console.error('Error loading markers:', error);
                    showMessage('markersStatus', '❌ Error loading markers', false);
                }
            }
            

            

            
            async function saveAllMarkersAsPNG() {
                console.log('Saving all markers as PNGs...');
                
                // Show loading state
                const btn = event.target;
                const originalText = btn.textContent;
                btn.textContent = '⏳ Creating PNGs...';
                btn.disabled = true;
                
                try {
                    const result = await window.pywebview.api.save_all_markers_png_only();
                    
                    if (result.success) {
                        const fileCount = result.files ? result.files.length : 0;
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
                    btn.textContent = originalText;
                    btn.disabled = false;
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
                // Wait for pywebview API to be ready
                if (!window.pywebview || !window.pywebview.api) {
                    console.log('PyWebView API not ready for config, using defaults...');
                    config = {
                        host: 'localhost',
                        port: 8765,
                        server_running: false
                    };
                    return;
                }
                
                try {
                    config = await window.pywebview.api.get_config();
                    const hostEl = document.getElementById('host');
                    const portEl = document.getElementById('port');
                    if (hostEl) hostEl.value = config.host;
                    if (portEl) portEl.value = config.port;
                } catch (error) {
                    console.error('Failed to load config:', error);
                    config = {
                        host: 'localhost',
                        port: 8765,
                        server_running: false
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
