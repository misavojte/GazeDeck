# Surface Layout Generator

A minimal Python package for generating AprilTag surface configurations for gaze tracking systems.

## Features

- **Simple API**: Clean, minimal interface for surface configuration
- **Flexible Layout**: Generate AprilTags around screen edges with customizable parameters
- **YAML Configuration**: Save and load surface configurations
- **PNG Generation**: Generate AprilTag images for printing
- **Error Handling**: Comprehensive validation and error reporting

## Installation

### Dependencies

Install required dependencies:

```bash
pip install opencv-python numpy PyYAML
```

**Note**: The `pupil-labs-realtime-screen-gaze` package may need to be installed separately depending on your Python environment.

## Usage

### Command Line

The easiest way to generate surface configurations:

```bash
# Default 1920x1080 layout with 10 tags
python -m surface_layout

# Custom resolution
python -m surface_layout --width 2560 --height 1440

# Custom layout with more tags
python -m surface_layout --rows 3 --columns 6

# Custom output directory
python -m surface_layout --output-dir my_surface_tags

# Full customization
python -m surface_layout --width 3440 --height 1440 --tag-size 120 --rows 3 --columns 8 --margin 60

# Markers outside frame (negative margin)
python -m surface_layout --margin -50 --output-dir external_markers
```

### Python API

```python
from surface_layout import SurfaceLayout

# Method 1: Generate from parameters
layout = SurfaceLayout.generate_from_rows_and_columns(
    width=1920,
    height=1080,
    tag_size=100,
    rows=2,
    columns=5,
    margin=50
)

# Method 2: Create from existing tags
tags = {0: [(50, 50), (150, 50), (150, 150), (50, 150)]}
layout = SurfaceLayout(width=1920, height=1080, tags=tags)

# Generate files
layout.generate_apriltags("apriltags")

# Save/load configuration
layout.save_config("config.yaml")
loaded = SurfaceLayout.create_from_yaml("config.yaml")
```

## Generated Files

Running the generator creates an output directory with:

- `apriltag_config.yaml` - Surface configuration with tag positions
- `apriltag_0.png`, `apriltag_1.png`, ... - AprilTag images for printing

## Configuration Format

The YAML configuration contains:

```yaml
surface_width: 1920
surface_height: 1080
tags:
  '0':
  - [50, 50]    # Top-left corner
  - [150, 50]   # Top-right corner
  - [150, 150]  # Bottom-right corner
  - [50, 150]   # Bottom-left corner
  '1': ...      # Next tag corners
```

## API Reference

### SurfaceLayout Class

#### Constructor
```python
SurfaceLayout(width: int = 1920, height: int = 1080, tags: Dict[int, List[Tuple[int, int]]] = None)
```

#### Static Methods
```python
generate_from_rows_and_columns(width, height, tag_size=100, rows=2, columns=5, margin=50) -> SurfaceLayout
create_from_yaml(path: str) -> SurfaceLayout
```

#### Instance Methods
```python
get_tag(tag_id: int) -> Optional[List[Tuple[int, int]]]
save_config(path: str = "apriltag_config.yaml")
generate_apriltags(output_path: str = "apriltags", config_filename: str = "apriltag_config.yaml")
```

## Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--width` | 1920 | Surface width in pixels |
| `--height` | 1080 | Surface height in pixels |
| `--tag-size` | 100 | AprilTag size in pixels |
| `--rows` | 2 | Number of tag rows (minimum: 2) |
| `--columns` | 5 | Number of tag columns (minimum: 2) |
| `--margin` | 50 | Margin from screen edges in pixels (can be negative) |
| `--output-dir` | apriltags | Output directory for config and images |

## Error Handling

The package includes comprehensive error handling:

- **Parameter validation**: Invalid parameters raise `ValueError`
- **File operations**: File system errors raise `OSError`
- **Dependencies**: Missing dependencies raise `ImportError` with installation instructions
- **YAML parsing**: Invalid configuration files raise `ValueError`

## Best Practices

1. **Test with defaults first**: Start with default parameters before customizing
2. **Check tag coverage**: Ensure tags cover your screen adequately for gaze tracking
3. **Use consistent units**: All dimensions are in pixels
4. **Backup configurations**: Save your working configurations for reuse
5. **Validate output**: Check generated files before printing
6. **Negative margins**: Use negative margins to position markers outside the visible frame area

## Troubleshooting

### "Required dependencies missing"
Install missing packages:
```bash
pip install opencv-python numpy PyYAML
```

### "pupil-labs-realtime-screen-gaze not found"
This package may need separate installation. Check the Pupil Labs documentation.

### "Invalid configuration"
Ensure your YAML file has the required fields: `surface_width`, `surface_height`, `tags`

### "tags parameter is required"
When creating a SurfaceLayout instance, you must provide a tags dictionary. Use `generate_from_rows_and_columns()` for automatic generation or `create_from_yaml()` to load from a file.

## License

This project is part of the GazeDeck gaze tracking system.
