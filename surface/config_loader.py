#!/usr/bin/env python3
"""
Surface Configuration Loader

Loads and validates surface configuration files containing AprilTag placement
information for gaze tracking systems.

This module provides functions to:
- Load configuration from YAML files
- Validate loaded configurations
- Access configuration data programmatically
- Handle configuration-related errors
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AprilTagConfig:
    """Configuration data for a single AprilTag."""
    id: int
    description: str
    corners: List[List[int]]  # List of [x, y] coordinates

    def __post_init__(self):
        """Validate AprilTag configuration after initialization."""
        if not isinstance(self.corners, list) or len(self.corners) != 4:
            raise ValueError(f"AprilTag {self.id} must have exactly 4 corners")

        for i, corner in enumerate(self.corners):
            if not isinstance(corner, list) or len(corner) != 2:
                raise ValueError(f"Corner {i} of AprilTag {self.id} must be [x, y] coordinates")


@dataclass
class SurfaceConfig:
    """Complete surface configuration data."""
    surface_width: int
    surface_height: int
    tag_size: int
    rows: int
    columns: int
    margin: int
    apriltags: Dict[str, AprilTagConfig]

    def __post_init__(self):
        """Validate surface configuration after initialization."""
        if self.surface_width <= 0:
            raise ValueError("surface_width must be positive")
        if self.surface_height <= 0:
            raise ValueError("surface_height must be positive")
        if self.tag_size <= 0:
            raise ValueError("tag_size must be positive")
        if self.rows < 2:
            raise ValueError("rows must be at least 2")
        if self.columns < 2:
            raise ValueError("columns must be at least 2")
        if self.margin < 0:
            raise ValueError("margin must be non-negative")

    def get_tag_by_id(self, tag_id: int) -> Optional[AprilTagConfig]:
        """Get AprilTag configuration by ID.

        Args:
            tag_id: The AprilTag ID to search for

        Returns:
            AprilTagConfig if found, None otherwise
        """
        for tag in self.apriltags.values():
            if tag.id == tag_id:
                return tag
        return None

    def get_corner_tags(self) -> List[AprilTagConfig]:
        """Get all corner-positioned AprilTags.

        Returns:
            List of AprilTagConfig objects positioned at corners
        """
        corner_descriptions = [
            "Top-left corner",
            "Top-right corner",
            "Bottom-left corner",
            "Bottom-right corner"
        ]
        return [tag for tag in self.apriltags.values()
                if tag.description in corner_descriptions]

    def get_edge_tags(self, edge: str) -> List[AprilTagConfig]:
        """Get all AprilTags positioned on a specific edge.

        Args:
            edge: Edge name ("top", "bottom", "left", "right")

        Returns:
            List of AprilTagConfig objects on the specified edge
        """
        edge_map = {
            "top": ["Top-left corner", "Top-right corner", "Top edge"],
            "bottom": ["Bottom-left corner", "Bottom-right corner", "Bottom edge"],
            "left": ["Left edge"],
            "right": ["Right edge"]
        }

        if edge not in edge_map:
            raise ValueError(f"Invalid edge: {edge}. Must be one of: {list(edge_map.keys())}")

        return [tag for tag in self.apriltags.values()
                if any(desc in tag.description for desc in edge_map[edge])]


class ConfigLoadError(Exception):
    """Exception raised when configuration loading fails."""
    pass


class ConfigValidationError(Exception):
    """Exception raised when configuration validation fails."""
    pass


def load_config_from_file(config_path: Union[str, Path]) -> SurfaceConfig:
    """Load surface configuration from a YAML file.

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        SurfaceConfig object containing the loaded configuration

    Raises:
        ConfigLoadError: If the file cannot be loaded or parsed
        ConfigValidationError: If the configuration is invalid
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise ConfigLoadError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            raw_config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigLoadError(f"Failed to parse YAML file {config_path}: {e}")
    except Exception as e:
        raise ConfigLoadError(f"Failed to read configuration file {config_path}: {e}")

    if raw_config is None:
        raise ConfigLoadError(f"Configuration file is empty: {config_path}")

    return _parse_config_dict(raw_config)


