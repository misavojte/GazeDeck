# Surface Module

A comprehensive Python package for managing AprilTag-based surface configurations for gaze tracking systems.

## 🚀 Quick Start

```python
from surface import Surface

# Load existing configuration
surface = Surface.from_file("apriltags/apriltag_config.yaml")
print(f"Loaded surface: {surface}")

# Generate new configuration
surface = Surface.generate(
    surface_width=1920,
    surface_height=1080,
    tag_size=100,
    rows=2,
    columns=5
)
```

## 📦 Main Classes

### `Surface`
The primary class for managing surface configurations.

#### Class Methods

- **`Surface.from_file(path)`** - Load from YAML file
- **`Surface.from_dict(config_dict)`** - Load from dictionary
- **`Surface.generate(...)`** - Generate new configuration

#### Instance Methods

- **`load_config(path)`** - Load configuration from file
- **`load_from_dict(config_dict)`** - Load from dictionary
- **`save_config(path)`** - Save configuration to file
- **`validate()`** - Validate configuration
- **`get_summary()`** - Get configuration summary
- **`get_tag_by_id(tag_id)`** - Get specific AprilTag
- **`get_corner_tags()`** - Get corner-positioned tags
- **`get_edge_tags(edge)`** - Get tags on specific edge

#### Properties

- **`config`** - SurfaceConfig object
- **`calibration`** - SurfaceCalibration object
- **`is_loaded`** - Boolean indicating if config is loaded

### `SurfaceConfig`
Structured configuration data.

### `SurfaceCalibration`
Calibration data for gaze mapping.

## 🔧 Usage Examples

### Loading Configuration
```python
from surface import Surface

# Method 1: Load from file
surface = Surface.from_file("apriltags/apriltag_config.yaml")

# Method 2: Create and load
surface = Surface()
surface.load_config("apriltags/apriltag_config.yaml")
```

### Generating Configuration
```python
from surface import Surface

surface = Surface.generate(
    surface_width=1920,    # Surface width in pixels
    surface_height=1080,   # Surface height in pixels
    tag_size=100,         # AprilTag size in pixels
    rows=2,               # Number of rows (min 2)
    columns=5,            # Tags per row
    margin=50,            # Margin from edges
    output_path="apriltags"  # Where to save images
)
```

### Accessing Data
```python
# Get calibration data for gaze mapping
marker_vertices = surface.calibration.marker_vertices
surface_size = surface.calibration.surface_size

# Access individual tags
tag = surface.get_tag_by_id(0)
print(f"Tag description: {tag.description}")
print(f"Corners: {tag.corners}")

# Get tags by position
corners = surface.get_corner_tags()
top_tags = surface.get_edge_tags("top")
```

### Validation
```python
errors = surface.validate()
if errors:
    print("Configuration errors:")
    for error in errors:
        print(f"  - {error}")
else:
    print("Configuration is valid!")
```

## 📁 Module Structure

```
surface/
├── __init__.py          # Package exports (Surface class only)
├── surface.py           # Main Surface class
├── config_generator.py  # Low-level AprilTag generation
├── config_loader.py     # Low-level configuration loading
├── example_usage.py     # Usage examples
└── README.md           # This documentation
```

## 🎯 Clean API Philosophy

The surface module follows a **"less is more"** approach:

- **Primary Interface**: `Surface` class handles everything
- **Simple Imports**: Only main classes exported
- **Encapsulated Complexity**: Internal functions hidden
- **Easy to Use**: Just import `Surface` and you're ready

**Before (complex):**
```python
from surface import load_config_from_file, generate_config, save_apriltag
# Many imports, complex usage
```

**After (simple):**
```python
from surface import Surface
# One import, everything encapsulated
```

## 🎯 Integration

The Surface class is designed to integrate seamlessly with gaze tracking applications:

```python
# In your gaze tracking application
from surface import Surface

# Load surface configuration
surface = Surface.from_file("apriltags/apriltag_config.yaml")

# Use for gaze mapping
marker_vertices = surface.calibration.marker_vertices
surface_size = surface.calibration.surface_size

# Add to gaze mapper
surface_obj = gaze_mapper.add_surface(marker_vertices, surface_size)
```

## 📋 Requirements

- Python 3.7+
- PyYAML
- OpenCV (for AprilTag generation)
- pupil-labs-realtime-api (for gaze tracking integration)

## 🔍 API Reference

For detailed API documentation, see the docstrings in each module file.

## 🐛 Error Handling

The Surface class provides comprehensive error handling:

- `ConfigLoadError` - Configuration file loading issues
- `ConfigValidationError` - Invalid configuration data
- Standard `ValueError` - Invalid parameters

## 📝 Notes

- All configurations are validated automatically
- AprilTag images are generated using pupil-labs marker generator
- Configurations follow YAML format for easy editing
- Surface class provides both low-level and high-level APIs
