from pathlib import Path

import pytest

from app.ingestion.package_validator import ensure_safe_relative_path


def test_rejects_path_traversal() -> None:
    with pytest.raises(ValueError):
        ensure_safe_relative_path("../escape")


def test_rejects_absolute_path() -> None:
    with pytest.raises(ValueError):
        ensure_safe_relative_path(str(Path("/tmp/escape")))