def load_config_from_dict(config_dict: Dict[str, Any]) -> SurfaceConfig:
    """Load surface configuration from a dictionary.

    Args:
        config_dict: Dictionary containing configuration data

    Returns:
        SurfaceConfig object containing the configuration

    Raises:
        ConfigValidationError: If the configuration is invalid
    """
    return _parse_config_dict(config_dict)


def _parse_config_dict(config_dict: Dict[str, Any]) -> SurfaceConfig:
    """Parse configuration dictionary into SurfaceConfig object.

    Args:
        config_dict: Raw configuration dictionary

    Returns:
        SurfaceConfig object

    Raises:
        ConfigValidationError: If the configuration is invalid
    """
    # Validate required fields
    required_fields = ['surface_width', 'surface_height', 'tag_size', 'rows', 'columns', 'margin', 'apriltags']
    missing_fields = [field for field in required_fields if field not in config_dict]
    if missing_fields:
        raise ConfigValidationError(f"Missing required fields: {missing_fields}")

    # Parse AprilTags
    apriltags = {}
    if not isinstance(config_dict['apriltags'], dict):
        raise ConfigValidationError("'apriltags' must be a dictionary")

    for tag_name, tag_data in config_dict['apriltags'].items():
        try:
            apriltag = AprilTagConfig(
                id=tag_data['id'],
                description=tag_data['description'],
                corners=tag_data['corners']
            )
            apriltags[tag_name] = apriltag
        except KeyError as e:
            raise ConfigValidationError(f"AprilTag '{tag_name}' missing required field: {e}")
        except ValueError as e:
            raise ConfigValidationError(f"Invalid AprilTag '{tag_name}': {e}")

    # Create SurfaceConfig
    try:
        config = SurfaceConfig(
            surface_width=config_dict['surface_width'],
            surface_height=config_dict['surface_height'],
            tag_size=config_dict['tag_size'],
            rows=config_dict['rows'],
            columns=config_dict['columns'],
            margin=config_dict['margin'],
            apriltags=apriltags
        )
    except ValueError as e:
        raise ConfigValidationError(f"Invalid surface configuration: {e}")

    return config


def validate_config_file(config_path: Union[str, Path]) -> List[str]:
    """Validate a configuration file without loading it completely.

    Args:
        config_path: Path to the configuration file

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    try:
        config = load_config_from_file(config_path)
        # Additional validation can be added here if needed
    except (ConfigLoadError, ConfigValidationError) as e:
        errors.append(str(e))
    except Exception as e:
        errors.append(f"Unexpected error: {e}")

    return errors


def get_config_summary(config: SurfaceConfig) -> Dict[str, Any]:
    """Get a summary of the configuration.

    Args:
        config: SurfaceConfig object

    Returns:
        Dictionary containing configuration summary
    """
    return {
        'surface_dimensions': f"{config.surface_width}x{config.surface_height}",
        'tag_size': config.tag_size,
        'layout': f"{config.rows}x{config.columns}",
        'total_tags': len(config.apriltags),
        'corner_tags': len(config.get_corner_tags()),
        'margin': config.margin,
        'tag_ids': sorted([tag.id for tag in config.apriltags.values()])
    }


def find_config_files(search_path: Union[str, Path] = ".") -> List[Path]:
    """Find all configuration files in a directory.

    Args:
        search_path: Directory to search in

    Returns:
        List of paths to configuration files
    """
    search_path = Path(search_path)
    config_files = []

    # Common configuration file names
    config_names = [
        'apriltag_config.yaml',
        'apriltags_config.yaml',
        'surface_config.yaml',
        'config.yaml'
    ]

    # Search for specific config files
    for config_name in config_names:
        config_file = search_path / config_name
        if config_file.exists():
            config_files.append(config_file)

    # Also search for any .yaml files that might contain apriltag configs
    for yaml_file in search_path.glob("*.yaml"):
        if yaml_file not in config_files:
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data and 'apriltags' in data:
                        config_files.append(yaml_file)
            except:
                pass  # Skip files that can't be parsed

    return sorted(config_files)
