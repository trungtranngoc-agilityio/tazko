import os
import stat
from pathlib import Path

import pytest

from tazko.core.config import ConfigError, load_settings
from tazko.core.secret import load_secret

SECRET = "s" * 40


def test_configured_secret_is_used(tmp_path: Path) -> None:
    settings = load_settings(env="development", data_dir=tmp_path, secret=SECRET)
    assert load_secret(settings) == SECRET.encode()
    assert not (tmp_path / "secret").exists()


def test_empty_secret_creates_a_random_file_once(tmp_path: Path) -> None:
    settings = load_settings(env="development", data_dir=tmp_path / "data")
    first = load_secret(settings)
    assert len(first) >= 32
    assert load_secret(settings) == first


def test_two_data_folders_get_different_secrets(tmp_path: Path) -> None:
    a = load_secret(load_settings(env="development", data_dir=tmp_path / "a"))
    b = load_secret(load_settings(env="development", data_dir=tmp_path / "b"))
    assert a != b


@pytest.mark.skipif(os.name == "nt", reason="POSIX file modes")
def test_secret_file_is_private(tmp_path: Path) -> None:
    load_secret(load_settings(env="development", data_dir=tmp_path))
    mode = stat.S_IMODE((tmp_path / "secret").stat().st_mode)
    assert mode == 0o600


@pytest.mark.skipif(os.name == "nt", reason="POSIX file modes")
def test_secret_file_readable_by_others_is_refused(tmp_path: Path) -> None:
    (tmp_path / "secret").write_text("x" * 64)
    (tmp_path / "secret").chmod(0o644)
    with pytest.raises(ConfigError, match="600"):
        load_secret(load_settings(env="development", data_dir=tmp_path))


def test_creating_the_secret_leaves_no_temporary_file(tmp_path: Path) -> None:
    load_secret(load_settings(env="development", data_dir=tmp_path))
    assert sorted(p.name for p in tmp_path.iterdir()) == ["secret"]
