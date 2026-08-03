from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pqc_quantum_research_agent.redaction import redact_text


TEXT_SUFFIXES = {".csv", ".html", ".json", ".md", ".txt", ".yaml", ".yml"}


def sanitize_paths(paths: list[Path], *, write: bool) -> list[Path]:
    changed: list[Path] = []
    for root in paths:
        candidates = [root] if root.is_file() else root.rglob("*")
        for path in candidates:
            if not path.is_file() or path.suffix.casefold() not in TEXT_SUFFIXES:
                continue
            original = path.read_text(encoding="utf-8")
            sanitized = redact_text(original)
            if sanitized == original:
                continue
            changed.append(path)
            if write:
                path.write_text(sanitized, encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect or remove credentials accidentally embedded in generated reports."
    )
    parser.add_argument("paths", nargs="*", type=Path, default=[Path("reports")])
    parser.add_argument(
        "--write",
        action="store_true",
        help="Rewrite affected files. Without this flag the command is a leak check.",
    )
    args = parser.parse_args()
    changed = sanitize_paths(args.paths, write=args.write)
    for path in changed:
        print(path)
    if changed and not args.write:
        print(f"Credential-like values found in {len(changed)} file(s).")
        return 1
    if changed:
        print(f"Sanitized {len(changed)} file(s).")
    else:
        print("No credential-like values found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
