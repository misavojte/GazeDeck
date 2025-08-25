"""Pupil Labs hardware integration for GazeDeck"""

import logging
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass
import time

try:
    from pupil_labs.realtime_api.simple import discover_one_device
    from pupil_labs.real_time_screen_gaze.gaze_mapper import GazeMapper
    from pupil_labs.real_time_screen_gaze import marker_generator
    PUPIL_AVAILABLE = True
except ImportError:
    PUPIL_AVAILABLE = False

from .config import config


@dataclass
class PupilDeviceInfo:
    """Information about connected Pupil Labs device"""
    device_type: str
    device_name: str
    serial_number: str
    battery_level: Optional[int] = None
    is_recording: bool = False


@dataclass
class MarkerInfo:
    """Information about AprilTag markers"""
    marker_id: int
    position: str  # "top-left", "top-right", "bottom-right", "bottom-left"
    screen_coords: Tuple[int, int, int, int]  # x, y, width, height
    description: str


class PupilLabsIntegration:
    """Manages Pupil Labs hardware connection and gaze mapping"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.device = None
        self.gaze_mapper = None
        self.screen_surface = None
        self.is_connected = False
        self.device_info: Optional[PupilDeviceInfo] = None
        self.markers: List[MarkerInfo] = []
        self._setup_default_markers()
    
    def _setup_default_markers(self):
        """Setup default AprilTag marker configuration"""
        # Default markers for a typical screen setup
        screen_width = config.get('screen.width', 1920)
        screen_height = config.get('screen.height', 1080)
        marker_size = config.get('markers.size', 64)
        margin = config.get('markers.margin', 32)
        
        self.markers = [
            MarkerInfo(
                marker_id=0,
                position="top-left",
                screen_coords=(margin, margin, marker_size, marker_size),
                description="Place this marker in the top-left corner of your screen"
            ),
            MarkerInfo(
                marker_id=1,
                position="top-right", 
                screen_coords=(screen_width - margin - marker_size, margin, marker_size, marker_size),
                description="Place this marker in the top-right corner of your screen"
            ),
            MarkerInfo(
                marker_id=2,
                position="bottom-right",
                screen_coords=(screen_width - margin - marker_size, screen_height - margin - marker_size, marker_size, marker_size),
                description="Place this marker in the bottom-right corner of your screen"
            ),
            MarkerInfo(
                marker_id=3,
                position="bottom-left",
                screen_coords=(margin, screen_height - margin - marker_size, marker_size, marker_size),
                description="Place this marker in the bottom-left corner of your screen"
            )
        ]
    
    def check_pupil_availability(self) -> Dict[str, Any]:
        """Check if Pupil Labs libraries are available"""
        return {
            "available": PUPIL_AVAILABLE,
            "message": "Pupil Labs libraries are available" if PUPIL_AVAILABLE else 
                      "Pupil Labs libraries not installed. Run: pip install -e '.[pupil]'"
        }
    
    def discover_device(self, timeout: int = 10) -> Dict[str, Any]:
        """Discover and connect to Pupil Labs device"""
        if not PUPIL_AVAILABLE:
            return {
                "success": False,
                "message": "Pupil Labs libraries not available"
            }
        
        try:
            self.logger.info(f"Searching for Pupil Labs device (timeout: {timeout}s)...")
            self.device = discover_one_device(max_search_duration_seconds=timeout)
            
            if self.device:
                # Get device info
                device_info = self.device.get_system_info()
                self.device_info = PupilDeviceInfo(
                    device_type=device_info.get('device_type', 'Unknown'),
                    device_name=device_info.get('device_name', 'Pupil Device'),
                    serial_number=device_info.get('serial_number', 'Unknown'),
                    battery_level=device_info.get('battery_level_percent')
                )
                
                self.is_connected = True
                self.logger.info(f"Connected to {self.device_info.device_name}")
                
                return {
                    "success": True,
                    "message": f"Connected to {self.device_info.device_name}",
                    "device_info": {
                        "type": self.device_info.device_type,
                        "name": self.device_info.device_name,
                        "serial": self.device_info.serial_number,
                        "battery": self.device_info.battery_level
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "No Pupil Labs device found. Make sure device is connected and powered on."
                }
                
        except Exception as e:
            self.logger.error(f"Error discovering device: {e}")
            return {
                "success": False,
                "message": f"Error discovering device: {str(e)}"
            }
    
    def setup_gaze_mapper(self) -> Dict[str, Any]:
        """Setup gaze mapper with device calibration"""
        if not self.device:
            return {
                "success": False,
                "message": "No device connected"
            }
        
        try:
            # Get calibration from device
            calibration = self.device.get_calibration()
            self.gaze_mapper = GazeMapper(calibration)
            
            # Setup screen surface with markers
            marker_verts = {}
            for marker in self.markers:
                x, y, w, h = marker.screen_coords
                # Define marker corners (top-left, top-right, bottom-right, bottom-left)
                marker_verts[marker.marker_id] = [
                    (x, y),           # top-left
                    (x + w, y),       # top-right  
                    (x + w, y + h),   # bottom-right
                    (x, y + h)        # bottom-left
                ]
            
            screen_size = (
                config.get('screen.width', 1920),
                config.get('screen.height', 1080)
            )
            
            self.screen_surface = self.gaze_mapper.add_surface(
                marker_verts,
                screen_size
            )
            
            self.logger.info("Gaze mapper setup complete")
            return {
                "success": True,
                "message": "Gaze mapper configured successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Error setting up gaze mapper: {e}")
            return {
                "success": False,
                "message": f"Error setting up gaze mapper: {str(e)}"
            }
    
    def generate_marker_image(self, marker_id: int) -> Optional[bytes]:
        """Generate high-resolution AprilTag marker image as PNG bytes"""
        try:
            from .apriltag_generator import apriltag_generator
            return apriltag_generator.generate_marker_image(marker_id, high_res=True)
        except Exception as e:
            self.logger.error(f"Error generating marker {marker_id}: {e}")
            return None
    
    def get_marker_info(self) -> List[Dict[str, Any]]:
        """Get information about all markers"""
        return [
            {
                "id": marker.marker_id,
                "position": marker.position,
                "coords": marker.screen_coords,
                "description": marker.description
            }
            for marker in self.markers
        ]
    
    def process_gaze_frame(self) -> Optional[Dict[str, Any]]:
        """Process a single frame and return gaze data"""
        if not self.device or not self.gaze_mapper or not self.screen_surface:
            return None
            
        try:
            # Get matched frame and gaze data
            frame, gaze = self.device.receive_matched_scene_video_frame_and_gaze()
            
            # Process with gaze mapper
            result = self.gaze_mapper.process_frame(frame, gaze)
            
            # Extract gaze points for our screen surface
            gaze_points = []
            if self.screen_surface.uid in result.mapped_gaze:
                for surface_gaze in result.mapped_gaze[self.screen_surface.uid]:
                    gaze_points.append({
                        "x": surface_gaze.x,
                        "y": surface_gaze.y,
                        "timestamp": time.time()
                    })
            
            return {
                "success": True,
                "gaze_points": gaze_points,
                "frame_timestamp": frame.timestamp_unix_seconds if frame else None
            }
            
        except Exception as e:
            self.logger.error(f"Error processing gaze frame: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def disconnect(self):
        """Disconnect from device and cleanup"""
        if self.device:
            try:
                self.device.close()
            except Exception as e:
                self.logger.error(f"Error disconnecting: {e}")
        
        self.device = None
        self.gaze_mapper = None
        self.screen_surface = None
        self.is_connected = False
        self.device_info = None
        
        self.logger.info("Disconnected from Pupil Labs device")


# Global instance
pupil_integration = PupilLabsIntegration()
