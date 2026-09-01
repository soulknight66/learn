"""Small opt-in microbenchmark for reference layer application."""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import statistics
import tarfile
import tempfile
import time

from minibox.archive import apply_layer


def positive(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def build_layer(path: Path, files: int, bytes_per_file: int) -> None:
    payload = b"x" * bytes_per_file
    with tarfile.open(path, "w") as archive:
        for index in range(files):
            info = tarfile.TarInfo(f"data/file-{index:06d}")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", type=positive, default=100)
    parser.add_argument("--bytes-per-file", type=positive, default=4096)
    parser.add_argument("--repeats", type=positive, default=5)
    arguments = parser.parse_args()

    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary)
        layer = base / "layer.tar"
        build_layer(layer, arguments.files, arguments.bytes_per_file)
        samples: list[float] = []
        for repeat in range(arguments.repeats):
            rootfs = base / f"rootfs-{repeat}"
            started = time.perf_counter()
            stats = apply_layer(layer, rootfs)
            samples.append(time.perf_counter() - started)
        result = {
            "bytes_per_file": arguments.bytes_per_file,
            "files": arguments.files,
            "median_seconds": statistics.median(samples),
            "repeats": arguments.repeats,
            "samples_seconds": samples,
            "validation_label": "LOCAL_MICROBENCHMARK_ONLY",
            "written_bytes_per_repeat": stats.bytes_written,
        }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
