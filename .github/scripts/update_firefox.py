#!/usr/bin/env python3
"""Update the offline Firefox installer and its language packs.

Downloads the latest Firefox release from archive.mozilla.org, verifies every
file against the release's SHA512SUMS, replaces the installer in Setup\\Files
and the language packs in distribution\\extensions, and points
InstallFirefox.cmd at the new installer.
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
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ARCHIVE_URL = "https://archive.mozilla.org/pub/firefox/releases"
VERSIONS_URL = "https://product-details.mozilla.org/1.0/firefox_versions.json"
PLATFORM = "win64"
# The installer ships this locale, so it doesn't need a language pack.
INSTALLER_LOCALE = "en-US"
# GitHub rejects pushes containing files larger than 100 MiB.
GITHUB_MAX_FILE_SIZE = 100 * 1024 * 1024

REPO_ROOT = Path(__file__).resolve().parents[2]
SETUP_DIR = Path("$OEM$", "$$", "Setup")
FILES_DIR = SETUP_DIR / "Files"
EXTENSIONS_DIR = FILES_DIR / "Mozilla Firefox" / "distribution" / "extensions"
INSTALL_SCRIPT = SETUP_DIR / "Scripts" / "InstallFirefox.cmd"

VERSION_PATTERN = re.compile(r"\d+(?:\.\d+)+")
SETUP_PATTERN = re.compile(r"Firefox Setup (\d+(?:\.\d+)+)\.exe")
LANGPACK_PATTERN = re.compile(rf"{PLATFORM}/xpi/([^/]+)\.xpi")


def open_url(url):
    for attempt in range(4):
        try:
            return urllib.request.urlopen(url, timeout=60)
        except OSError as e:
            if attempt == 3:
                raise
            delay = 2 ** (attempt + 1)
            print(f"  {url}: {e}, retrying in {delay}s", file=sys.stderr)
            time.sleep(delay)


def fetch(url):
    with open_url(url) as response:
        return response.read()


def download(url, dest, expected_sha512):
    sha512 = hashlib.sha512()
    with open_url(url) as response, open(dest, "wb") as f:
        while chunk := response.read(1024 * 1024):
            sha512.update(chunk)
            f.write(chunk)
    if sha512.hexdigest() != expected_sha512:
        raise RuntimeError(f"SHA-512 mismatch for {url}")


def parse_version(version):
    if not VERSION_PATTERN.fullmatch(version):
        raise RuntimeError(f"Unexpected Firefox version: {version!r}")
    return tuple(int(part) for part in version.split("."))


def latest_version():
    return json.loads(fetch(VERSIONS_URL))["LATEST_FIREFOX_VERSION"]


def current_setups(files_dir):
    return [p for p in files_dir.iterdir() if SETUP_PATTERN.fullmatch(p.name)]


def read_checksums(version):
    checksums = {}
    for line in fetch(f"{ARCHIVE_URL}/{version}/SHA512SUMS").decode().splitlines():
        match = re.fullmatch(r"([0-9a-f]{128})\s+(.+)", line)
        if match:
            checksums[match.group(2)] = match.group(1)
    return checksums


def langpack_id(xpi):
    with zipfile.ZipFile(xpi) as z:
        manifest = json.loads(z.read("manifest.json"))
    settings = manifest.get("browser_specific_settings") or manifest.get("applications")
    return settings["gecko"]["id"]


def write_outputs(**outputs):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            for key, value in outputs.items():
                f.write(f"{key}={value}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="Firefox version to install (default: latest release)")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    args = parser.parse_args()

    files_dir = args.root / FILES_DIR
    extensions_dir = args.root / EXTENSIONS_DIR
    install_script = args.root / INSTALL_SCRIPT

    old_setups = current_setups(files_dir)
    if len(old_setups) > 1:
        raise RuntimeError(f"More than one Firefox installer in {files_dir}")
    old_version = SETUP_PATTERN.fullmatch(old_setups[0].name).group(1) if old_setups else None

    version = args.version or latest_version()
    if old_version and parse_version(version) <= parse_version(old_version):
        print(f"Firefox {old_version} is up to date (latest release: {version}).")
        write_outputs(updated="false", version=old_version)
        return

    print(f"Updating Firefox {old_version} -> {version}")

    # Read the install script first so a bad script fails before anything changes.
    with open(install_script, newline="") as f:
        script = f.read()
    setup_name = f"Firefox Setup {version}.exe"
    script, count = SETUP_PATTERN.subn(setup_name, script)
    if not count:
        raise RuntimeError(f"No Firefox installer referenced in {install_script}")

    checksums = read_checksums(version)
    base_url = f"{ARCHIVE_URL}/{version}"

    with tempfile.TemporaryDirectory() as staging:
        staging = Path(staging)

        setup_key = f"{PLATFORM}/{INSTALLER_LOCALE}/{setup_name}"
        if setup_key not in checksums:
            raise RuntimeError(f"{setup_key} not found in SHA512SUMS")
        print(f"Downloading {setup_key}")
        new_setup = staging / setup_name
        download(f"{base_url}/{urllib.parse.quote(setup_key)}", new_setup, checksums[setup_key])
        if new_setup.stat().st_size >= GITHUB_MAX_FILE_SIZE:
            raise RuntimeError(f"{setup_name} is larger than GitHub's 100 MiB file limit")

        langpacks_dir = staging / "extensions"
        langpacks_dir.mkdir()
        for key in sorted(checksums):
            match = LANGPACK_PATTERN.fullmatch(key)
            if not match or match.group(1) == INSTALLER_LOCALE:
                continue
            # Firefox only installs distribution add-ons whose file name is their ID.
            addon_id = f"langpack-{match.group(1)}@firefox.mozilla.org"
            print(f"Downloading {key}")
            xpi = langpacks_dir / f"{addon_id}.xpi"
            download(f"{base_url}/{key}", xpi, checksums[key])
            if langpack_id(xpi) != addon_id:
                raise RuntimeError(f"{key} has ID {langpack_id(xpi)!r}, expected {addon_id!r}")
        if not any(langpacks_dir.iterdir()):
            raise RuntimeError("No language packs found in SHA512SUMS")

        for old_setup in old_setups:
            old_setup.unlink()
        shutil.move(new_setup, files_dir / setup_name)

        for old_xpi in extensions_dir.glob("*.xpi"):
            old_xpi.unlink()
        for xpi in langpacks_dir.iterdir():
            shutil.move(xpi, extensions_dir / xpi.name)

    with open(install_script, "w", newline="") as f:
        f.write(script)

    print(f"Updated Firefox to {version}")
    write_outputs(updated="true", version=version)


if __name__ == "__main__":
    main()
