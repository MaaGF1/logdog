# mk/logdog.spec
# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None

spec_dir = SPECPATH
src_path = os.path.abspath(os.path.join(spec_dir, '..', 'src'))
icon_path = os.path.join(spec_dir, 'logdog.ico')

print(f"Spec file location (SPECPATH): {spec_dir}")
print(f"Source path resolved to: {src_path}")
print(f"Icon path resolved to: {icon_path}")

if not os.path.exists(icon_path):
    print(f"WARNING: Icon file not found at {icon_path}. Build will proceed with default icon.")
    icon_path = None

main_script = os.path.join(src_path, 'main.py')
if not os.path.exists(main_script):
    raise FileNotFoundError(f"Cannot find main.py at: {main_script}")

a = Analysis(
    [main_script],
    pathex=[src_path],
    binaries=[],
    datas=[
        (os.path.join(src_path, 'watchdog.conf'), '.')
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
    [],
    exclude_binaries=True,
    name='logdog',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path 
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='logdog',
)