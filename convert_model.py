"""Convert a Transformers Whisper fine-tune into CTranslate2 format for faster-whisper.

Default: the official MediaTek-Research/Breeze-ASR-26 weights into
models/Breeze-ASR-26-ct2, which whisper.py then uses for --model breeze-asr-26
in place of the community conversion on the Hub.

Needs torch + transformers (a few GB). They are deliberately not project
dependencies, since transformers pulls a newer huggingface-hub/tokenizers into
the transcriber's environment; run it with a one-off overlay instead:
    uv run --with "transformers[torch]" python convert_model.py
"""

import argparse
import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Copied next to model.bin so faster-whisper picks up the right tokenizer and
# feature extractor (e.g. 128 mel bins for large-v3 based models).
EXTRA_FILES = ("tokenizer.json", "preprocessor_config.json")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--model",
        default="MediaTek-Research/Breeze-ASR-26",
        help="Hugging Face repo id or local folder of the Transformers model",
    )
    parser.add_argument(
        "--output",
        default=os.path.join(APP_DIR, "models", "Breeze-ASR-26-ct2"),
        help="Output directory (default: models/Breeze-ASR-26-ct2)",
    )
    parser.add_argument(
        "--quantization",
        default="float16",
        choices=["float16", "int8_float16", "int8", "float32"],
        help="Weight type stored on disk; ctranslate2 converts on load if the "
        "device needs another one (default: float16)",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite --output")
    return parser.parse_args(argv)


def available_extra_files(model):
    if os.path.isdir(model):
        names = set(os.listdir(model))
    else:
        from huggingface_hub import list_repo_files

        names = set(list_repo_files(model))
    return [name for name in EXTRA_FILES if name in names]


def main(argv=None):
    args = parse_args(argv)
    try:
        # ctranslate2's converter only imports these once it starts converting.
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError as error:
        print(
            f"{error}\nRun it with: "
            'uv run --with "transformers[torch]" python convert_model.py',
            file=sys.stderr,
        )
        return 1
    from ctranslate2.converters import TransformersConverter

    copy_files = available_extra_files(args.model)
    missing = sorted(set(EXTRA_FILES) - set(copy_files))
    if missing:
        print(f"Note: {args.model} has no {', '.join(missing)}; faster-whisper "
              "falls back to its defaults for those.")

    print(f"Converting {args.model} -> {args.output} ({args.quantization})…")
    TransformersConverter(args.model, copy_files=copy_files).convert(
        args.output, quantization=args.quantization, force=args.force
    )
    print(f"Done. Use it with --model \"{args.output}\" (for the default "
          "output folder, --model breeze-asr-26 picks it up automatically).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
