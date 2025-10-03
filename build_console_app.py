#!/usr/bin/env python3
"""
Build script for Gazedeck Console Application
"""

import subprocess
import sys
import os
import platform

def install_pyinstaller():
    """Install PyInstaller if not already installed."""
    try:
        import PyInstaller
        print("PyInstaller is already installed")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def detect_platform():
    """Detect the current platform and return platform-specific info."""
    system = platform.system().lower()

    if system == "windows":
        return {
            "platform": "windows",
            "lib_extension": ".dll",
            "lib_name": "apriltag.dll",
            "venv_path": ".venv/Lib/site-packages"
        }
    elif system == "darwin":  # macOS
        return {
            "platform": "macos",
            "lib_extension": ".dylib",
            "lib_name": "libapriltag.dylib",
            "venv_path": ".venv/lib/python3.11/site-packages"
        }
    else:
        raise NotImplementedError(f"Platform {system} is not supported yet")

def find_apriltag_libraries(platform_info):
    """Find apriltag library files for the current platform."""
    import glob

    lib_pattern = f"{platform_info['venv_path']}/pupil_apriltags/lib/*{platform_info['lib_extension']}"
    libraries = glob.glob(lib_pattern)

    if not libraries:
        # Also check for alternative names
        if platform_info["platform"] == "macos":
            alt_pattern = f"{platform_info['venv_path']}/pupil_apriltags/lib/libapriltag*.dylib"
            libraries = glob.glob(alt_pattern)

    return libraries

def update_spec_file(platform_info, libraries):
    """Update the PyInstaller spec file with platform-specific library paths."""
    spec_file = "GazedeckConsole.spec"

    # Read the current spec file
    with open(spec_file, 'r') as f:
        content = f.read()

    # Create the binaries section for this platform
    binaries_section = "    binaries=[\n"

    for lib_path in libraries:
        # Convert absolute path to relative path for PyInstaller
        rel_path = os.path.relpath(lib_path)
        binaries_section += f"        ('{rel_path}', 'pupil_apriltags/lib'),\n"

    binaries_section += "    ],"

    # Replace the binaries section in the spec file
    old_binaries_pattern = r"    binaries=\[.*?\],"
    new_content = content.replace(
        "    binaries=[\n        ('.venv/Lib/site-packages/pupil_apriltags/lib/apriltag.dll', 'pupil_apriltags/lib'),\n    ],",
        binaries_section
    )

    # Write back the updated spec file
    with open(spec_file, 'w') as f:
        f.write(new_content)

    print(f"Updated spec file for {platform_info['platform']} with {len(libraries)} library files")

    # Show what would happen on Windows for comparison
    if platform_info['platform'] == 'macos':
        print("\nOn Windows, this build script would:")
        print("- Detect Windows platform")
        print("- Look for: .venv/Lib/site-packages/pupil_apriltags/lib/apriltag.dll")
        print("- Update spec file with Windows DLL path")
        print("- Build executable at: dist/GazedeckConsole/GazedeckConsole.exe")

def build_executable():
    """Build the executable using PyInstaller."""
    print("Building Gazedeck Console executable...")

    # Detect platform and find libraries
    platform_info = detect_platform()
    print(f"Detected platform: {platform_info['platform']}")

    libraries = find_apriltag_libraries(platform_info)
    if not libraries:
        print(f"Warning: No apriltag libraries found for {platform_info['platform']}")
        print("Build may fail if libraries are missing")
    else:
        print(f"Found {len(libraries)} apriltag libraries")
        for lib in libraries:
            print(f"  - {lib}")

    # Update spec file with platform-specific paths
    update_spec_file(platform_info, libraries)

    # Try to clean up old build directory (ignore errors)
    if os.path.exists("dist"):
        try:
            import shutil
            shutil.rmtree("dist")
            print("Cleaned old build directory")
        except PermissionError:
            print("Warning: Could not clean old build directory - some files may be in use.")
            print("Continuing with build...")

    # Build using the spec file
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "GazedeckConsole.spec"
    ]

    try:
        subprocess.check_call(cmd)
        print("Build completed successfully!")

        # Platform-specific executable path message
        exe_name = "GazedeckConsole.exe" if platform_info["platform"] == "windows" else "GazedeckConsole"
        exe_path = f"dist/GazedeckConsole/{exe_name}"
        print(f"Executable created at: {exe_path}")
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