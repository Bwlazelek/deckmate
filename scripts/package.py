#!/usr/bin/env python3
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_NAME = "DeckMate"
VERSION = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]
BUILD = ROOT / "build"
STAGING = BUILD / PLUGIN_NAME
ARCHIVE = BUILD / f"deckmate-v{VERSION}.zip"

FILES = [
    "LICENSE",
    "README.md",
    "package.json",
    "plugin.json",
    "main.py",
    "deckmate_core.py",
    "dist/index.js",
]


def main():
    if BUILD.exists():
        shutil.rmtree(BUILD)
    STAGING.mkdir(parents=True)

    for relative in FILES:
        source = ROOT / relative
        if not source.exists():
            raise SystemExit(f"Missing required build file: {relative}")
        destination = STAGING / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(STAGING.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(BUILD))

    print(ARCHIVE)
    print(f"Packaged {len(FILES)} files under {PLUGIN_NAME}/")


if __name__ == "__main__":
    main()
