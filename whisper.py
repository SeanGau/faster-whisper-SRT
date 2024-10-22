from faster_whisper import WhisperModel
from pathlib import Path
import opencc
import argparse

# 解析命令列參數
parser = argparse.ArgumentParser(description='Transcribe an audio file using Whisper and save as SRT.')
parser.add_argument('filename', type=str, help='Path to the audio file')
args = parser.parse_args()

# Load Whisper model
model = WhisperModel("large-v3")
filename = args.filename
converter = opencc.OpenCC('s2tw')

# Transcribe the audio file
segments, info = model.transcribe(filename, language="zh")

# Function to format time in SRT format with more precise milliseconds
def format_timestamp(seconds):
    milliseconds = int(seconds * 1000) % 1000
    seconds = int(seconds)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

# Save SRT
srt_file_path = Path(filename + ".srt")
with open(srt_file_path, "w", encoding="utf-8") as srt_file:
    for i, segment in enumerate(segments, start=1):
        start = format_timestamp(segment.start)
        end = format_timestamp(segment.end)
        text = converter.convert(segment.text)
        line = f"{i}\n{start} --> {end}\n{text}"
        print(line, flush=True)
        srt_file.write(f"{line}\n\n")

print(f"SRT file saved to {srt_file_path}")
