# receiptpro.spec — PyInstaller spec for ReceiptPro desktop app
# Environment variables expected at build time:
#   TESSERACT_DIR — path to Tesseract installation directory (Windows)
#   POPPLER_DIR   — path to Poppler bin directory

import os
import sys
from pathlib import Path
import customtkinter

block_cipher = None

# ---- Helper to collect a directory tree as datas tuples ----
def collect_dir(src_dir, dest_prefix):
    result = []
    src_dir = Path(src_dir)
    for f in src_dir.rglob("*"):
        if f.is_file():
            rel = f.parent.relative_to(src_dir.parent)
            result.append((str(f), str(Path(dest_prefix) / rel)))
    return result


# ---- customtkinter themes ----
ctk_dir = Path(customtkinter.__file__).parent
ctk_datas = collect_dir(ctk_dir, "customtkinter")

# ---- openpyxl templates ----
import openpyxl
openpyxl_dir = Path(openpyxl.__file__).parent / "templates"
openpyxl_datas = [(str(openpyxl_dir), "openpyxl/templates")]

# ---- Tesseract (Windows only) ----
tesseract_datas = []
tesseract_dir = os.environ.get("TESSERACT_DIR", "")
if tesseract_dir and Path(tesseract_dir).exists():
    tesseract_datas = collect_dir(tesseract_dir, "tesseract")

# ---- Poppler ----
poppler_datas = []
poppler_dir = os.environ.get("POPPLER_DIR", "")
if poppler_dir and Path(poppler_dir).exists():
    poppler_datas = collect_dir(poppler_dir, "poppler")

all_datas = ctk_datas + openpyxl_datas + tesseract_datas + poppler_datas

a = Analysis(
    ["desktop/app.py"],
    pathex=["."],
    binaries=[],
    datas=all_datas,
    hiddenimports=[
        "customtkinter",
        "PIL._tkinter_finder",
        "openpyxl",
        "pytesseract",
        "pdf2image",
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
    name="ReceiptPro",
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
    onefile=True,
)
