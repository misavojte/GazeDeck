#!/usr/bin/env python3
"""
Simple Nuitka build script for Gazedeck Console Application
"""

import subprocess
import sys
import os
import platform
import plistlib

def fix_console_app_plist(plist_path):
    """Fix Info.plist to make console app launch properly on macOS."""
    try:
        # Read the existing plist
        with open(plist_path, 'rb') as f:
            plist_data = plistlib.load(f)
        
        # Add LSUIElement to make it a console app that shows terminal
        plist_data['LSUIElement'] = False  # False means it will show in dock and show terminal
        
        # Write back the modified plist
        with open(plist_path, 'wb') as f:
            plistlib.dump(plist_data, f)
        
        print("✅ Fixed Info.plist for console app")
    except Exception as e:
        print(f"⚠️ Could not fix Info.plist: {e}")

def create_terminal_launcher(app_path):
    """Create a launcher script that opens Terminal and runs the console app."""
    try:
        # Get the absolute path to the executable
        exe_path = os.path.join(app_path, "Contents", "MacOS", "GazedeckConsole")
        exe_path = os.path.abspath(exe_path)
        
        # Create a launcher script
        launcher_script = f'''#!/bin/bash
# GazeDeck Console Launcher
# This script opens Terminal and runs the GazeDeck console application

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${{BASH_SOURCE[0]}}" )" &> /dev/null && pwd )"
EXE_PATH="$SCRIPT_DIR/Contents/MacOS/GazedeckConsole"

# Check if executable exists
if [ ! -f "$EXE_PATH" ]; then
    echo "Error: GazeDeckConsole executable not found at $EXE_PATH"
    exit 1
fi

# Open Terminal and run the console app
osascript -e 'tell application "Terminal" to do script "cd \\"$SCRIPT_DIR\\" && \\"$EXE_PATH\\""'
'''
        
        # Write the launcher script
        launcher_path = os.path.join(app_path, "Contents", "MacOS", "launcher.sh")
        with open(launcher_path, 'w') as f:
            f.write(launcher_script)
        
        # Make it executable
        os.chmod(launcher_path, 0o755)
        
        # Update Info.plist to use the launcher instead of the direct executable
        plist_path = os.path.join(app_path, "Contents", "Info.plist")
        with open(plist_path, 'rb') as f:
            plist_data = plistlib.load(f)
        
        # Change the executable to the launcher script
        plist_data['CFBundleExecutable'] = 'launcher.sh'
        
        # Write back the modified plist
        with open(plist_path, 'wb') as f:
            plistlib.dump(plist_data, f)
        
        print("✅ Created Terminal launcher for console app")
    except Exception as e:
        print(f"⚠️ Could not create launcher: {e}")

def set_plist_executable(plist_path: str, executable_name: str) -> None:
    """Set CFBundleExecutable in Info.plist to the given executable name."""
    try:
        with open(plist_path, 'rb') as f:
            plist_data = plistlib.load(f)
        plist_data['CFBundleExecutable'] = executable_name
        with open(plist_path, 'wb') as f:
            plistlib.dump(plist_data, f)
        print(f"✅ Set CFBundleExecutable to '{executable_name}'")
    except Exception as e:
        print(f"⚠️ Could not update CFBundleExecutable: {e}")

def create_command_launcher(dist_root: str, app_bundle_name: str = "console_app.app") -> str:
    """Create a double-clickable .command file that opens Terminal and runs the app binary.

    Returns the path to the created launcher.
    """
    app_bundle_path = os.path.join(dist_root, app_bundle_name)
    exe_rel_path = "console_app.app/Contents/MacOS/GazedeckConsole"
    launcher_path = os.path.join(dist_root, "GazeDeckConsole.command")

    launcher_script = f"""#!/bin/bash
cd "$(dirname "$0")"
exec "./{exe_rel_path}" "$@"
"""

    try:
        with open(launcher_path, 'w') as f:
            f.write(launcher_script)
        os.chmod(launcher_path, 0o755)
        print(f"✅ Created launcher: {launcher_path}")
        return launcher_path
    except Exception as e:
        print(f"⚠️ Could not create .command launcher: {e}")
        return ""

