# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['console_app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'gazedeck.main',
        'gazedeck.cli.command_test_device_discovery',
        'gazedeck.cli.command_generate_surface',
        'gazedeck.cli.command_test_surface_layout_discovery',
        'gazedeck.cli.command_stream',
        'gazedeck.cli.command_mock',
        'pupil_labs_realtime_api',
        'websockets',
        'PIL',
        'cv2',
        'yaml',
        'pynput',
        'colorama',
        'colorama.initialise',
        'colorama.ansi',
        'colorama.winterm',
        'colorama.win32'
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
