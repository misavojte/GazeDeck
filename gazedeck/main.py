from __future__ import annotations

import argparse
import asyncio
import atexit
import gc
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
from gazedeck.cli.command_mock import (
    add_mock_parser,
    execute_mock
)

def _cleanup_all_sessions():
    """Clean up all aiohttp sessions to prevent unclosed session warnings."""
    # Force garbage collection to close any remaining sessions
    gc.collect()

@atexit.register
def _atexit_cleanup():
    """Cleanup function registered with atexit to run when program exits."""
    _cleanup_all_sessions()


def main() -> None:
    parser = argparse.ArgumentParser(prog="gazedeck", description="Gazedeck setup utilities")

    # Create subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add command parsers
    add_stream_parser(subparsers)
    add_mock_parser(subparsers)
    add_test_device_discovery_parser(subparsers)
    add_generate_surface_parser(subparsers)
    add_test_surface_layout_discovery_parser(subparsers)

    args = parser.parse_args()

    if args.command == "test-device-discovery":
        try:
            asyncio.run(execute_test_device_discovery(args))
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\n🛑 Received keyboard interrupt, exiting gracefully...")
            return
    elif args.command == "stream":
        try:
            asyncio.run(execute_stream(args))
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\n🛑 Received keyboard interrupt, exiting gracefully...")
            # Force immediate cleanup of any remaining sessions
            _cleanup_all_sessions()
            return
    elif args.command == "mock":
        try:
            asyncio.run(execute_mock(args))
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\n🛑 Received keyboard interrupt, exiting gracefully...")
            return
    elif args.command == "generate-surface":
        execute_generate_surface(args)
    elif args.command == "test-surface-layout-discovery":
        try:
            asyncio.run(execute_test_surface_layout_discovery(args))
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\n🛑 Received keyboard interrupt, exiting gracefully...")
            return
    else:
        parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Received keyboard interrupt, exiting gracefully...")
        _cleanup_all_sessions()
        # Exit cleanly without showing traceback
        exit(0)
    except asyncio.CancelledError:
        # This can occur during shutdown - suppress it
        print("\n🛑 Shutdown completed")
        _cleanup_all_sessions()
        exit(0)
