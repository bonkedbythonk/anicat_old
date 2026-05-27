# -*- mode: python ; coding: utf-8 -*-
import os
import sys

# Get the current directory (should be root of the repo if run correctly)
block_cipher = None

a = Analysis(
    ['anicat-server.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../anicat_media', 'anicat_media'),
        ('../version.txt', 'version.txt'),
    ],
    hiddenimports=[
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.protocols.websockets.websockets_impl',
        'uvicorn.protocols.websockets.wsproto_impl',
        'uvicorn.loops.asyncio',
        'uvicorn.loops.auto',
        'uvicorn.logging',
        'fastapi',
        'pydantic_core._pydantic_core',
        'email_validator',
        'starlette',
        # Config modules (imported via re-exports in model.py)
        'anicat_media.core.config.base',
        'anicat_media.core.config.general',
        'anicat_media.core.config.stream',
        'anicat_media.core.config.downloads',
        'anicat_media.core.config.api',
        'anicat_media.core.config.infrastructure',
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
    name='anicat-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
