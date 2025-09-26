#!/usr/bin/env python3
"""
Gazedeck Console Application
A minimal console wrapper for Gazedeck CLI commands.
"""

import sys
import os
import argparse
import asyncio
import signal

# Add the current directory to Python path so we can import gazedeck
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gazedeck.main import main as gazedeck_main
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


def print_intro():
    """Print a clean intro screen with description and commands."""
    # Title section
    print("=" * 50)
    print("GAZEDECK CONSOLE APPLICATION")
    print("=" * 50)
    print()

    # Subtitle
    print("Real-time Screen Gaze Tracking with Pupil Labs")
    print()

    # Description
    print("Interactive console for Gazedeck CLI commands.")
    print("No Python environment required - standalone executable.")
    print()

    # Commands section
    print("BASIC COMMANDS:")
    print("-" * 20)

    commands = [
        "gazedeck --help                    Show all available commands",
        "gazedeck generate-surface         Generate surface layout",
        "gazedeck test-device-discovery    Test device discovery",
        "gazedeck stream                   Start gaze streaming",
        "gazedeck mock                     Start mock streaming",
        "exit/quit/q                       Exit the console"
    ]

    for cmd in commands:
        print(f"  {cmd}")
    print()

    # Authors section
    print("AUTHORS:")
    print("-" * 10)
    print("Vojtechovska, M., Popelka, S.")
    print("Department of Geoinformatics, Palacky University Olomouc")
    print()

    # Instructions
    print("Type your commands below or 'exit' to quit:")
    print()


def create_parser():
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(prog="gazedeck", description="Gazedeck setup utilities")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add all command parsers
    add_stream_parser(subparsers)
    add_mock_parser(subparsers)
    add_test_device_discovery_parser(subparsers)
    add_generate_surface_parser(subparsers)
    add_test_surface_layout_discovery_parser(subparsers)

    return parser


def execute_command(command_line):
    """Execute a gazedeck command from command line string."""
    try:
        # Parse the command line
        parser = create_parser()
        args = parser.parse_args(command_line.split())

        # Execute the appropriate command
        if args.command == "test-device-discovery":
            asyncio.run(execute_test_device_discovery(args))
        elif args.command == "stream":
            asyncio.run(execute_stream(args))
        elif args.command == "mock":
            asyncio.run(execute_mock(args))
        elif args.command == "generate-surface":
            execute_generate_surface(args)
        elif args.command == "test-surface-layout-discovery":
            asyncio.run(execute_test_surface_layout_discovery(args))
        else:
            parser.print_help()

    except SystemExit:
        # argparse uses SystemExit for --help, catch it to continue
        pass
    except KeyboardInterrupt:
        print("\n\n[STOP] Command interrupted by user (Ctrl+C)")
        print("Returning to console...")
    except Exception as e:
        print(f"[ERR] Error: {e}")


def main():
    """Main console application loop."""
    print_intro()

    while True:
        try:
            # Get user input
            user_input = input("gazedeck> ").strip()

            # Check for exit commands
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("Goodbye!")
                break

            # Skip empty input
            if not user_input:
                continue

            # Handle gazedeck commands
            if user_input.startswith('gazedeck '):
                command = user_input[9:]  # Remove 'gazedeck ' prefix
                execute_command(command)
            elif user_input == 'gazedeck':
                execute_command('')
            else:
                # Try to execute as a gazedeck command directly
                execute_command(user_input)

        except KeyboardInterrupt:
            # Don't break - just print a newline and continue
            print("\n[STOP] Keyboard interrupt detected, continuing...")
            continue
        except EOFError:
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()
