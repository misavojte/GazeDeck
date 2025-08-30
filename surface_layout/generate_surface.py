#!/usr/bin/env python3
"""
Console script to generate AprilTag surface configurations.

Usage:
    python -m surface_layout                      # Use defaults (1920x1080, 10 tags)
    python -m surface_layout --width 2560 --height 1440  # Custom resolution
    python -m surface_layout --rows 3 --columns 4       # Custom layout
"""

import argparse
import sys
from pathlib import Path
from . import SurfaceLayout


def main():
    """Main entry point for the surface layout generator."""
    parser = argparse.ArgumentParser(
        description="Generate AprilTag surface configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m surface_layout                           # Default 1920x1080 layout
  python -m surface_layout --width 2560 --height 1440 # 1440p resolution
  python -m surface_layout --rows 3 --columns 6      # More tags
  python -m surface_layout --output-dir my_tags       # Custom output directory
        """
    )

    parser.add_argument(
        "--width", type=int, default=1920,
        help="Surface width in pixels (default: 1920)"
    )
    parser.add_argument(
        "--height", type=int, default=1080,
        help="Surface height in pixels (default: 1080)"
    )
    parser.add_argument(
        "--tag-size", type=int, default=100,
        help="AprilTag size in pixels (default: 100)"
    )
    parser.add_argument(
        "--rows", type=int, default=2,
        help="Number of tag rows (minimum: 2, default: 2)"
    )
    parser.add_argument(
        "--columns", type=int, default=5,
        help="Number of tag columns (minimum: 2, default: 5)"
    )
    parser.add_argument(
        "--margin", type=int, default=50,
        help="Margin from screen edges in pixels (default: 50)"
    )
    parser.add_argument(
        "--output-dir", type=str, default="apriltags",
        help="Output directory for config and images (default: apriltags)"
    )

    args = parser.parse_args()

    try:
        # Validate arguments
        if args.width <= 0 or args.height <= 0:
            raise ValueError("Width and height must be positive integers")

        # Create layout using static method
        print("Generating surface layout...")
        layout = SurfaceLayout.generate_from_rows_and_columns(
            width=args.width,
            height=args.height,
            tag_size=args.tag_size,
            rows=args.rows,
            columns=args.columns,
            margin=args.margin
        )

        print(f"✓ Generated layout: {layout}")
        print(f"✓ Tag IDs: {sorted(layout.tags.keys())}")

        # Generate everything in output directory
        print(f"Generating AprilTags in: {args.output_dir}")
        layout.generate_apriltags(args.output_dir)

        output_path = Path(args.output_dir)
        if output_path.exists():
            files = list(output_path.iterdir())
            print(f"✓ Success! Generated {len(files)} files:")
            for file in sorted(files):
                print(f"  - {file.name}")

        print(f"\n🎯 All files generated in: {args.output_dir}")

    except ValueError as e:
        print(f"❌ Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"❌ File system error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
