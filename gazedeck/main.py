"""Main entry point for GazeDeck application"""

from .gui import create_gui


def main():
    """Main entry point for the gazedeck command"""
    print("Starting GazeDeck GUI...")
    create_gui()


if __name__ == "__main__":
    main()
