from faster_whisper import WhisperModel
from pathlib import Path
import opencc
import argparse

# parse command line arguments
parser = argparse.ArgumentParser(
    description="Transcribe an audio file using Whisper and save as SRT."
)
parser.add_argument("filename", type=str, help="Path to the audio file")
parser.add_argument("--model", type=str, help="Model to use", default="large-v3")
parser.add_argument(
    "--language", type=str, help="Language of the audio file", default="zh"
)
parser.add_argument(
    "--keywords", type=str, help="Initial prompt for the model", default=""
)
parser.add_argument(
    "--offset", type=int, help="Offset for the timecode (ms)", default=500
)
args = parser.parse_args()
print(args)

# Load Whisper model
model = WhisperModel(args.model)
filename = args.filename
converter = opencc.OpenCC("s2tw")

# Transcribe the audio file
initial_prompt = (
    f"This is a conversation about: 生成式 AI, ChatGPT, Claude AI, Prompt, {args.filename.split('/')[-1].split('.')[0]}, {args.keywords}"
)

segments, info = model.transcribe(
    filename,
    language=args.language,
    initial_prompt=initial_prompt,
    word_timestamps=True,
    vad_filter=True,
    vad_parameters={"min_silence_duration_ms": 500},
)


# Function to format time in SRT format with more precise milliseconds
def format_timestamp(seconds):
    seconds += args.offset / 1000
    milliseconds = int(seconds * 1000) % 1000
    seconds = int(seconds)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


# Save SRT
srt_file_path = Path(filename + ".srt")
with open(srt_file_path, "w", encoding="utf-8") as srt_file:
    id = 1
    for i, segment in enumerate(segments, start=1):
        start = format_timestamp(segment.start)
        current_text = ""
        for word in segment.words:
            current_text += word.word
            end = format_timestamp(word.end)
            # split text by comma or 逗號 into multiple lines
            if "," in word.word or "，" in word.word or word == segment.words[-1]:
                current_text = current_text.replace(",", "").replace("，", "").strip()
                if "zh" in args.language:
                    current_text = converter.convert(current_text)
                line = f"{id}\n{start} --> {end}\n{current_text}"
                print(line, flush=True)
                srt_file.write(f"{line}\n\n")
                start = format_timestamp(word.end)
                current_text = ""
                id += 1

print(f"SRT file saved to {srt_file_path}")
