from pathlib import Path

import pytest

from cryptoswarms.immutable_artifacts import write_immutable_json, write_immutable_text


def test_write_immutable_text_blocks_overwrite(tmp_path: Path):
    path = tmp_path / "a.txt"
    write_immutable_text(path, "one\n")
    with pytest.raises(FileExistsError):
        write_immutable_text(path, "two\n")


def test_write_immutable_json_allows_idempotent_rewrite(tmp_path: Path):
    path = tmp_path / "a.json"
    payload = {"x": 1}
    write_immutable_json(path, payload)
    write_immutable_json(path, payload)
    assert path.exists()
