import io
import zipfile

import pytest

from analytics.data import download as dl


def nested_archive(files: dict[str, bytes]) -> bytes:
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as z:
        for name, content in files.items():
            z.writestr(name, content)
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w") as z:
        z.writestr("student.zip", inner.getvalue())
    return outer.getvalue()


@pytest.fixture
def fake_files(monkeypatch):
    files = {"student-mat.csv": b"math", "student-por.csv": b"por", "student.txt": b"notes"}
    pinned = {n: dl.sha256(files[n]) for n in ("student-mat.csv", "student-por.csv")}
    monkeypatch.setattr(dl, "expected_files", lambda: pinned)
    return files


def test_download_extracts_nested_archive_and_verifies(tmp_path, fake_files):
    written = dl.download(tmp_path, fetch=lambda: nested_archive(fake_files))

    assert written == sorted(fake_files)
    assert (tmp_path / "student-mat.csv").read_bytes() == b"math"
    assert dl.verify(tmp_path) == []
    assert not list(tmp_path.glob("*.zip"))


def test_download_is_skipped_when_files_are_already_valid(tmp_path, fake_files):
    dl.download(tmp_path, fetch=lambda: nested_archive(fake_files))

    def fail():
        raise AssertionError("should not fetch")

    assert dl.download(tmp_path, fetch=fail) == []


def test_checksum_mismatch_is_rejected_and_nothing_written(tmp_path, fake_files):
    tampered = {**fake_files, "student-por.csv": b"changed"}

    with pytest.raises(dl.DatasetIntegrityError, match="student-por.csv"):
        dl.download(tmp_path, fetch=lambda: nested_archive(tampered))
    assert not (tmp_path / "student-mat.csv").exists()


def test_verify_reports_missing_and_corrupted_files(tmp_path, fake_files):
    (tmp_path / "student-mat.csv").write_bytes(b"corrupted")

    problems = dl.verify(tmp_path)
    assert any("student-mat.csv: checksum mismatch" in p for p in problems)
    assert any("student-por.csv: missing" in p for p in problems)


def test_archive_missing_expected_file_is_rejected(tmp_path, fake_files):
    partial = {k: v for k, v in fake_files.items() if k != "student-por.csv"}
    with pytest.raises(dl.DatasetIntegrityError, match="missing"):
        dl.download(tmp_path, fetch=lambda: nested_archive(partial))
