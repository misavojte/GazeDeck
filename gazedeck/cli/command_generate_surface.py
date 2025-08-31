# gazedeck/cli/command_generate_surface.py

from __future__ import annotations

import argparse
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
        required=True,
        help="Number of rows of tags (minimum 2)",
    )
    generate_parser.add_argument(
        "--columns",
        type=int,
        required=True,
        help="Number of columns of tags (minimum 2)",
    )
    generate_parser.add_argument(
        "--surface-width",
        type=float,
        required=True,
        help="Width of the surface in your chosen units",
    )
    generate_parser.add_argument(
        "--surface-height",
        type=float,
        required=True,
        help="Height of the surface in your chosen units",
    )
    generate_parser.add_argument(
        "--tag-size",
        type=float,
        required=True,
        help="Size of each AprilTag in the same units as surface dimensions",
    )
    generate_parser.add_argument(
        "--margin",
        type=float,
        default=0.0,
        help="Margin from surface edge to first tag (default: 0.0). Can be negative.",
    )
    generate_parser.add_argument(
        "--starting-tag-id",
        type=int,
        default=0,
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
        print(f"Generating surface layout '{args.id}' with {args.rows}x{args.columns} tags...")
        print(f"Surface size: {args.surface_width}x{args.surface_height}")
        print(f"Tag size: {args.tag_size}, Margin: {args.margin}")
        print(f"Starting tag ID: {args.starting_tag_id}")
        print(f"Output directory: {args.output_dir}")

        # Generate the surface layout
        layout = generate_surface_layout_from_rows_and_columns(
            id=args.id,
            rows=args.rows,
            columns=args.columns,
            surface_size=(args.surface_width, args.surface_height),
            tag_size=args.tag_size,
            margin=args.margin,
            starting_tag_id=args.starting_tag_id
        )

        # Save the layout
        save_surface_layout(layout, args.output_dir)

        print("✅ Surface layout generated successfully!")
        print(f"📁 Files saved to: {args.output_dir}/{args.id}")
        print(f"🏷️  Generated {len(layout.tags)} AprilTag markers")
        print("📄 Configuration saved as: surface_layout.yaml")

    except ValueError as e:
        print(f"❌ Error: {e}")
        return
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return
