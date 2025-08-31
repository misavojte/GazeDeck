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


def main() -> None:
    parser = argparse.ArgumentParser(prog="gazedeck", description="Gazedeck setup utilities")

    # Create subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add command parsers
    add_test_device_discovery_parser(subparsers)
    add_generate_surface_parser(subparsers)

    args = parser.parse_args()

    if args.command == "test-device-discovery":
        asyncio.run(execute_test_device_discovery(args))
    elif args.command == "generate-surface":
        execute_generate_surface(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
