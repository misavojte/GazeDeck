#!/usr/bin/env python3
"""
Example usage of the Surface class.

This file demonstrates how to use the high-level Surface class
for managing AprilTag surface configurations.
"""

from surface import Surface


def example_load_existing():
    """Example: Load an existing surface configuration."""
    print("=== Loading Existing Surface Configuration ===")

    # Load from file
    surface = Surface.from_file("apriltags/apriltag_config.yaml")

    print(f"Loaded: {surface}")
    print(f"Surface size: {surface.config.surface_width}x{surface.config.surface_height}")
    print(f"Total AprilTags: {len(surface.config.apriltags)}")

    # Get summary
    summary = surface.get_summary()
    print(f"Summary: {summary}")

    # Access calibration data
    print(f"Calibration vertices: {len(surface.calibration.marker_vertices)} tags")
    print(f"First tag corners: {surface.calibration.marker_vertices[0]}")


def example_generate_new():
    """Example: Generate a new surface configuration."""
    print("\n=== Generating New Surface Configuration ===")

    # Generate new configuration
    surface = Surface.generate(
        surface_width=1920,
        surface_height=1080,
        tag_size=100,
        rows=2,
        columns=5,
        margin=50,
        output_path="apriltags",
        config_filename="generated_config.yaml"
    )

    print(f"Generated: {surface}")
    print("AprilTags saved to apriltags/ directory")
    print("Configuration saved as apriltags/generated_config.yaml")


def example_from_dict():
    """Example: Create surface from dictionary."""
    print("\n=== Creating Surface from Dictionary ===")

    config_dict = {
        'surface_width': 1280,
        'surface_height': 720,
        'tag_size': 80,
        'rows': 2,
        'columns': 3,
        'margin': 40,
        'apriltags': {
            'tag_0': {
                'id': 0,
                'description': 'Top-left corner',
                'corners': [[40, 40], [120, 40], [120, 120], [40, 120]]
            },
            'tag_1': {
                'id': 1,
                'description': 'Top-right corner',
                'corners': [[1160, 40], [1240, 40], [1240, 120], [1160, 120]]
            }
        }
    }

    surface = Surface.from_dict(config_dict)
    print(f"Created from dict: {surface}")


def example_validation():
    """Example: Configuration validation."""
    print("\n=== Configuration Validation ===")

    surface = Surface.from_file("apriltags/apriltag_config.yaml")
    errors = surface.validate()

    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("Configuration is valid!")


def example_tag_access():
    """Example: Accessing individual tags."""
    print("\n=== Accessing Individual Tags ===")

    surface = Surface.from_file("apriltags/apriltag_config.yaml")

    # Get tag by ID
    tag = surface.get_tag_by_id(0)
    if tag:
        print(f"Tag 0: {tag.description}")
        print(f"Corners: {tag.corners}")

    # Get corner tags
    corners = surface.get_corner_tags()
    print(f"Corner tags: {len(corners)}")

    # Get edge tags
    top_tags = surface.get_edge_tags("top")
    print(f"Top edge tags: {len(top_tags)}")


if __name__ == "__main__":
    print("Surface Class Usage Examples")
    print("=" * 40)

    try:
        example_load_existing()
        example_generate_new()
        example_from_dict()
        example_validation()
        example_tag_access()

        print("\n" + "=" * 40)
        print("All examples completed successfully!")

    except Exception as e:
        print(f"Error running examples: {e}")
        print("Make sure you have a valid apriltags/apriltag_config.yaml file")
