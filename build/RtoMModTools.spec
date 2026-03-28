# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for RtoM Mod Tools v2 (PySide6 GUI).

Builds a single-file Windows executable that bundles src/, PySide6,
and the data/ templates.  Saves/ and large mod assets are handled
separately by the Inno Setup installer.

Build command:
    pyinstaller build/RtoMModTools.spec --noconfirm
"""

import os

from PyInstaller.utils.hooks import collect_data_files

# SPECPATH is the directory containing this .spec file
PROJECT_ROOT = os.path.dirname(SPECPATH)

block_cipher = None

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'main.py')],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        # Config template
        (os.path.join(PROJECT_ROOT, 'config.ini.example'), '.'),
        # Data: templates, field_values, Tobis_json, manifest — NOT game_extract (4.8 GB, re-extracted on first run)
        (os.path.join(PROJECT_ROOT, 'data', 'templates'), os.path.join('data', 'templates')),
        (os.path.join(PROJECT_ROOT, 'data', 'field_values'), os.path.join('data', 'field_values')),
        (os.path.join(PROJECT_ROOT, 'data', 'Tobis_json'), os.path.join('data', 'Tobis_json')),
        (os.path.join(PROJECT_ROOT, 'data', 'extraction_manifest.ini'), 'data'),
        (os.path.join(PROJECT_ROOT, 'data', 'Imports.json'), 'data'),
        # App icon (for window icon at runtime)
        (os.path.join(PROJECT_ROOT, 'assets', 'icons'), os.path.join('assets', 'icons')),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim unused Qt modules to reduce bundle size
        'PySide6.QtWebEngine',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        'PySide6.Qt3DCore',
        'PySide6.Qt3DRender',
        'PySide6.QtMultimedia',
        'PySide6.QtNetwork',
        'PySide6.QtQml',
        'PySide6.QtQuick',
    ],
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
    name='RtoMModTools',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(PROJECT_ROOT, 'assets', 'icons', 'app_icon.ico'),
)
