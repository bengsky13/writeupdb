from __future__ import annotations

import json
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PackageValidationResult:
    manifest: dict
    root: Path


def ensure_safe_relative_path(path: str) -> None:
    path_obj = Path(path)
    if path_obj.is_absolute() or ".." in path_obj.parts:
        raise ValueError(f"unsafe path: {path}")


def validate_package(package_dir: Path) -> PackageValidationResult:
    manifest_path = package_dir / "manifest.json"
    if not manifest_path.exists():
        raise ValueError("manifest.json is required")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ensure_safe_relative_path(manifest["content_file"])
    for attachment in manifest.get("attachments", []):
        ensure_safe_relative_path(attachment["path"])
    for path in package_dir.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"symlink rejected: {path}")
    return PackageValidationResult(manifest=manifest, root=package_dir)


def extract_zip_package(zip_path: Path, destination: Path, size_limit_bytes: int) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    total = 0
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            ensure_safe_relative_path(member.filename)
            total += member.file_size
            if total > size_limit_bytes:
                raise ValueError("archive extraction limit exceeded")
        archive.extractall(destination)
    return destination


def move_package(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    return Path(shutil.move(str(source), str(destination)))

