#!/usr/bin/env python3
"""
Configuration utilities for GazeDeck AprilTags.

This module provides functions to read and manage AprilTag configurations
from YAML config files.
"""

import yaml
import os
from typing import Dict, List, Tuple, Any
from pathlib import Path


def load_apriltag_config(config_path: str = "apriltags/config.yaml") -> Dict[str, Any]:
    """
    Load AprilTag configuration from YAML file.

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        Dictionary containing the configuration data

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is malformed
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)

        if config is None:
            raise ValueError("Config file is empty or invalid")

        return config

    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing config file {config_path}: {e}")


def get_marker_vertices_from_config(config: Dict[str, Any]) -> Dict[int, List[Tuple[int, int]]]:
    """
    Extract marker vertices from configuration data.

    Args:
        config: Configuration dictionary loaded from YAML

    Returns:
        Dictionary mapping marker IDs to their corner coordinates
    """
    if 'apriltags' not in config:
        raise ValueError("Config file missing 'apriltags' section")

    marker_vertices = {}

    for tag_name, tag_data in config['apriltags'].items():
        if 'id' not in tag_data:
            raise ValueError(f"Tag {tag_name} missing 'id' field")
        if 'corners' not in tag_data:
            raise ValueError(f"Tag {tag_name} missing 'corners' field")

        tag_id = tag_data['id']
        corners = tag_data['corners']

        if len(corners) != 4:
            raise ValueError(f"Tag {tag_name} must have exactly 4 corners, got {len(corners)}")

        # Convert corners to tuples
        marker_vertices[tag_id] = [tuple(corner) for corner in corners]

    return marker_vertices


def get_screen_size_from_config(config: Dict[str, Any]) -> Tuple[int, int]:
    """
    Extract screen size from configuration data.

    Args:
        config: Configuration dictionary loaded from YAML

    Returns:
        Tuple of (width, height)
    """
    if 'screen_width' not in config or 'screen_height' not in config:
        raise ValueError("Config file missing screen_width or screen_height")

    return (config['screen_width'], config['screen_height'])


def get_apriltag_info(config: Dict[str, Any], tag_id: int) -> Dict[str, Any]:
    """
    Get information about a specific AprilTag.

    Args:
        config: Configuration dictionary loaded from YAML
        tag_id: ID of the tag to look up

    Returns:
        Dictionary with tag information (id, description, corners)
    """
    if 'apriltags' not in config:
        raise ValueError("Config file missing 'apriltags' section")

    for tag_name, tag_data in config['apriltags'].items():
        if tag_data.get('id') == tag_id:
            return {
                'id': tag_data['id'],
                'description': tag_data.get('description', ''),
                'corners': tag_data['corners'],
                'name': tag_name
            }

    raise ValueError(f"Tag with ID {tag_id} not found in configuration")


def list_available_tags(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get a list of all available AprilTags with their information.

    Args:
        config: Configuration dictionary loaded from YAML

    Returns:
        List of dictionaries with tag information
    """
    if 'apriltags' not in config:
        return []

    tags = []
    for tag_name, tag_data in config['apriltags'].items():
        tags.append({
            'id': tag_data['id'],
            'description': tag_data.get('description', ''),
            'name': tag_name,
            'corners': tag_data['corners']
        })

    # Sort by ID
    return sorted(tags, key=lambda x: x['id'])


def validate_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate the configuration data and return any issues found.

    Args:
        config: Configuration dictionary loaded from YAML

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check required fields
    required_fields = ['screen_width', 'screen_height', 'apriltags']
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")

    if 'apriltags' in config:
        apriltags = config['apriltags']
        if not isinstance(apriltags, dict):
            errors.append("'apriltags' must be a dictionary")
        else:
            # Check each tag
            used_ids = set()
            for tag_name, tag_data in apriltags.items():
                if not isinstance(tag_data, dict):
                    errors.append(f"Tag '{tag_name}' must be a dictionary")
                    continue

                # Check ID
                if 'id' not in tag_data:
                    errors.append(f"Tag '{tag_name}' missing 'id' field")
                else:
                    tag_id = tag_data['id']
                    if tag_id in used_ids:
                        errors.append(f"Duplicate tag ID: {tag_id}")
                    used_ids.add(tag_id)

                # Check corners
                if 'corners' not in tag_data:
                    errors.append(f"Tag '{tag_name}' missing 'corners' field")
                else:
                    corners = tag_data['corners']
                    if len(corners) != 4:
                        errors.append(f"Tag '{tag_name}' must have exactly 4 corners, got {len(corners)}")
                    else:
                        for i, corner in enumerate(corners):
                            if len(corner) != 2:
                                errors.append(f"Tag '{tag_name}' corner {i} must have 2 coordinates [x, y]")

    # Check screen dimensions
    if 'screen_width' in config and config['screen_width'] <= 0:
        errors.append("screen_width must be positive")
    if 'screen_height' in config and config['screen_height'] <= 0:
        errors.append("screen_height must be positive")

    return errors


# Convenience functions for easy access
def get_marker_vertices(config_path: str = "apriltags/config.yaml") -> Dict[int, List[Tuple[int, int]]]:
    """Load config and return marker vertices."""
    config = load_apriltag_config(config_path)
    return get_marker_vertices_from_config(config)


def get_screen_size(config_path: str = "apriltags/config.yaml") -> Tuple[int, int]:
    """Load config and return screen size."""
    config = load_apriltag_config(config_path)
    return get_screen_size_from_config(config)


if __name__ == "__main__":
    # Example usage and testing
    try:
        config = load_apriltag_config()
        print("Config loaded successfully!")

        # Validate config
        errors = validate_config(config)
        if errors:
            print("Configuration errors found:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("Configuration is valid!")

        # Show some info
        screen_size = get_screen_size_from_config(config)
        print(f"Screen size: {screen_size[0]}x{screen_size[1]}")

        marker_vertices = get_marker_vertices_from_config(config)
        print(f"Found {len(marker_vertices)} AprilTags")

        tags = list_available_tags(config)
        print("\nAvailable tags:")
        for tag in tags:
            print(f"  ID {tag['id']}: {tag['description'] or tag['name']}")

    except Exception as e:
        print(f"Error: {e}")
