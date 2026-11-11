"""Fetch Google's official hand-landmarker model explicitly for local inference.

Remote model assets have their own licenses. This file is NOT included in git.
"""

from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download official MediaPipe hand landmarker")
    parser.add_argument("--output", default="models/hand_landmarker.task")
    args = parser.parse_args()
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        parser.error(f"Refusing to overwrite existing model: {destination}")
    request = urllib.request.Request(MODEL_URL, headers={"User-Agent": "robothand-model-fetch/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read()
    if len(data) < 100_000:
        raise RuntimeError("Downloaded model is unexpectedly small; refusing to save")
    destination.write_bytes(data)
    print(f"Saved {len(data)} bytes to {destination}")
    print("Model is external: verify provenance and licensing before redistributing.")


if __name__ == "__main__":
    main()