def build_with_nuitka():
    """Build the executable using Nuitka."""

    # Determine platform-specific options
    system = platform.system().lower()
    is_windows = system == "windows"
    is_macos = system == "darwin"

    print("Building Gazedeck Console with Nuitka...")
    print(f"Platform: {system}")

    # Base Nuitka command - use virtual environment
    venv_python = os.path.join(os.path.dirname(__file__), ".venv", "bin", "python")
    if not os.path.exists(venv_python):
        venv_python = sys.executable  # fallback

    cmd = [
        venv_python, "-m", "nuitka",
        "--mode=app",  # App mode for Foundation compatibility
        "--assume-yes-for-downloads",  # Auto-download required tools
        "--output-filename=GazedeckConsole",
        "--output-dir=dist_nuitka",
        "console_app.py"
    ]

    # Platform-specific options
    if is_macos:
        # macOS options for console app that can be double-clicked
        cmd.extend([
            "--macos-app-icon=none",  # Disable icon warning
        ])
    elif is_windows:
        # Windows options (console app with icon disabled by default)
        cmd.extend([
            "--windows-console-mode=force",
            "--windows-icon-from-ico=None",
        ])

    # Include websockets.legacy explicitly to fix compilation issue
    cmd.extend([
        "--include-package=websockets",
        "--include-package=websockets.legacy",
    ])

    # Show progress and run the build
    print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print("✅ Nuitka build completed successfully!")

        # Platform-specific output paths (app mode creates .app bundle on macOS)
        if is_macos:
            exe_path = "dist_nuitka/console_app.app/Contents/MacOS/GazedeckConsole"
        else:
            exe_path = "dist_nuitka/GazedeckConsole.exe"

        print(f"📦 Executable created at: {exe_path}")

        # Fix Info.plist and create a .command launcher (do not change CFBundleExecutable)
        if is_macos and os.path.exists("dist_nuitka/console_app.app/Contents/Info.plist"):
            plist_path = "dist_nuitka/console_app.app/Contents/Info.plist"
            fix_console_app_plist(plist_path)
            set_plist_executable(plist_path, "GazedeckConsole")
            create_command_launcher("dist_nuitka")

        # Show size comparison if PyInstaller build exists
        pyinstaller_path = "dist/GazedeckConsole/GazedeckConsole"
        if is_macos:
            pyinstaller_path = pyinstaller_path.replace(".exe", "")

        if os.path.exists(pyinstaller_path):
            import shutil

            def get_dir_size(path):
                total = 0
                for dirpath, dirnames, filenames in os.walk(path):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        try:
                            total += os.path.getsize(fp)
                        except OSError:
                            pass
                return total

            pyinstaller_size = get_dir_size(pyinstaller_path)
            nuitka_size = get_dir_size(exe_path) if os.path.exists(exe_path) else 0

            print(f"📊 Size comparison:")
            print(f"   PyInstaller: {pyinstaller_size / 1024 / 1024:.1f}MB")
            print(f"   Nuitka:      {nuitka_size / 1024 / 1024:.1f}MB")
            if nuitka_size > 0:
                reduction = (1 - nuitka_size / pyinstaller_size) * 100
                print(f"   Reduction:   {reduction:.1f}% smaller")

        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Nuitka build failed: {e}")
        return False
    except KeyboardInterrupt:
        print("\n⚠️ Build interrupted by user")
        return False

def main():
    """Main build function."""
    print("Gazedeck Console Nuitka Builder")
    print("=" * 35)

    if build_with_nuitka():
        print("\n🎉 Build successful! The Nuitka executable is ready.")
        print("💡 Nuitka provides better performance and smaller size than PyInstaller.")
        if is_macos:
            print("🖱️ On macOS: Double-click 'dist_nuitka/GazeDeckConsole.command' to run in Terminal")
        elif is_windows:
            print("🖱️ On Windows: Double-click 'dist_nuitka/GazedeckConsole.exe' or run from cmd/PowerShell")
    else:
        print("\n❌ Build failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
