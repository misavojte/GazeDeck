"""CLI interface for marker setup generation."""

import typer
from pathlib import Path
from datetime import datetime
from .generator import generate_apriltag_markers, save_config

# Default to config/markers relative to the gazedeck package
DEFAULT_OUTPUT = Path(__file__).parent.parent.parent / "markers"

app = typer.Typer()


@app.command()
def generate(
    width: int = typer.Argument(..., help="Screen width in pixels"),
    height: int = typer.Argument(..., help="Screen height in pixels"),
    output_dir: Path = typer.Option(DEFAULT_OUTPUT, "--output", "-o", help="Output directory"),
    marker_size: int = typer.Option(200, "--marker-size", help="Marker size in pixels"),
    position: str = typer.Option("inside", "--position", help="Marker position: inside or outside screen bounds"),
    count: int = typer.Option(4, "--count", "-c", help="Number of markers: 4, 6, 8, or 10"),
    name: str = typer.Option(None, "--name", "-n", help="Custom name for the setup folder")
) -> None:
    """Generate AprilTag markers and config for gaze tracking setup.

    This generates AprilTag markers and a JSON configuration file that can be
    used directly with GazeDeck's --markers-json flag.

    The markers and config are saved to gazedeck/config/markers/ by default.

    Examples:
        python -m gazedeck.config.generator.marker 1920 1080
        python -m gazedeck.config.generator.marker 2560 1440 --count 8 --position outside --name ultrawide
        python -m gazedeck.config.generator.marker 1920 1080 --count 10 --name office_setup
    """

    if position not in ["inside", "outside"]:
        raise typer.BadParameter("Position must be 'inside' or 'outside'")

    # Create subdirectory with custom name or timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if name:
        # Sanitize the name to be filesystem-safe
        safe_name = "".join(c for c in name if c.isalnum() or c in ('_', '-')).strip()
        if not safe_name:
            safe_name = f"unnamed_{timestamp}"
        setup_dir = output_dir / safe_name
    else:
        setup_dir = output_dir / f"setup_{timestamp}"

    setup_dir.mkdir(parents=True, exist_ok=True)

    # Generate markers and config
    config = generate_apriltag_markers(width, height, setup_dir, marker_size, position, count)

    # Save config
    config_path = setup_dir / "config.json"
    save_config(config, config_path)

    # Print results
    typer.echo(f"Generated {count} AprilTag markers ({position} screen) in {setup_dir}/markers/")
    typer.echo(f"Config saved to {config_path}")
    typer.echo(f"Ready for: gazedeck --markers-json {config_path}")


if __name__ == "__main__":
    app()
