"""Download and verify the official UCI Student Performance dataset.

Usage (from backend/):

    python -m analytics.data.download            # download if missing, verify
    python -m analytics.data.download --verify   # verify existing files only
    python -m analytics.data.download --force    # re-download and overwrite
    python -m analytics.data.download --raw-dir /other/path

The official archive (https://archive.ics.uci.edu/dataset/320/student+performance) is
a zip containing ``student.zip``, which in turn contains the two cohort CSVs and the
UCI attribute notes. Only the CSVs and ``student.txt`` are extracted; archives are
never written to disk. Each CSV is checked against a pinned SHA-256 so a changed or
corrupted upstream file is detected rather than silently used.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

from analytics.data.cohorts import COHORTS

DATASET_PAGE = "https://archive.ics.uci.edu/dataset/320/student+performance"
ARCHIVE_URL = "https://archive.ics.uci.edu/static/public/320/student+performance.zip"
INNER_ARCHIVE = "student.zip"
ATTRIBUTE_NOTES = "student.txt"
TIMEOUT_SECONDS = 60
#: <repo>/data/raw, resolved from this file so the script works from any directory.
DEFAULT_RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"


class DatasetIntegrityError(RuntimeError):
    """Raised when a file does not match its pinned checksum."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def expected_files() -> dict[str, str]:
    """Map of required CSV filename -> pinned SHA-256."""
    return {info.filename: info.sha256 for info in COHORTS.values()}


def verify(raw_dir: Path) -> list[str]:
    """Return a list of problems with the files in ``raw_dir`` (empty when valid)."""
    problems = []
    for name, digest in expected_files().items():
        path = raw_dir / name
        if not path.is_file():
            problems.append(f"{name}: missing")
        elif (actual := sha256(path.read_bytes())) != digest:
            problems.append(f"{name}: checksum mismatch (expected {digest}, got {actual})")
    return problems


def fetch_archive(url: str = ARCHIVE_URL) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "student-academic-analytics"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read()


def extract(archive: bytes) -> dict[str, bytes]:
    """Extract the CSVs and attribute notes from the nested official archive."""
    with zipfile.ZipFile(io.BytesIO(archive)) as outer:
        inner_bytes = outer.read(INNER_ARCHIVE)
    wanted = {*expected_files(), ATTRIBUTE_NOTES}
    with zipfile.ZipFile(io.BytesIO(inner_bytes)) as inner:
        found = {Path(n).name: n for n in inner.namelist()}
        missing = wanted - found.keys()
        if missing:
            raise DatasetIntegrityError(f"Archive is missing: {', '.join(sorted(missing))}")
        return {name: inner.read(found[name]) for name in wanted}


def download(raw_dir: Path, *, force: bool = False, fetch=fetch_archive) -> list[str]:
    """Ensure verified files exist in ``raw_dir``. Returns the names written."""
    if not force and not verify(raw_dir):
        return []

    files = extract(fetch())
    checksums = expected_files()
    for name, digest in checksums.items():
        if (actual := sha256(files[name])) != digest:
            raise DatasetIntegrityError(
                f"{name} from {ARCHIVE_URL} does not match the pinned checksum "
                f"(expected {digest}, got {actual}). The upstream file may have changed; "
                "review it before updating the checksum in analytics/data/cohorts.py."
            )

    raw_dir.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (raw_dir / name).write_bytes(content)
    return sorted(files)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="re-download even if valid")
    parser.add_argument("--verify", action="store_true", help="only verify existing files")
    parser.add_argument(
        "--raw-dir", type=Path, default=DEFAULT_RAW_DIR, help=f"target (default {DEFAULT_RAW_DIR})"
    )
    args = parser.parse_args(argv)

    raw_dir = args.raw_dir
    if args.verify:
        problems = verify(raw_dir)
        for problem in problems:
            print(f"✗ {problem}")
        if not problems:
            print(f"✓ Dataset verified in {raw_dir}")
        return 1 if problems else 0

    try:
        written = download(raw_dir, force=args.force)
    except (OSError, zipfile.BadZipFile, DatasetIntegrityError) as error:
        print(f"✗ Download failed: {error}", file=sys.stderr)
        return 1

    if written:
        print(f"✓ Downloaded from {ARCHIVE_URL}")
        for name in written:
            print(f"  {raw_dir / name}")
    else:
        print(f"✓ Dataset already present and verified in {raw_dir}")
    print(f"Source: {DATASET_PAGE} (CC BY 4.0, Cortez & Silva, 2008)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
