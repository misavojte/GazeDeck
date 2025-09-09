# -*- mode: python ; coding: utf-8 -*-

import os
import glob

block_cipher = None

# Collect pupil_apriltags DLL files
def collect_pupil_apriltags_binaries():
    """Collect DLL files from pupil_apriltags package."""
    try:
        import pupil_apriltags
        base_path = os.path.dirname(pupil_apriltags.__file__)
        dll_files = glob.glob(os.path.join(base_path, '**', '*.dll'), recursive=True)
        binaries = []
        for dll in dll_files:
            # Calculate relative path within the package
            rel_path = os.path.relpath(dll, base_path)
            # Destination should be pupil_apriltags/lib/ to match what the library expects
            dest_dir = os.path.join('pupil_apriltags', os.path.dirname(rel_path))
            binaries.append((dll, dest_dir))
        return binaries
    except ImportError:
        return []

# Collect pupil_apriltags data files
def collect_pupil_apriltags_datas():
    """Collect data files from pupil_apriltags package."""
    try:
        import pupil_apriltags
        base_path = os.path.dirname(pupil_apriltags.__file__)
        data_files = []
        for root, dirs, files in os.walk(base_path):
            for file in files:
                if not file.endswith('.dll') and not file.endswith('.lib'):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, base_path)
                    dest_dir = os.path.join('pupil_apriltags', os.path.dirname(rel_path))
                    data_files.append((full_path, dest_dir))
        return data_files
    except ImportError:
        return []

a = Analysis(
    ['console_app.py'],
    pathex=[],
    binaries=collect_pupil_apriltags_binaries(),
    datas=collect_pupil_apriltags_datas(),
    hiddenimports=[
        'gazedeck.main',
        'gazedeck.cli.command_test_device_discovery',
        'gazedeck.cli.command_generate_surface',
        'gazedeck.cli.command_test_surface_layout_discovery',
        'gazedeck.cli.command_stream',
        'gazedeck.cli.command_mock',
        'pupil_labs_realtime_api',
        'pupil_labs.realtime_api',
        'pupil_labs.realtime_api.discovery',
        'pupil_labs.realtime_api.streaming',
        'pupil_apriltags',
        'pupil_apriltags.bindings',
        'zeroconf',
        'zeroconf._core',
        'zeroconf._engine',
        'zeroconf._listener',
        'zeroconf._services',
        'zeroconf._services.info',
        'zeroconf._services.browser',
        'zeroconf._services.registry',
        'zeroconf._services.types',
        'zeroconf._utils',
        'zeroconf._utils.ipaddress',
        'zeroconf._utils.name',
        'zeroconf._utils.net',
        'zeroconf._utils.time',
        'zeroconf._utils.asyncio',
        'zeroconf._handlers',
        'zeroconf._handlers.answers',
        'zeroconf._handlers.multicast_outgoing_queue',
        'zeroconf._handlers.query_handler',
        'zeroconf._handlers.record_manager',
        'zeroconf._protocol',
        'zeroconf._protocol.incoming',
        'zeroconf._protocol.outgoing',
        'websockets',
        'PIL',
        'cv2',
        'yaml',
        'pynput',
        'pynput.keyboard',
        'pynput.mouse',
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
        'pynput.keyboard._xorg',
        'pynput.mouse._xorg',
        'pynput._util',
        'pynput._util.win32',
        'colorama',
        'colorama.initialise',
        'colorama.ansi',
        'colorama.winterm',
        'colorama.win32',
        'surface_tracker',
        'surface_tracker.surface',
        'surface_tracker.marker',
        'surface_tracker.coordinate_space',
        'surface_tracker.core',
        'surface_tracker.geometry',
        'surface_tracker.calibration',
        'numpy',
        'numpy.typing',
        'dataclasses',
        'asyncio',
        'typing',
        'struct',
        'math',
        'json',
        'random',
        'threading',
        'contextlib',
        'uuid',
        'ifaddr',
        'av',
        'pywin32',
        'pythonnet',
        'pywin32-ctypes'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GazedeckConsole',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
