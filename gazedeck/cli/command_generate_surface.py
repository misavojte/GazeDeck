# gazedeck/cli/command_generate_surface.py

# python
from __future__ import annotations

# external
import argparse

# internal
from gazedeck.core.surface_layout_generation import generate_surface_layout_from_rows_and_columns, save_surface_layout


def add_generate_surface_parser(subparsers) -> argparse.ArgumentParser:
    """
    Add the generate-surface subparser to the main parser.

    Args:
        subparsers: The subparsers object from the main argument parser

    Returns:
        The configured subparser for generate-surface command
    """
    generate_parser = subparsers.add_parser(
        "generate-surface",
        help="Generate a surface layout with AprilTags"
    )
    generate_parser.add_argument(
        "id",
        type=str,
        help="Unique identifier for the surface layout",
    )
    generate_parser.add_argument(
        "--rows",
        type=int,
        default=3,
        required=False,
        help="Number of rows of tags (minimum 2)",
    )
    generate_parser.add_argument(
        "--columns",
        type=int,
        default=5,
        required=False,
        help="Number of columns of tags (minimum 2)",
    )
    generate_parser.add_argument(
        "--surface-width",
        type=float,
        default=1920.0,
        required=False,
        help="Width of the surface in your chosen units",
    )
    generate_parser.add_argument(
        "--surface-height",
        type=float,
        default=1080.0,
        required=False,
        help="Height of the surface in your chosen units",
    )
    generate_parser.add_argument(
        "--tag-size",
        type=float,
        default=100.0,
        required=False,
        help="Size of each AprilTag in the same units as surface dimensions",
    )
    generate_parser.add_argument(
        "--margin",
        type=float,
        default=25.0,
        required=False,
        help="Margin from surface edge to first tag (default: 0.0). Can be negative.",
    )
    generate_parser.add_argument(
        "--starting-tag-id",
        type=int,
        default=0,
        required=False,
        help="Starting ID for the AprilTags (default: 0)",
    )
    generate_parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Output directory for generated files (default: 'output')",
    )
    return generate_parser


def execute_generate_surface(args: argparse.Namespace):
    """
    Execute the generate-surface command with the parsed arguments.

    Args:
        args: Parsed command line arguments
    """
    try:
        print(f"[INIT] Generating surface layout '{args.id}' with {args.rows}x{args.columns} tags...")
        print(f"   Surface size: {args.surface_width}x{args.surface_height}")
        print(f"   Tag size: {args.tag_size}, Margin: {args.margin}")
        print(f"   Starting tag ID: {args.starting_tag_id}")
        print(f"   Output directory: {args.output_dir}")

        # Generate the surface layout
        layout = generate_surface_layout_from_rows_and_columns(
            id=args.id,
            rows=args.rows,
            columns=args.columns,
            surface_size=(args.surface_width, args.surface_height),
            tag_size_pixels=args.tag_size,
            margin=args.margin,
            starting_tag_id=args.starting_tag_id
        )

        # Save the layout
        save_surface_layout(layout, args.output_dir)

        print("[SUCCESS] Surface layout generated successfully!")
        print(f"[SUCCESS] Files saved to: {args.output_dir}/{args.id}")
        print(f"[SUCCESS] Generated {len(layout.tags)} AprilTag markers")
        print(f"[SUCCESS] Configuration saved as: surface_layout.yaml")

    except ValueError as e:
        print(f"[ERR] Error: {e}")
        return
    except Exception as e:
        print(f"[ERR] Unexpected error: {e}")
        return
