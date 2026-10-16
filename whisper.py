from faster_whisper import WhisperModel
from pathlib import Path
import opencc
import argparse
import logging
import os
import sys
import time

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


def setup_logging():
    """Send faster-whisper's own progress logs (audio duration, VAD, language
    detection) to stdout so the GUI log pane shows what happens between the
    subtitle lines."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("  [%(name)s] %(message)s"))
    logger = logging.getLogger("faster_whisper")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)


def format_duration(seconds):
    seconds = int(seconds)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


# Function to format time in SRT format with more precise milliseconds
def format_timestamp(seconds, offset_ms):
    seconds += offset_ms / 1000
    milliseconds = int(seconds * 1000) % 1000
    seconds = int(seconds)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def transcribe(model, converter, filename, args, index=1, total=1):
    # Transcribe the audio file
    title = os.path.splitext(os.path.basename(filename))[0]
    initial_prompt = f"This is a conversation about: {title}, {args.keywords}"

    started = time.monotonic()
    print(f"\n[{index}/{total}] Transcribing {filename}", flush=True)

    segments, info = model.transcribe(
        filename,
        language=args.language,
        initial_prompt=initial_prompt,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )

    print(
        f"  audio {format_duration(info.duration)}, "
        f"language {info.language} ({info.language_probability:.2f})",
        flush=True,
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

            percent = min(100, segment.end / info.duration * 100) if info.duration else 100
            print(
                f"  -- {percent:5.1f}%  {format_duration(segment.end)}"
                f" / {format_duration(info.duration)}"
                f"  {id - 1} lines  {time.monotonic() - started:.0f}s",
                flush=True,
            )

    print(
        f"SRT file saved to {srt_file_path} "
        f"({id - 1} lines, {time.monotonic() - started:.1f}s)",
        flush=True,
    )


# Releasing a WhisperModel tears down ctranslate2, which crashes on Windows
# (0xC0000409) after transcribing with an explicit --language plus word
# timestamps. Holding the model here keeps it alive past main() so the process
# can leave through os._exit below instead.
_model = None
_dead_models = []


def is_missing_cuda_library(error):
    # ctranslate2 only loads cublas64_12.dll / cudnn on the first GPU call, so a
    # box with a GPU but no CUDA 12 runtime fails mid-transcribe, not at load.
    message = str(error).lower()
    return "cublas" in message or "cudnn" in message or "cuda" in message


def main(argv=None):
    global _model

    # The GUI reads this process' stdout through a pipe; keep it UTF-8 and
    # line buffered so the log pane updates while transcribing.
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

    args = parse_args(argv)
    setup_logging()
    print(args, flush=True)

    # Expand directories up front so the progress counter knows the real total.
    files = []
    for target in args.filename:
        if os.path.isdir(target):
            found = sorted(
                os.path.join(target, f)
                for f in os.listdir(target)
                if f.lower().endswith(MEDIA_EXTENSIONS)
            )
            print(f"Found {len(found)} media file(s) in {target}", flush=True)
            files.extend(found)
        else:
            files.append(target)

    if not files:
        print("No media files to transcribe.", flush=True)
        return 1

    # Load Whisper model (downloads it on first use, which can take a while)
    print(f"Loading model {args.model}…", flush=True)
    started = time.monotonic()
    model = _model = WhisperModel(args.model)
    converter = opencc.OpenCC("s2tw")
    print(f"Model ready in {time.monotonic() - started:.1f}s", flush=True)

    for index, file in enumerate(files, start=1):
        try:
            transcribe(model, converter, file, args, index=index, total=len(files))
        except RuntimeError as error:
            if model.model.device != "cuda" or not is_missing_cuda_library(error):
                raise
            print(
                f"\nGPU unavailable ({error}).\n"
                "Falling back to CPU — install the CUDA 12 runtime to use the GPU "
                "(see README).",
                flush=True,
            )
            # Keep the broken GPU model referenced; releasing it may crash (see _model).
            _dead_models.append(model)
            model = _model = WhisperModel(args.model, device="cpu", compute_type="int8")
            transcribe(model, converter, file, args, index=index, total=len(files))

    print(f"\nAll done: {len(files)} file(s).", flush=True)
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
