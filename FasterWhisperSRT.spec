# -*- mode: python ; coding: utf-8 -*-
"""Builds dist/FasterWhisperSRT/ containing two executables that share one _internal:

  FasterWhisperSRT.exe  windowed tkinter GUI (gui.py)
  fw-worker.exe         console transcriber (whisper.py), spawned by the GUI

The GUI stays a separate, tiny executable so it starts instantly and so the
transcription still runs in a killable child process (the 停止 button).
"""

from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

# Native libs + data files that are loaded at runtime by path, not by import:
#   faster_whisper -> assets/silero_vad_v6.onnx
#   opencc         -> clib/share/opencc/*.json + *.ocd2 dictionaries
#   ctranslate2    -> ctranslate2.dll, libiomp5md.dll, cudnn64_9.dll
#   onnxruntime    -> capi/*.dll (silero VAD inference)
#   av             -> bundled FFmpeg DLLs in av.libs
for package in ("faster_whisper", "opencc", "ctranslate2", "onnxruntime", "av"):
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

# opencc imports its extension through a try/except fallback.
hiddenimports += ["opencc.clib", "opencc.clib.opencc_clib"]
# huggingface_hub picks hf_xet up dynamically; without it model downloads fall
# back to plain HTTP, which is noticeably slower for the large models.
hiddenimports += ["hf_xet"]

worker_a = Analysis(
    ["whisper.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
    optimize=0,
)

gui_a = Analysis(
    ["gui.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["faster_whisper", "ctranslate2", "onnxruntime", "av", "numpy", "opencc"],
    noarchive=False,
    optimize=0,
)

worker_pyz = PYZ(worker_a.pure)
gui_pyz = PYZ(gui_a.pure)

worker_exe = EXE(
    worker_pyz,
    worker_a.scripts,
    [],
    exclude_binaries=True,
    name="fw-worker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

gui_exe = EXE(
    gui_pyz,
    gui_a.scripts,
    [],
    exclude_binaries=True,
    name="FasterWhisperSRT",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    gui_exe,
    worker_exe,
    worker_a.binaries,
    worker_a.datas,
    gui_a.binaries,
    gui_a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="FasterWhisperSRT",
)
