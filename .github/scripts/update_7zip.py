#!/usr/bin/env python3
"""Update the offline 7-Zip installer.

Downloads the latest 7-Zip release from its official GitHub repository,
verifies it against the SHA-256 digest GitHub publishes for the file,
replaces the installer in Setup\\Files, and points autounattend.xml at it.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

RELEASES_URL = "https://api.github.com/repos/ip7z/7zip/releases"

REPO_ROOT = Path(__file__).resolve().parents[2]
FILES_DIR = Path("$OEM$", "$$", "Setup", "Files")
UNATTEND = Path("autounattend.xml")

TAG_PATTERN = re.compile(r"(\d+)\.(\d\d)")
# 7-Zip 26.04 is 7z2604-x64.exe.
SETUP_PATTERN = re.compile(r"7z(\d+)(\d\d)-x64\.exe")


def open_url(request):
    url = getattr(request, "full_url", request)
    for attempt in range(4):
        try:
            return urllib.request.urlopen(request, timeout=60)
        except OSError as e:
            if attempt == 3:
                raise
            delay = 2 ** (attempt + 1)
            print(f"  {url}: {e}, retrying in {delay}s", file=sys.stderr)
            time.sleep(delay)


def fetch_release(tag):
    url = f"{RELEASES_URL}/tags/{tag}" if tag else f"{RELEASES_URL}/latest"
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if token := os.environ.get("GITHUB_TOKEN"):
        # Unredirected, so the token is never sent to another host.
        request.add_unredirected_header("Authorization", f"Bearer {token}")
    with open_url(request) as response:
        return json.loads(response.read())


def download(url, dest, expected_sha256):
    sha256 = hashlib.sha256()
    with open_url(url) as response, open(dest, "wb") as f:
        while chunk := response.read(1024 * 1024):
            sha256.update(chunk)
            f.write(chunk)
    if sha256.hexdigest() != expected_sha256:
        raise RuntimeError(f"SHA-256 mismatch for {url}")


def write_outputs(**outputs):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            for key, value in outputs.items():
                f.write(f"{key}={value}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", help="7-Zip release to install, e.g. 26.04 (default: latest release)")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    args = parser.parse_args()

    files_dir = args.root / FILES_DIR
    unattend = args.root / UNATTEND

    old_setups = [p for p in files_dir.iterdir() if SETUP_PATTERN.fullmatch(p.name)]
    if len(old_setups) > 1:
        raise RuntimeError(f"More than one 7-Zip installer in {files_dir}")
    old_match = SETUP_PATTERN.fullmatch(old_setups[0].name) if old_setups else None
    old_version = f"{old_match.group(1)}.{old_match.group(2)}" if old_match else None

    release = fetch_release(args.tag)
    version = release["tag_name"]
    match = TAG_PATTERN.fullmatch(version)
    if not match:
        raise RuntimeError(f"Unexpected 7-Zip version: {version!r}")
    if old_match and (int(match.group(1)), int(match.group(2))) <= (
        int(old_match.group(1)),
        int(old_match.group(2)),
    ):
        print(f"7-Zip {old_version} is up to date (latest release: {version}).")
        write_outputs(updated="false", version=old_version)
        return

    print(f"Updating 7-Zip {old_version} -> {version}")

    # Read autounattend.xml first so a bad file fails before anything changes.
    with open(unattend, newline="") as f:
        xml = f.read()
    setup_name = f"7z{match.group(1)}{match.group(2)}-x64.exe"
    xml, count = SETUP_PATTERN.subn(setup_name, xml)
    if not count:
        raise RuntimeError(f"No 7-Zip installer referenced in {unattend}")

    asset = next((a for a in release["assets"] if a["name"] == setup_name), None)
    if not asset:
        raise RuntimeError(f"{setup_name} not found in 7-Zip {version} release")
    digest = asset.get("digest") or ""
    if not digest.startswith("sha256:"):
        raise RuntimeError(f"No SHA-256 digest published for {setup_name}")

    with tempfile.TemporaryDirectory() as staging:
        new_setup = Path(staging) / setup_name
        print(f"Downloading {asset['browser_download_url']}")
        download(asset["browser_download_url"], new_setup, digest.removeprefix("sha256:"))

        for old_setup in old_setups:
            old_setup.unlink()
        shutil.move(new_setup, files_dir / setup_name)

    with open(unattend, "w", newline="") as f:
        f.write(xml)

    print(f"Updated 7-Zip to {version}")
    write_outputs(updated="true", version=version)


if __name__ == "__main__":
    main()
