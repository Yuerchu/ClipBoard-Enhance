# -*- mode: python ; coding: utf-8 -*-
# 测试模式：程序将展示终端内容，并且强制启用 Debug 等级日志

add_files = [
    ('static\\MapleMono-NF-CN-Regular.ttf', 'static'),
    ('static\\favicon.ico', 'static'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=add_files,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='clipboard',
    icon='static/favicon.ico',
    debug=True,
    bootloader_ignore_signals=True,
    strip=True,
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