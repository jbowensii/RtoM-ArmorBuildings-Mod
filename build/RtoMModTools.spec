# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for RtoM Mod Tools.

Builds a single-file Windows executable that bundles the src/ package.
Data files (mod assets, localization) are NOT bundled in the exe —
they are handled separately by the Inno Setup installer from
build/staging/.

Build command:
    pyinstaller build/RtoMModTools.spec --noconfirm
"""

import os
import sys

# Project root is one level up from this spec file
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(SPECPATH)))

block_cipher = None

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'main.py')],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        # Bundle config template so the exe can create a default on first run
        (os.path.join(PROJECT_ROOT, 'config.ini.example'), '.'),
    ],
    hiddenimports=[],
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
    name='RtoMModTools',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # CLI app for now; change to False when GUI is added
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon=os.path.join(PROJECT_ROOT, 'assets', 'icons', 'app_icon.ico'),
)
