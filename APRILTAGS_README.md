# AprilTags Configuration Guide

This guide explains how to configure and manage AprilTags for the GazeDeck application.

## Overview

The GazeDeck app now uses a YAML configuration file (`apriltags_config.yaml`) to manage AprilTag positions and settings. This makes it easy to:

- Customize tag positions for your specific setup
- Add or remove tags as needed
- Document your physical tag placement
- Validate your configuration

## Configuration File Structure

The configuration file (`apriltags_config.yaml`) contains:

```yaml
# Screen dimensions (update these to match your actual screen size)
screen_width: 1020
screen_height: 780

# April tag definitions
apriltags:
  tag_0:
    id: 0
    description: "Top-left tag (Row 1, Col 1)"
    corners:
      - [65, 90]      # Top-left corner
      - [165, 90]     # Top-right corner
      - [165, 190]    # Bottom-right corner
      - [65, 190]     # Bottom-left corner

# ... more tags ...

# Layout information
layout:
  rows: 2
  columns: 5
  tag_spacing_x: 230  # Approximate spacing between tag centers horizontally
  tag_spacing_y: 500  # Approximate spacing between tag centers vertically
  tag_size: 100       # Size of each tag in pixels (width/height)
```

## How to Configure Your AprilTags

### 1. Print the AprilTags

Use the provided `generate_apriltags.py` script to generate PNG images of the AprilTags:

```bash
# Generate tags 0-9 (default)
python generate_apriltags.py

# Generate specific range
python generate_apriltags.py 0 15  # Generate tags 0-14
```

The generated tags will be saved in the `apriltags/` directory.

### 2. Place Tags on Your Screen

1. Print the generated AprilTag images
2. Place them on your screen according to your desired layout
3. Measure the actual positions of each tag's corners

### 3. Update the Configuration

Edit `apriltags_config.yaml` to match your physical setup:

1. **Update screen dimensions**: Set `screen_width` and `screen_height` to match your actual screen
2. **Update tag positions**: For each tag, update the `corners` coordinates to match where you placed the physical tags
3. **Update descriptions**: Optionally update the `description` field for each tag to help identify them

### 4. Validate Your Configuration

Test your configuration using the built-in validation:

```bash
python config_utils.py
```

This will:
- Load your configuration
- Validate the structure and data
- Show information about your tags
- Report any errors

## Configuration Utilities

The `config_utils.py` module provides several utility functions:

### Loading Configuration
```python
from config_utils import load_apriltag_config
config = load_apriltag_config("apriltags_config.yaml")
```

### Getting Marker Data
```python
from config_utils import get_marker_vertices, get_screen_size
marker_vertices = get_marker_vertices()
screen_size = get_screen_size()
```

### Validating Configuration
```python
from config_utils import validate_config
errors = validate_config(config)
if errors:
    print("Configuration errors:", errors)
```

### Listing Available Tags
```python
from config_utils import list_available_tags
tags = list_available_tags(config)
for tag in tags:
    print(f"Tag {tag['id']}: {tag['description']}")
```

## Testing Your Setup

Run the integration test to verify everything works:

```bash
python test_config_integration.py
```

This will test:
- Config file exists
- Configuration loads correctly
- Gaze config integration works
- Data consistency

## Tips for Best Results

1. **Accurate measurements**: Use a ruler or measuring tool to get precise corner coordinates
2. **Consistent units**: All coordinates should be in the same units (pixels)
3. **Tag orientation**: Make sure tags are placed flat and not distorted
4. **Lighting**: Ensure good lighting conditions for tag detection
5. **Validation**: Always run the config validation after making changes

## Troubleshooting

### Common Issues

1. **"Config file not found"**: Make sure `apriltags_config.yaml` exists in the project directory
2. **"Tag X missing corners"**: Each tag needs exactly 4 corner coordinates
3. **"Duplicate tag ID"**: Each tag must have a unique ID
4. **"Screen dimensions invalid"**: Width and height must be positive numbers

### Getting Help

If you encounter issues:
1. Run `python config_utils.py` to see detailed error messages
2. Check that your YAML syntax is valid (you can use online YAML validators)
3. Verify your coordinate measurements are accurate
4. Run the integration test: `python test_config_integration.py`

## Example Configurations

### Basic 2x5 Grid (Default)
The default configuration assumes a 2x5 grid of 100x100px tags on a 1020x780 screen.

### Custom Layout
You can create any layout by updating the coordinates. For example, for a circular arrangement:

```yaml
apriltags:
  center_tag:
    id: 0
    description: "Center tag"
    corners:
      - [510, 380]   # Top-left
      - [610, 380]   # Top-right
      - [610, 480]   # Bottom-right
      - [510, 480]   # Bottom-left
```

## Advanced Usage

### Multiple Configurations
You can create multiple configuration files for different setups:

```bash
# Development setup
python main.py  # Uses apriltags_config.yaml

# Custom config
python -c "from gaze_config import GazeConfig; gc = GazeConfig(calibration, 'custom_config.yaml')"
```

### Programmatic Configuration
You can also create configurations programmatically:

```python
from config_utils import validate_config
import yaml

# Create custom config
config = {
    'screen_width': 1920,
    'screen_height': 1080,
    'apriltags': {
        'tag_0': {
            'id': 0,
            'description': 'Custom tag',
            'corners': [[100, 100], [200, 100], [200, 200], [100, 200]]
        }
    }
}

# Validate and save
errors = validate_config(config)
if not errors:
    with open('custom_config.yaml', 'w') as f:
        yaml.dump(config, f)
```
