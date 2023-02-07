# -*- mode: python ; coding: utf-8 -*-

# https://www.pythonguis.com/tutorials/packaging-pyqt5-applications-pyinstaller-macos-dmg/
# https://developer.apple.com/library/archive/documentation/CoreFoundation/Conceptual/CFBundles/BundleTypes/BundleTypes.html

block_cipher = None

a = Analysis(
    ['src/extract_otp_secrets.py'],
    pathex=[],
    binaries=[],
    datas=[('$macos_python_path/__yolo_v3_qr_detector/', '__yolo_v3_qr_detector/')],
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
    name='extract_otp_secrets',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
app = BUNDLE(
    exe,
    name='extract_otp_secrets.app',
    icon=None,
    bundle_identifier='ch.scito.tools.extract_otp_secrets',
    version='$VERSION_STR',
        info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'NSHumanReadableCopyright': 'Copyright © $COPYRIGHT_YEARS Scito.',
        'CFBundleDocumentTypes': [
            # Reference: https://chromium.googlesource.com/chromium/src/+/lkgr/chrome/app/app-Info.plist
            # https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/understanding_utis/understand_utis_conc/understand_utis_conc.html#//apple_ref/doc/uid/TP40001319-CH202-SW6
            # https://developer.apple.com/documentation/uniformtypeidentifiers/system-declared_uniform_type_identifiers
            {
                'CFBundleTypeName': 'GIF image',
                'CFBundleTypeIconFile': 'document.icns',
                'LSItemContentTypes': ['com.compuserve.gif'],
                'LSHandlerRank': 'Alternate',
                'NSExportableTypes': ['public.json','public.comma-separated-values-text','public.plain-text'],
            },
            {
                'CFBundleTypeName': 'JPEG image',
                'CFBundleTypeIconFile': 'document.icns',
                'LSItemContentTypes': ['public.jpeg'],
                'LSHandlerRank': 'Alternate',
                'NSExportableTypes': ['public.json','public.comma-separated-values-text','public.plain-text'],
            },
            {
                'CFBundleTypeName': 'PNG image',
                'CFBundleTypeIconFile': 'document.icns',
                'LSItemContentTypes': ['public.png'],
                'LSHandlerRank': 'Alternate',
                'NSExportableTypes': ['public.json','public.comma-separated-values-text','public.plain-text'],
            },
            {
                'CFBundleTypeName': 'WebP image',
                'CFBundleTypeIconFile': 'document.icns',
                'LSItemContentTypes': ['org.webmproject.webp'],
                'LSHandlerRank': 'Alternate',
                'NSExportableTypes': ['public.json','public.comma-separated-values-text','public.plain-text'],
            },
            {
                'CFBundleTypeName': 'Tiff image',
                'CFBundleTypeIconFile': 'document.icns',
                'LSItemContentTypes': ['public.tiff'],
                'LSHandlerRank': 'Alternate',
                'NSExportableTypes': ['public.json','public.comma-separated-values-text','public.plain-text'],
            },
            {
                'CFBundleTypeName': 'Bmp image',
                'CFBundleTypeIconFile': 'document.icns',
                'LSItemContentTypes': ['com.microsoft.bmp'],
                'LSHandlerRank': 'Alternate',
                'NSExportableTypes': ['public.json','public.comma-separated-values-text','public.plain-text'],
            },
            {
                'CFBundleTypeName': 'Plain text document',
                'CFBundleTypeIconFile': 'document.icns',
                'LSItemContentTypes': ['public.plain-text'],
                'LSHandlerRank': 'Alternate',
                'NSExportableTypes': ['public.json','public.comma-separated-values-text','public.plain-text'],
            },
        ],
    },
)
