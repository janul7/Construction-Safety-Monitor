import argparse
from pathlib import Path

from src.monitor import SafetyMonitor

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".avi", ".mov", ".mkv", ".m4v"}


def parse_args():
    parser = argparse.ArgumentParser(description="Construction Safety Monitor")
    parser.add_argument("--model", required=True, help="Path to best.pt")
    parser.add_argument("--rules", required=True, help="Path to rules.yaml")
    parser.add_argument("--source", required=True, help="Path to image or video")
    parser.add_argument("--output", default="runs/output", help="Output directory")
    return parser.parse_args()


def main():
    args = parse_args()
    source_path = Path(args.source)

    monitor = SafetyMonitor(model_path=args.model, rules_path=args.rules)

    suffix = source_path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        result = monitor.process_image(str(source_path), args.output)
    elif suffix in VIDEO_SUFFIXES:
        result = monitor.process_video(str(source_path), args.output)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    print("\nFinished successfully.\n")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()