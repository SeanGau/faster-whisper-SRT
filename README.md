# Whisper Audio Transcription

This project uses the Faster Whisper model to transcribe audio files into Chinese (Traditional) subtitles in SRT format.

## Features

- Transcribes audio files using the Whisper AI model
- Converts Simplified Chinese to Traditional Chinese
- Outputs subtitles in SRT format
- Supports command-line arguments for easy use

## Use in Local

1. Clone this repository:
   ```
   git clone https://github.com/seangau/faster-whisper-srt.git
   
   cd faster-whisper-SRT
   ```

2. Use uv to install dependencies:
   ```
   uv venv
   uv sync 
   ```

3. Run the script from the command line, providing the path to your audio file:
```
python whisper.py "your_audio_file.mp3" --keywords "Taiwan"
```

## Use in Google Colab:

1. Go to https://colab.research.google.com/
2. Open notebook, import `faster_whisper_SRT.ipynb` from https://github.com/SeanGau/faster-whisper-SRT/
3. Run with GPU (T4 for free)
