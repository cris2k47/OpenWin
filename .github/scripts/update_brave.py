#!/usr/bin/env python3
"""Update the Brave installer that OpenWin ships.

Brave's offline installer is larger than GitHub's 100 MiB file limit, so the
repository keeps only its version, URL and SHA-256 in Setup\\Files\\Brave.json,
and the release job downloads it when it builds OpenWin.zip and
autounattend.iso.

By default, checks for a new Brave Release-channel version, verifies the
installer's SHA-256 against Brave's GPG-signed checksum file, and updates
Brave.json. With --download, downloads the installer pinned in Brave.json
instead and verifies it.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

VERSION_URL = "https://versions.brave.com/latest/release-windows-x64.version"
RELEASES_URL = "https://api.github.com/repos/brave/brave-browser/releases"
KEYS_URL = "https://brave-browser-downloads.s3.brave.com/keys/github-checksums-release.asc"
# Offline, installs for all users when run as SYSTEM, and includes Brave's
# updater. The "Silent" variant installs for the current user only.
SETUP_NAME = "BraveBrowserStandaloneSetup.exe"

REPO_ROOT = Path(__file__).resolve().parents[2]
PIN = Path("$OEM$", "$$", "Setup", "Files", "Brave.json")
# Brave's "GitHub Checksums - Release Channel" keys (https://brave.com/signing-keys/).
# Beta and Nightly checksums are signed with other keys.
KEYRING = Path(".github", "brave-checksums-release.asc")

VERSION_PATTERN = re.compile(r"\d+\.\d+\.\d+")


def open_url(request):
    url = getattr(request, "full_url", request)
    for attempt in range(4):
        try:
            return urllib.request.urlopen(request, timeout=60)
        except OSError as e:
            # Client errors such as 404 don't go away by retrying.
            permanent = isinstance(e, urllib.error.HTTPError) and e.code < 500 and e.code != 429
            if permanent or attempt == 3:
                raise
            delay = 2 ** (attempt + 1)
            print(f"  {url}: {e}, retrying in {delay}s", file=sys.stderr)
            time.sleep(delay)


def fetch(url):
    with open_url(url) as response:
        return response.read()


def fetch_release(version):
    """Return the GitHub release of a Brave version, or None if there isn't one yet."""
    request = urllib.request.Request(
        f"{RELEASES_URL}/tags/v{version}", headers={"Accept": "application/vnd.github+json"}
    )
    if token := os.environ.get("GITHUB_TOKEN"):
        # Unredirected, so the token is never sent to another host.
        request.add_unredirected_header("Authorization", f"Bearer {token}")
    try:
        with open_url(request) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def download(url, dest, expected_sha256):
    sha256 = hashlib.sha256()
    with open_url(url) as response, open(dest, "wb") as f:
        while chunk := response.read(1024 * 1024):
            sha256.update(chunk)
            f.write(chunk)
    if sha256.hexdigest() != expected_sha256:
        raise RuntimeError(f"SHA-256 mismatch for {url}")


def verify_signature(data, signature, keyring):
    with tempfile.TemporaryDirectory() as home:
        gpg = ["gpg", "--homedir", home, "--batch", "--no-autostart"]
        subprocess.run([*gpg, "--quiet", "--import", keyring], check=True, capture_output=True)
        result = subprocess.run(
            [*gpg, "--status-fd", "1", "--verify", signature, data], capture_output=True, text=True
        )
    if result.returncode or "[GNUPG:] VALIDSIG " not in result.stdout:
        raise RuntimeError(
            f"{data.name} isn't signed with a key in {KEYRING}. If Brave added a new Release"
            f" checksum key (see https://brave.com/signing-keys/), replace {KEYRING} with"
            f" {KEYS_URL}.\n{result.stdout}{result.stderr}"
        )


def parse_version(version):
    if not VERSION_PATTERN.fullmatch(version):
        raise RuntimeError(f"Unexpected Brave version: {version!r}")
    return tuple(int(part) for part in version.split("."))


def write_outputs(**outputs):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            for key, value in outputs.items():
                f.write(f"{key}={value}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="Brave version to pin, e.g. 1.97.56 (default: latest release)")
    parser.add_argument(
        "--download", type=Path, metavar="DIR", help="download the pinned installer into DIR instead"
    )
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    args = parser.parse_args()

    pin_path = args.root / PIN
    pin = json.loads(pin_path.read_text()) if pin_path.exists() else None

    if args.download:
        if not pin:
            raise RuntimeError(f"{pin_path} not found")
        print(f"Downloading Brave {pin['version']} from {pin['url']}")
        download(pin["url"], args.download / SETUP_NAME, pin["sha256"])
        return

    old_version = pin["version"] if pin else None
    version = args.version or fetch(VERSION_URL).decode().strip()
    if old_version and parse_version(version) <= parse_version(old_version):
        print(f"Brave {old_version} is up to date (latest release: {version}).")
        write_outputs(updated="false", version=old_version)
        return

    # versions.brave.com moves to a new version a few minutes before its GitHub
    # release and signed checksum are published, so wait for those.
    release = fetch_release(version)
    assets = {a["name"]: a for a in (release or {}).get("assets", []) if a["state"] == "uploaded"}
    names = [SETUP_NAME, f"{SETUP_NAME}.sha256", f"{SETUP_NAME}.sha256.asc"]
    if not release or release["prerelease"] or not all(name in assets for name in names):
        print(f"Brave {version} isn't fully published on GitHub yet.")
        write_outputs(updated="false")
        return

    print(f"Updating Brave {old_version} -> {version}")

    with tempfile.TemporaryDirectory() as staging:
        checksum, signature = (Path(staging) / name for name in names[1:])
        for path in (checksum, signature):
            path.write_bytes(fetch(assets[path.name]["browser_download_url"]))
        verify_signature(checksum, signature, args.root / KEYRING)
        line = checksum.read_text().strip()

    # The signed line names the exact build, e.g.
    # "<sha256>  BraveBrowserStandaloneSetup_155_1_97_56.exe" for 1.97.56.
    build = rf"BraveBrowserStandaloneSetup_\d+_{version.replace('.', '_')}\.exe"
    match = re.fullmatch(rf"([0-9a-f]{{64}}) [ *]{build}", line)
    if not match:
        raise RuntimeError(f"Unexpected checksum for Brave {version}: {line!r}")
    sha256 = match.group(1)
    digest = assets[SETUP_NAME].get("digest")
    if digest and digest != f"sha256:{sha256}":
        raise RuntimeError(f"GitHub's digest of {SETUP_NAME} doesn't match Brave's signed checksum")

    pin = {"version": version, "url": assets[SETUP_NAME]["browser_download_url"], "sha256": sha256}
    pin_path.write_text(json.dumps(pin, indent=2) + "\n")

    print(f"Updated Brave to {version}")
    write_outputs(updated="true", version=version)


if __name__ == "__main__":
    main()
