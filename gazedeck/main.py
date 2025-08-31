from __future__ import annotations

import argparse
import asyncio
from gazedeck.cli.command_test_device_discovery import (
    add_test_device_discovery_parser,
    execute_test_device_discovery
)
from gazedeck.cli.command_generate_surface import (
    add_generate_surface_parser,
    execute_generate_surface
)
from gazedeck.cli.command_test_surface_layout_discovery import (
    add_test_surface_layout_discovery_parser,
    execute_test_surface_layout_discovery
)
from gazedeck.cli.command_stream import (
    add_stream_parser,
    execute_stream
)


def main() -> None:
    parser = argparse.ArgumentParser(prog="gazedeck", description="Gazedeck setup utilities")

    # Create subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add command parsers
    add_stream_parser(subparsers)
    add_test_device_discovery_parser(subparsers)
    add_generate_surface_parser(subparsers)
    add_test_surface_layout_discovery_parser(subparsers)

    args = parser.parse_args()

    if args.command == "test-device-discovery":
        asyncio.run(execute_test_device_discovery(args))
    elif args.command == "stream":
        asyncio.run(execute_stream(args))
    elif args.command == "generate-surface":
        execute_generate_surface(args)
    elif args.command == "test-surface-layout-discovery":
        asyncio.run(execute_test_surface_layout_discovery(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
