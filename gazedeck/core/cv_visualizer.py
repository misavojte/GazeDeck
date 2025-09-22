# gazedeck/core/cv_visualizer.py
"""
Minimal CV visualization for live tag detection and surface tracking.

Shows detected AprilTags with colored edges, IDs, and confidence scores
on the original distorted video feed.
"""

import cv2
import numpy as np
import numpy.typing as npt
from typing import List, Dict, Optional

from .marker_detection import DetectedMarker
from .surface_tracking import SurfaceLocation

# Best practice colors for tag edges (BGR format for OpenCV)
COLORS = {
    'top': (0, 255, 0),      # Green
    'right': (255, 0, 0),    # Blue  
    'bottom': (0, 0, 255),   # Red
    'left': (0, 255, 255)    # Yellow
}

# Note: distort_points function removed - we now use original_corners directly from DetectedMarker

def draw_tag_visualization(frame: npt.NDArray[np.uint8], 
                          detected_markers: List[DetectedMarker],
                          surface_locations: Optional[Dict[int, SurfaceLocation]] = None) -> npt.NDArray[np.uint8]:
    """
    Draw tag detection visualization on frame.
    
    For each detected tag:
    - Draw colored edges (top=green, right=blue, bottom=red, left=yellow)  
    - Show tag ID as large number in center
    - Show confidence below ID
    - Optionally highlight tags that are part of tracked surfaces
    
    Args:
        frame: Original BGR video frame
        detected_markers: List of detected markers (with original distorted corners)
        surface_locations: Optional surface tracking results
        
    Returns:
        Frame with visualization overlay
    """
    if not detected_markers:
        # Add simple overlay text when no markers detected
        vis_frame = frame.copy()
        cv2.putText(vis_frame, "No AprilTags detected", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        return vis_frame
        
    # Work on copy to avoid modifying original
    vis_frame = frame.copy()
    
    for marker in detected_markers:
        try:
            # Use original distorted corners directly for accurate visualization
            corners_distorted = np.array(marker.original_corners, dtype=np.float32)
            corners_int = corners_distorted.astype(int)
            
        except Exception as e:
            print(f"⚠️  Error processing marker {marker.tag_id}: {e}")
            continue
        
        # Draw colored edges
        try:
            # Top edge (top-left to top-right)
            cv2.line(vis_frame, tuple(corners_int[3]), tuple(corners_int[2]), COLORS['top'], 3)
            # Right edge (top-right to bottom-right)  
            cv2.line(vis_frame, tuple(corners_int[2]), tuple(corners_int[1]), COLORS['right'], 3)
            # Bottom edge (bottom-right to bottom-left)
            cv2.line(vis_frame, tuple(corners_int[1]), tuple(corners_int[0]), COLORS['bottom'], 3)
            # Left edge (bottom-left to top-left)
            cv2.line(vis_frame, tuple(corners_int[0]), tuple(corners_int[3]), COLORS['left'], 3)
        except Exception as e:
            print(f"⚠️  Failed to draw edges for marker {marker.tag_id}: {e}")
            # Fallback: draw a simple circle
            center = tuple(np.mean(corners_int, axis=0).astype(int))
            cv2.circle(vis_frame, center, 20, (0, 255, 255), 3)
        
        # Calculate center for text placement
        center_x = int(np.mean(corners_int[:, 0]))
        center_y = int(np.mean(corners_int[:, 1]))
        
        # Draw tag ID as large number
        cv2.putText(vis_frame, str(marker.tag_id), 
                   (center_x - 20, center_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        cv2.putText(vis_frame, str(marker.tag_id), 
                   (center_x - 20, center_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2)
        
        # Draw confidence below ID
        confidence_text = f"{marker.confidence:.2f}"
        cv2.putText(vis_frame, confidence_text,
                   (center_x - 30, center_y + 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(vis_frame, confidence_text,
                   (center_x - 30, center_y + 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
    
    return vis_frame

class CVVisualizer:
    """
    Minimal OpenCV visualizer for live tag detection.
    
    Shows detected AprilTags with colored edges and metadata
    on original distorted video feed.
    """
    
    def __init__(self, window_name: str = "GazeDeck CV"):
        self.window_name = window_name
        cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)
    
    def show_frame(self, frame: npt.NDArray[np.uint8], 
                   detected_markers: List[DetectedMarker],
                   surface_locations: Optional[Dict[int, SurfaceLocation]] = None):
        """
        Display frame with tag visualization.
        
        Args:
            frame: Original BGR video frame
            detected_markers: List of detected markers
            surface_locations: Optional surface tracking results
        """
        vis_frame = draw_tag_visualization(
            frame, detected_markers, surface_locations
        )
        
        cv2.imshow(self.window_name, vis_frame)
        
    def should_close(self) -> bool:
        """Check if user wants to close visualization (ESC key). Non-blocking."""
        key = cv2.waitKey(1) & 0xFF
        return key == 27  # ESC key
    
    def cleanup(self):
        """Clean up OpenCV resources."""
        cv2.destroyWindow(self.window_name)
