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

try:
    from colorama import init, Fore, Back, Style
    COLORAMA_AVAILABLE = True
    init(autoreset=True)  # Initialize colorama
except ImportError:
    COLORAMA_AVAILABLE = False

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
    if COLORAMA_AVAILABLE:
        light_cyan = Fore.LIGHTCYAN_EX
        reset = Style.RESET_ALL
    else:
        light_cyan = reset = ""

    # Title
    print(f"{light_cyan}GAZEDECK CONSOLE APPLICATION{reset}")
    print(f"{light_cyan}{'─' * 30}{reset}")

    # Subtitle
    print(f"{light_cyan}Real-time Screen Gaze Tracking with Pupil Labs{reset}")
    print()

    # Description
    print(f"{light_cyan}Interactive console for Gazedeck CLI commands.{reset}")
    print(f"{light_cyan}No Python environment required - standalone executable.{reset}")
    print()

    # Commands section
    print(f"{light_cyan}BASIC COMMANDS:{reset}")
    print(f"{light_cyan}{'─' * 15}{reset}")

    commands = [
        "gazedeck --help                    Show all available commands",
        "gazedeck generate-surface         Generate surface layout",
        "gazedeck test-device-discovery    Test device discovery",
        "gazedeck stream                   Start gaze streaming",
        "gazedeck mock                     Start mock streaming",
        "exit/quit/q                       Exit the console"
    ]

    for cmd in commands:
        print(f"{light_cyan}{cmd}{reset}")
    print()

    # Authors section
    print(f"{light_cyan}AUTHORS:{reset}")
    print(f"{light_cyan}{'─' * 8}{reset}")
    print(f"{light_cyan}Vojtechovska, M., Popelka, S. at Department of Geoinformatics, Palacky University Olomouc{reset}")
    print()

    # Instructions
    print(f"{light_cyan}Type your commands below or 'exit' to quit:{reset}")
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
        print("\n\nCommand interrupted by user (Ctrl+C)")
        print("Returning to console...")
    except Exception as e:
        print(f"Error: {e}")


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
            print("\n")
            continue
        except EOFError:
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()
