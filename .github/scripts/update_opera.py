#!/usr/bin/env python3
"""Update the Opera installer that OpenWin's Opera edition ships.

Opera's offline installer is larger than GitHub's 100 MiB file limit, so the
repository keeps only its version, URL and SHA-256 in Opera.json, and the
release job downloads it when it builds the Opera edition.

By default, this looks for the newest version in Opera's download archive,
which only has stable releases, downloads its offline installer, checks it
against the SHA-256 Opera publishes next to it and that it's signed by Opera
Norway AS, and updates Opera.json. With --check, it only reports whether
there's a version to pin. With --download, it downloads the pinned installer
instead and checks that it's still the same file.

Verifying the installer needs osslsigncode.
"""

import argparse
import hashlib
import http.client
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

ARCHIVE_URL = "https://get.geo.opera.com/pub/opera/desktop/"
# Offline, and installs for all users with /allusers=1.
SETUP_NAME = "Opera_Setup_x64.exe"
# The organization and common name of the certificate Opera signs Opera with.
SIGNER = "Opera Norway AS"

REPO_ROOT = Path(__file__).resolve().parents[2]
PIN = Path("Opera", "$OEM$", "$$", "Setup", "Files", "Opera.json")

VERSION_PATTERN = re.compile(r"\d+\.\d+\.\d+\.\d+")


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


def exists(url):
    try:
        open_url(urllib.request.Request(url, method="HEAD")).close()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise
    return True


def installer_url(version):
    return f"{ARCHIVE_URL}{version}/win/Opera_{version}_Setup_x64.exe"


def latest_version():
    listing = fetch(ARCHIVE_URL).decode()
    versions = re.findall(r'href="(\d+\.\d+\.\d+\.\d+)/"', listing)
    if not versions:
        raise RuntimeError(f"No Opera versions found in {ARCHIVE_URL}")
    # The listing is sorted as text, and also gets fixes for older versions.
    return max(versions, key=parse_version)


def download(url, dest):
    """Download url to dest and return its SHA-256."""
    for attempt in range(4):
        sha256 = hashlib.sha256()
        size = 0
        try:
            with open_url(url) as response, open(dest, "wb") as f:
                length = int(response.headers.get("Content-Length", -1))
                while chunk := response.read(1024 * 1024):
                    sha256.update(chunk)
                    f.write(chunk)
                    size += len(chunk)
            # A dropped connection can end the download early without an error.
            if length < 0 or size == length:
                return sha256.hexdigest()
            error = f"got {size} of {length} bytes"
        except urllib.error.HTTPError:
            raise
        except (OSError, http.client.HTTPException) as e:
            error = e
        if attempt == 3:
            raise RuntimeError(f"Couldn't download {url}: {error}")
        delay = 2 ** (attempt + 1)
        print(f"  {url}: {error}, retrying in {delay}s", file=sys.stderr)
        time.sleep(delay)


def verify_signature(setup):
    result = subprocess.run(["osslsigncode", "verify", "-in", setup], capture_output=True, text=True)
    output = result.stdout + result.stderr
    # The first subject after "Signer's certificate:" is the signing certificate's.
    signer = re.search(r"Signer's certificate:.*?Subject: *([^\n]+)", output, re.DOTALL)
    if result.returncode or "Signature verification: ok" not in output or not signer:
        raise RuntimeError(f"{setup.name} doesn't have a valid signature.\n{output}")
    subject = signer.group(1).strip()
    # osslsigncode 2.13 prints the subject as "CN=Opera Norway AS,O=Opera Norway AS,...",
    # and older versions as ".../O=Opera Norway AS/CN=Opera Norway AS".
    fields = dict(re.findall(r"(?:^|[/,]) *(\w+)=([^/,]*)", subject))
    if fields.get("O") != SIGNER or fields.get("CN") != SIGNER:
        raise RuntimeError(f"{setup.name} is signed by {subject}, not Opera Norway AS.")


def parse_version(version):
    if not VERSION_PATTERN.fullmatch(version):
        raise RuntimeError(f"Unexpected Opera version: {version!r}")
    return tuple(int(part) for part in version.split("."))


def write_outputs(**outputs):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            for key, value in outputs.items():
                f.write(f"{key}={value}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="only report whether there's a version to pin")
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
        print(f"Downloading Opera {pin['version']} from {pin['url']}")
        try:
            sha256 = download(pin["url"], args.download / SETUP_NAME)
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            raise RuntimeError(
                f"Opera {pin['version']} was withdrawn from {ARCHIVE_URL}: run the workflow"
                " again to pin the current version."
            )
        if sha256 != pin["sha256"]:
            raise RuntimeError(f"{pin['url']} isn't the pinned Opera {pin['version']} anymore.")
        return

    old_version = pin["version"] if pin else None
    version = latest_version()
    if old_version and parse_version(version) <= parse_version(old_version):
        # Opera has withdrawn a release before. Never go back to an older
        # version, unless the pinned one can't be downloaded anymore.
        if version == old_version or exists(pin["url"]):
            print(f"Opera {old_version} is up to date (latest release: {version}).")
            write_outputs(changed="false")
            return
        print(f"Opera {old_version} was withdrawn, so going back to {version}.")
    if args.check:
        print(f"Opera {version} can be pinned (pinned: {old_version}).")
        write_outputs(changed="true")
        return

    url = installer_url(version)
    try:
        checksum = fetch(f"{url}.sha256sum").decode().strip()
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        print(f"Opera {version} isn't fully published yet.")
        return
    # The file holds only the SHA-256 in hex.
    if not re.fullmatch(r"[0-9a-f]{64}", checksum):
        raise RuntimeError(f"Unexpected checksum for Opera {version}: {checksum!r}")

    with tempfile.TemporaryDirectory() as staging:
        setup = Path(staging) / SETUP_NAME
        sha256 = download(url, setup)
        if sha256 != checksum:
            raise RuntimeError(f"{url} doesn't match the SHA-256 Opera publishes for it.")
        verify_signature(setup)

    print(f"Updating Opera {old_version} -> {version}")
    pin = {"version": version, "url": url, "sha256": sha256}
    pin_path.parent.mkdir(parents=True, exist_ok=True)
    pin_path.write_text(json.dumps(pin, indent=2) + "\n")
    write_outputs(commit=f"Update Opera to {version}")


if __name__ == "__main__":
    main()
