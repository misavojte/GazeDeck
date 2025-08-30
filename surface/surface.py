#!/usr/bin/env python3
"""
Surface Class - High-level interface for surface configuration management.

This module provides a convenient Surface class that encapsulates all surface
configuration functionality, making it easy to work with AprilTag-based
surface configurations for gaze tracking systems.
"""

from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union, Any
from dataclasses import dataclass

from .config_loader import (
    SurfaceConfig,
    AprilTagConfig,
    load_config_from_file,
    load_config_from_dict,
    ConfigLoadError,
    ConfigValidationError
)
from .config_generator import (
    generate_config,
    save_config,
    save_apriltag,
    validate_config
)


@dataclass
class SurfaceCalibration:
    """Calibration data for surface mapping containing april tag vertices and screen size."""
    marker_vertices: Dict[int, List[Tuple[int, int]]]
    surface_size: Tuple[int, int]

    def __init__(self, config: SurfaceConfig):
        """Initialize calibration from SurfaceConfig."""
        self.marker_vertices = {}
        for tag in config.apriltags.values():
            self.marker_vertices[tag.id] = [tuple(corner) for corner in tag.corners]
        self.surface_size = (config.surface_width, config.surface_height)


class Surface:
    """
    High-level Surface class for managing AprilTag surface configurations.

    This class provides a convenient interface for:
    - Loading and validating surface configurations
    - Generating new configurations
    - Accessing configuration data
    - Managing AprilTag calibration data
    """

    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        Initialize Surface with configuration.

        Args:
            config_path: Path to YAML configuration file (optional)
        """
        self._config: Optional[SurfaceConfig] = None
        self._calibration: Optional[SurfaceCalibration] = None
        self._config_path: Optional[Path] = Path(config_path) if config_path else None

        if self._config_path:
            self.load_config(self._config_path)

    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> 'Surface':
        """Create Surface instance from configuration file."""
        return cls(config_path)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'Surface':
        """Create Surface instance from configuration dictionary."""
        surface = cls()
        surface.load_from_dict(config_dict)
        return surface

    @classmethod
    def generate(cls,
                 surface_width: int,
                 surface_height: int,
                 tag_size: int,
                 rows: int = 2,
                 columns: int = 5,
                 margin: int = 50,
                 output_path: str = "apriltags",
                 config_filename: str = "apriltag_config.yaml") -> 'Surface':
        """
        Generate a new surface configuration.

        Args:
            surface_width: Surface width in pixels
            surface_height: Surface height in pixels
            tag_size: Size of each AprilTag in pixels
            rows: Number of rows (minimum 2)
            columns: Number of columns per row
            margin: Margin from surface edges in pixels
            output_path: Directory to save AprilTag images
            config_filename: Filename for configuration file

        Returns:
            Surface instance with generated configuration
        """
        # Generate configuration
        config = generate_config(surface_width, surface_height, tag_size, rows, columns, margin)

        # Save configuration
        config_path = Path(output_path) / config_filename
        save_config(config, str(config_path))

        # Generate AprilTag images
        for tag_id in config['apriltags'].keys():
            save_apriltag(tag_id, output_path, tag_size)

        # Create and return Surface instance
        surface = cls()
        surface._config = SurfaceConfig(
            surface_width=config['surface_width'],
            surface_height=config['surface_height'],
            tag_size=config['tag_size'],
            rows=config['rows'],
            columns=config['columns'],
            margin=config['margin'],
            apriltags={
                name: AprilTagConfig(
                    id=tag_data['id'],
                    description=tag_data['description'],
                    corners=tag_data['corners']
                )
                for name, tag_data in config['apriltags'].items()
            }
        )
        surface._config_path = config_path
        surface._update_calibration()

        print(f"Generated surface configuration with {len(surface._config.apriltags)} AprilTags")
        return surface

    def load_config(self, config_path: Union[str, Path]) -> None:
        """
        Load configuration from file.

        Args:
            config_path: Path to configuration file

        Raises:
            ConfigLoadError: If configuration cannot be loaded
            ConfigValidationError: If configuration is invalid
        """
        self._config_path = Path(config_path)
        self._config = load_config_from_file(config_path)
        self._update_calibration()

    def load_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """
        Load configuration from dictionary.

        Args:
            config_dict: Configuration dictionary

        Raises:
            ConfigValidationError: If configuration is invalid
        """
        self._config = load_config_from_dict(config_dict)
        self._update_calibration()

    def _update_calibration(self) -> None:
        """Update calibration data from current configuration."""
        if self._config:
            self._calibration = SurfaceCalibration(self._config)

    def save_config(self, output_path: Optional[Union[str, Path]] = None) -> None:
        """
        Save current configuration to file.

        Args:
            output_path: Path to save configuration (uses current path if None)
        """
        if not self._config:
            raise ValueError("No configuration loaded to save")

        save_path = Path(output_path) if output_path else self._config_path
        if not save_path:
            raise ValueError("No output path specified and no config path set")

        save_config(self._config_to_dict(), str(save_path))
        self._config_path = save_path

    def _config_to_dict(self) -> Dict[str, Any]:
        """Convert SurfaceConfig to dictionary format."""
        if not self._config:
            return {}

        return {
            'surface_width': self._config.surface_width,
            'surface_height': self._config.surface_height,
            'tag_size': self._config.tag_size,
            'rows': self._config.rows,
            'columns': self._config.columns,
            'margin': self._config.margin,
            'apriltags': {
                name: {
                    'id': tag.id,
                    'description': tag.description,
                    'corners': tag.corners
                }
                for name, tag in self._config.apriltags.items()
            }
        }

    @property
    def config(self) -> Optional[SurfaceConfig]:
        """Get the current configuration."""
        return self._config

    @property
    def calibration(self) -> Optional[SurfaceCalibration]:
        """Get the calibration data."""
        return self._calibration

    @property
    def is_loaded(self) -> bool:
        """Check if configuration is loaded."""
        return self._config is not None

    def get_tag_by_id(self, tag_id: int) -> Optional[AprilTagConfig]:
        """Get AprilTag configuration by ID."""
        if not self._config:
            return None
        return self._config.get_tag_by_id(tag_id)

    def get_corner_tags(self) -> List[AprilTagConfig]:
        """Get all corner-positioned AprilTags."""
        if not self._config:
            return []
        return self._config.get_corner_tags()

    def get_edge_tags(self, edge: str) -> List[AprilTagConfig]:
        """Get all AprilTags positioned on a specific edge."""
        if not self._config:
            return []
        return self._config.get_edge_tags(edge)

    def validate(self) -> List[str]:
        """Validate the current configuration."""
        if not self._config:
            return ["No configuration loaded"]
        return validate_config(self._config_to_dict())

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the surface configuration."""
        if not self._config:
            return {"status": "No configuration loaded"}

        from .config_loader import get_config_summary
        return get_config_summary(self._config)

    def regenerate_apriltags(self, output_path: str = "apriltags") -> None:
        """Regenerate AprilTag images for current configuration."""
        if not self._config:
            raise ValueError("No configuration loaded")

        for tag in self._config.apriltags.values():
            save_apriltag(tag.id, output_path, self._config.tag_size)

        print(f"Regenerated {len(self._config.apriltags)} AprilTag images")

    def __str__(self) -> str:
        """String representation of the Surface."""
        if not self._config:
            return "Surface: No configuration loaded"

        return (f"Surface: {self._config.surface_width}x{self._config.surface_height}, "
                f"{len(self._config.apriltags)} AprilTags")

    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"Surface(config_path={self._config_path}, loaded={self.is_loaded})"
