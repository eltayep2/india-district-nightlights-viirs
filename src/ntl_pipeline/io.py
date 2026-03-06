from __future__ import annotations

import time
import zipfile
from pathlib import Path

import requests
from rich import print as rprint


def download_file(url: str, dest: Path, chunk: int = 1 << 20, retries: int = 3) -> Path:
    """Download a file with automatic retry on failure."""
    dest.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, retries + 1):
        try:
            with requests.get(url, stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for part in r.iter_content(chunk_size=chunk):
                        if part:
                            f.write(part)
            return dest
        except (requests.RequestException, IOError) as e:
            if attempt == retries:
                raise
            rprint(f"[yellow]Download attempt {attempt}/{retries} failed: {e}. Retrying in 5s...[/yellow]")
            time.sleep(5)

    return dest


def unzip_to_bytes(zip_path: Path) -> zipfile.ZipFile:
    # Caller must close
    return zipfile.ZipFile(zip_path, "r")


def unzip_member(zip_path: Path, member: str, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        with z.open(member) as src, open(out_path, "wb") as dst:
            dst.write(src.read())
    return out_path
