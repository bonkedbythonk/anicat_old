# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['anicat-server.py'],
    pathex=['/Users/thomas/Documents/randomcode/anicat'],
    binaries=[],
    datas=[('/Users/thomas/Documents/randomcode/anicat/anicat_media', 'anicat_media')],
    hiddenimports=['uvicorn.protocols.http.h11_impl', 'uvicorn.protocols.http.httptools_impl', 'uvicorn.protocols.websockets.websockets_impl', 'uvicorn.protocols.websockets.wsproto_impl', 'uvicorn.loop.asyncio', 'uvicorn.logging', 'fastapi', 'pydantic_core._pydantic_core'],
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
    name='anicat-server-temp',
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
