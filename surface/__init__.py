#!/usr/bin/env python3
"""
Surface Configuration Module

This package provides a high-level Surface class for managing AprilTag-based
surface configurations for gaze tracking systems.

The main Surface class encapsulates all functionality needed for:
- Loading surface configurations from YAML files
- Generating new surface configurations with AprilTags
- Validating configurations
- Accessing calibration data for gaze mapping
"""

from .surface import Surface, SurfaceCalibration
from .config_loader import SurfaceConfig, AprilTagConfig

__version__ = "1.0.0"
__all__ = [
    'Surface',
    'SurfaceCalibration',
    'SurfaceConfig',
    'AprilTagConfig'
]
