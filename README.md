# Whisper Audio Transcription

This project uses the Faster Whisper model to transcribe audio files into Chinese (Traditional) subtitles in SRT format.

## Features

- Transcribes audio files using the Whisper AI model
- Converts Simplified Chinese to Traditional Chinese
- Outputs subtitles in SRT format
- Supports command-line arguments for easy use

## Requirements

- Python 3.x
- faster_whisper

## Installation

1. Clone this repository:   ```
   git clone https://github.com/seangau/faster-whisper-srt.git
   cd faster-whisper-SRT   ```

2. Install the required packages:   ```
   pip install faster_whisper```

## Usage

Run the script from the command line, providing the path to your audio file:
```
python whisper.py your_audio_file.mp3
```
