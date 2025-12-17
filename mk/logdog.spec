# mk/logdog.spec
# -*- mode: python ; coding: utf-8 -*-

import sys
import os
import glob
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# SPECPATH is automatically defined by PyInstaller
spec_dir = SPECPATH
src_path = os.path.abspath(os.path.join(spec_dir, '..', 'src'))
icon_path = os.path.join(spec_dir, 'logdog.ico')

print(f"Spec file location: {spec_dir}")
print(f"Source path: {src_path}")

# 1. Find the compiled C++ extension (_logdog_core.pyd or .so)
# It should have been built by SCons into the src directory
extensions = []
# Match .pyd (Windows) and .so (Linux)
found_exts = glob.glob(os.path.join(src_path, '_logdog_core*'))
for ext in found_exts:
    if ext.endswith('.pyd') or ext.endswith('.so'):
        print(f"Found C++ Extension: {ext}")
        # Tuple format: (Path to file, Destination folder in bundle)
        extensions.append((ext, '.'))

if not extensions:
    print("WARNING: No _logdog_core extension found! Did you run SCons?")

# 2. Check Icon
if not os.path.exists(icon_path):
    print(f"WARNING: Icon file not found at {icon_path}. Build will proceed with default icon.")
    icon_path = None

# 3. Define Main Script
main_script = os.path.join(src_path, 'main.py')

# 4. Analysis
a = Analysis(
    [main_script],
    pathex=[src_path], # Important: Add src to path so imports work
    binaries=extensions, # Include the C++ extension here
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
    [], # exclude_binaries=True means we are in onedir mode
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

# 5. Collect (Create the folder structure)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='logdog',
    # This creates the _internal folder for dependencies
    contents_directory='_internal' 
)