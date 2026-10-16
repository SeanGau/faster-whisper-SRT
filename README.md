# Whisper Audio Transcription

This project uses the Faster Whisper model to transcribe audio files into Chinese (Traditional) subtitles in SRT format.

## Features

- Transcribes audio files using the Whisper AI model
- Converts Simplified Chinese to Traditional Chinese
- Outputs subtitles in SRT format
- Supports command-line arguments for easy use

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/seangau/faster-whisper-srt.git
   
   cd faster-whisper-SRT
   ```

3. Use uv to install dependencies:   ```
   uv venv
   uv sync 
   ```

### GPU (CUDA) on a fresh Windows machine

`WhisperModel` runs with `device="auto"`, so it picks CUDA whenever a GPU is
present. The ctranslate2 wheel only ships `ctranslate2.dll` and `cudnn64_9.dll`
— it still links against **`cublas64_12.dll`** (CUDA 12), which is not bundled.
On a machine that has never had CUDA installed the first run dies with a missing
`cublas64_12.dll`.

It has to come from **CUDA 12** specifically. A `cu13x` PyTorch wheel does not
help — it ships `cublas64_13.dll`, which does not satisfy the import. Either:

- Install the CUDA 12.x Toolkit. Its installer puts `.../CUDA/v12.6/bin` on the
  system `PATH`, so the DLL is found with no further setup. This is what makes
  the current dev machine work.
- Or `pip install nvidia-cublas-cu12`, then add
  `<site-packages>/nvidia/cublas/bin` to `PATH`. Nothing here imports torch, so
  torch's own `add_dll_directory` call never runs and the plain Windows search
  path is all ctranslate2 gets.

Torch itself is not needed and is deliberately absent from `pyproject.toml` —
nothing imports it, and pinning a CUDA variant would break CPU-only boxes.

## Usage

### GUI

A small tkinter UI for picking files or a folder (no extra dependencies):
```
python gui.py
```
Pick one or more media files, or a whole folder, adjust model / language / keywords /
timecode offset, then hit 開始轉錄. Output is streamed into the log pane.

### Command line

Run the script from the command line, providing the path to your audio file:
```
python whisper.py "your_audio_file.mp3" --keywords "Taiwan"
```
Multiple files and directories can be mixed in one run (the model is only loaded once):
```
python whisper.py "clip.mp4" "podcasts/" --model medium --offset 350
```

## Building a Windows executable

Build on Windows 11 (PyInstaller does not cross-compile):
```
uv sync --group build
uv run pyinstaller FasterWhisperSRT.spec --noconfirm --clean
```

The result is `dist/FasterWhisperSRT/` (~860 MB), a self-contained folder — no
Python or FFmpeg needed on the target machine. Copy the whole folder, then run:

- `FasterWhisperSRT.exe` — the GUI
- `fw-worker.exe` — the transcriber; the GUI spawns it per run, and it also
  works standalone with the same arguments as `whisper.py`

Whisper models are not bundled. They are downloaded from Hugging Face into the
user's cache on first use of each model size, so the first run needs a network
connection.

The build needs the CUDA 12.x Toolkit on the build machine: the spec copies
`cublas64_12.dll` and `cublasLt64_12.dll` (~600 MB) from `%CUDA_PATH%\bin` into
`_internal/`, so a target machine with an NVIDIA GPU needs only a recent driver,
not a CUDA install. Without a GPU, or if the GPU still fails to load cuBLAS,
`fw-worker` falls back to CPU (int8) and keeps going.
