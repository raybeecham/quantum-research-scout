"""Publish only the exact public files emitted by the dashboard build."""

import hashlib
import json
import shutil
from pathlib import Path, PurePosixPath

MANIFEST = ".publication-manifest.json"


def _public_file(root, name):
    if not isinstance(name, str) or not name or any(c in name for c in ("\\", ":")):
        raise ValueError("Invalid publication file path")
    relative = PurePosixPath(name)
    if relative.is_absolute() or any(part in {".", ".."} for part in name.split("/")):
        raise ValueError("Invalid publication file path")
    path = (root / name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"Missing or unsafe publication file: {name}")
    return path


def write_publication_manifest(output, files, build_id):
    root = Path(output).resolve()
    entries = {
        name: hashlib.sha256(_public_file(root, name).read_bytes()).hexdigest()
        for name in sorted(set(files))
    }
    (root / MANIFEST).write_text(
        json.dumps({"version": 1, "build_id": build_id, "files": entries}, indent=2) + "\n",
        encoding="utf-8",
    )


def package_publication(site, destination):
    """Verify all files before copying to a new, non-overwriting destination."""
    root, output = Path(site).resolve(), Path(destination).resolve()
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    entries = manifest.get("files")
    if manifest.get("version") != 1 or not isinstance(entries, dict) or not entries:
        raise ValueError("Invalid publication manifest")
    if output.exists() or output == root or output in root.parents or output.is_relative_to(root):
        raise ValueError("Publication destination must be a new directory outside the preview")
    verified = []
    for name, expected in entries.items():
        source = _public_file(root, name)
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Publication file changed after build: {name}")
        verified.append((name, source))
    output.mkdir(parents=True)
    for name, source in verified:
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return {"build_id": manifest["build_id"], "files": len(verified), "output": str(output)}
