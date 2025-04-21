import os
import subprocess
import shutil
from pathlib import Path

def build_app():
    # Create the spec file for PyInstaller
    spec_content = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('utils', 'utils'),
    ],
    hiddenimports=['flask', 'flask_cors', 'PIL', 'psd_tools', 'numpy', 'cv2', 'skimage'],
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
    name='CreativeAutomationTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='static/icon.icns',
)
"""
    
    # Write the spec file
    with open('CreativeAutomationTool.spec', 'w') as f:
        f.write(spec_content)
    
    # Run PyInstaller
    subprocess.run(['pyinstaller', 'CreativeAutomationTool.spec'])

def create_dmg():
    # Create the DMG
    app_path = 'dist/CreativeAutomationTool.app'
    dmg_path = 'CreativeAutomationTool.dmg'
    
    # Create a temporary directory for the DMG contents
    temp_dir = 'temp_dmg'
    os.makedirs(temp_dir, exist_ok=True)
    
    # Copy the application to the temporary directory
    shutil.copytree(app_path, os.path.join(temp_dir, 'CreativeAutomationTool.app'))
    
    # Create a symbolic link to Applications
    os.symlink('/Applications', os.path.join(temp_dir, 'Applications'))
    
    # Create the DMG
    subprocess.run([
        'hdiutil', 'create',
        '-volname', 'Creative Automation Tool',
        '-srcfolder', temp_dir,
        '-ov', dmg_path
    ])
    
    # Clean up
    shutil.rmtree(temp_dir)

def main():
    print("Building application...")
    build_app()
    
    print("Creating DMG installer...")
    create_dmg()
    
    print("Done! DMG file created: CreativeAutomationTool.dmg")

if __name__ == '__main__':
    main() 