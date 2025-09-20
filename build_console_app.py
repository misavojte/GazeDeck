#!/usr/bin/env python3
"""
Build script for Gazedeck Console Application
"""

import subprocess
import sys
import os

def install_pyinstaller():
    """Install PyInstaller if not already installed."""
    try:
        import PyInstaller
        print("PyInstaller is already installed")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def build_executable():
    """Build the executable using PyInstaller."""
    print("Building Gazedeck Console executable...")
    
    # Clean up old build directory
    if os.path.exists("dist"):
        import shutil
        shutil.rmtree("dist")
        print("Cleaned old build directory")

    # Build using spec file
    cmd = [sys.executable, "-m", "PyInstaller", "--clean", "console_app.spec"]
    
    try:
        subprocess.check_call(cmd)
        print("Build completed successfully!")
        print("Executable created at: dist/GazedeckConsole/GazedeckConsole.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        return False

def main():
    """Main build function."""
    print("Gazedeck Console App Builder")
    print("=" * 30)

    install_pyinstaller()
    
    if build_executable():
        print("\nBuild successful! The executable is ready at dist/GazedeckConsole/GazedeckConsole.exe")
    else:
        print("\nBuild failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
