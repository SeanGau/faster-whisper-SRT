from faster_whisper import WhisperModel
from pathlib import Path
import opencc
import argparse
import os
import sys

MEDIA_EXTENSIONS = (
    ".mp3", ".wav", ".aac", ".m4a", ".flac", ".ogg",
    ".mp4", ".mkv", ".mov", ".webm", ".avi", ".flv",
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Transcribe an audio file using Whisper and save as SRT."
    )
    parser.add_argument(
        "filename", type=str, nargs="+", help="Path to the audio file(s) or directory"
    )
    parser.add_argument("--model", type=str, help="Model to use", default="medium")
    parser.add_argument(
        "--language", type=str, help="Language of the audio file", default="zh"
    )
    parser.add_argument(
        "--keywords", type=str, help="Initial prompt for the model", default=""
    )
    parser.add_argument(
        "--offset", type=int, help="Offset for the timecode (ms)", default=0
    )
    return parser.parse_args(argv)


# Function to format time in SRT format with more precise milliseconds
def format_timestamp(seconds, offset_ms):
    seconds += offset_ms / 1000
    milliseconds = int(seconds * 1000) % 1000
    seconds = int(seconds)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def transcribe(model, converter, filename, args):
    # Transcribe the audio file
    title = os.path.splitext(os.path.basename(filename))[0]
    initial_prompt = f"This is a conversation about: {title}, {args.keywords}"

    segments, info = model.transcribe(
        filename,
        language=args.language,
        initial_prompt=initial_prompt,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )

    # Save SRT
    srt_file_path = Path(filename + ".srt")
    with open(srt_file_path, "w", encoding="utf-8") as srt_file:
        id = 1
        for i, segment in enumerate(segments, start=1):
            start = format_timestamp(segment.start, args.offset)
            current_text = ""
            for word in segment.words:
                current_text += word.word
                end = format_timestamp(word.end, args.offset)
                # split text by comma or 逗號 into multiple lines
                if "," in word.word or "，" in word.word or word == segment.words[-1]:
                    current_text = current_text.replace(",", "").replace("，", "").strip()
                    if "zh" in args.language:
                        current_text = converter.convert(current_text)
                    line = f"{id}\n{start} --> {end}\n{current_text}"
                    print(line, flush=True)
                    srt_file.write(f"{line}\n\n")
                    start = format_timestamp(word.end, args.offset)
                    current_text = ""
                    id += 1

    print(f"SRT file saved to {srt_file_path}")


# Releasing a WhisperModel tears down ctranslate2, which crashes on Windows
# (0xC0000409) after transcribing with an explicit --language plus word
# timestamps. Holding the model here keeps it alive past main() so the process
# can leave through os._exit below instead.
_model = None


def main(argv=None):
    global _model

    # The GUI reads this process' stdout through a pipe; keep it UTF-8 and
    # line buffered so the log pane updates while transcribing.
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

    args = parse_args(argv)
    print(args)

    # Load Whisper model
    model = _model = WhisperModel(args.model)
    converter = opencc.OpenCC("s2tw")

    for target in args.filename:
        if os.path.isdir(target):
            # run through all files in the directory
            files = sorted(
                f for f in os.listdir(target) if f.lower().endswith(MEDIA_EXTENSIONS)
            )
            print(f"Transcribing all files in {target}")
            print(f"Total files: {len(files)}")
            for file in files:
                transcribe(model, converter, os.path.join(target, file), args)
        else:
            transcribe(model, converter, target, args)

    return 0


if __name__ == "__main__":
    code = main()
    if sys.stdout is not None:
        sys.stdout.flush()
    # Leave without running finalization, which would release _model and crash
    # (see above); the GUI would report that as a bogus failure code. The SRT is
    # closed and stdout flushed by now. A real error still raises out of main()
    # and exits non-zero the normal way.
    os._exit(code)
