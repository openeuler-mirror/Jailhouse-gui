# -*- mode: python ; coding: utf-8 -*-
import glob
import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

ROOT = os.path.abspath(".")
local_hiddenimports = [
    os.path.splitext(os.path.basename(p))[0]
    for p in glob.glob("*.py")
    if os.path.basename(p) not in ("build.py",)
]

a = Analysis(
    ['mainui.py'],
    pathex=[ROOT],
    binaries=[],
    datas=[
        ('platform', 'platform'),
        ('demos', 'demos'),
        ('assets/template', 'template'),
        ('tools', 'tools'),
    ] + collect_data_files('jaraco.text'),
    hiddenimports=local_hiddenimports + ['backports.tarfile'],
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
    name='resource-tool-nonversion',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/images/logo_0.ico'
)
