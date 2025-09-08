#!/usr/bin/env python3
"""
Build script for Gazedeck Console Application
"""

import subprocess
import sys
import os
import argparse

def install_pyinstaller():
    """Install PyInstaller if not already installed."""
    try:
        import PyInstaller
        print("PyInstaller is already installed")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def cleanup_old_executable(force=False):
    """Clean up the old executable if it exists and is not locked."""
    exe_path = "dist/GazedeckConsole.exe"
    if os.path.exists(exe_path):
        try:
            os.remove(exe_path)
            print(f"Removed old executable: {exe_path}")
            return True
        except PermissionError:
            if force:
                print(f"Force mode: Attempting to kill processes using {exe_path}...")
                # Try to kill any processes using the executable
                try:
                    import psutil
                    for proc in psutil.process_iter(['pid', 'name', 'exe']):
                        try:
                            if proc.info['exe'] and exe_path in proc.info['exe']:
                                print(f"Killing process {proc.info['pid']} ({proc.info['name']})")
                                proc.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    # Try removal again after killing processes
                    os.remove(exe_path)
                    print(f"Successfully removed executable after killing processes: {exe_path}")
                    return True
                except ImportError:
                    print("psutil not available for process killing. Install with: pip install psutil")
                except Exception as e:
                    print(f"Could not kill processes: {e}")

            print(f"Warning: Cannot remove {exe_path} - it may be in use by another process.")
            print("Please close any running instances of GazedeckConsole.exe and try again.")
            print("Alternatively, you can manually delete the file or kill the process using Task Manager.")
            if not force:
                print("You can also try running with --force to attempt automatic cleanup.")
            return False
        except OSError as e:
            print(f"Warning: Could not remove {exe_path}: {e}")
            return False
    return True

def build_executable(force=False):
    """Build the executable using PyInstaller."""
    print("Building Gazedeck Console executable...")

    # Use the spec file we created
    spec_file = "console_app.spec"

    if not os.path.exists(spec_file):
        print(f"Error: {spec_file} not found!")
        return False

    # Clean up old executable first
    if not cleanup_old_executable(force=force):
        return False

    try:
        # First try: Use the spec file (most reliable)
        cmd = [sys.executable, "-m", "PyInstaller", "--clean", spec_file]
        subprocess.check_call(cmd)
        print("Build completed successfully!")
        print("Executable created at: dist/GazedeckConsole.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Spec file build failed: {e}")
        print("Trying alternative build method...")

        try:
            # Alternative: Build directly from Python file with --onefile and --noconfirm
            cmd = [
                sys.executable, "-m", "PyInstaller",
                "--onefile",
                "--noconfirm",
                "--clean",
                "--name=GazedeckConsole",
                "console_app.py"
            ]
            subprocess.check_call(cmd)
            print("Alternative build completed successfully!")
            print("Executable created at: dist/GazedeckConsole.exe")
            return True
        except subprocess.CalledProcessError as e2:
            print(f"Alternative build also failed: {e2}")
            return False

def main():
    """Main build function."""
    parser = argparse.ArgumentParser(description="Build Gazedeck Console Application")
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force cleanup of old executable by killing running processes"
    )
    args = parser.parse_args()

    print("Gazedeck Console App Builder")
    print("=" * 30)

    if args.force:
        print("Force mode enabled - will attempt to kill running processes if needed")

    # Install PyInstaller if needed
    install_pyinstaller()

    # Build the executable
    if build_executable(force=args.force):
        print("\nBuild successful! The executable is ready at dist/GazedeckConsole.exe")
        print("You can distribute this .exe file - it doesn't require Python to run.")
    else:
        print("\nBuild failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
