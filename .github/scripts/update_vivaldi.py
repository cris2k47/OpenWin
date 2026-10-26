#!/usr/bin/env python3
"""Update the Vivaldi installer that OpenWin's Vivaldi edition ships.

Vivaldi's offline installer is larger than GitHub's 100 MiB file limit, so the
repository keeps only its version, URL and SHA-256 in Vivaldi.json, and the
release job downloads it when it builds the Vivaldi edition.

Vivaldi publishes no checksums. By default, this looks up the newest stable
Vivaldi in the update feed Vivaldi's own updater reads, downloads its offline
installer, checks that it's signed by Vivaldi Technologies AS, and updates
Vivaldi.json. With --check, it only reports whether there's a newer version.
With --download, it downloads the pinned installer instead and checks that it's
still the same file.

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
import xml.etree.ElementTree as ET
from pathlib import Path

# The stable channel's feed. The one under /win/ is for snapshots.
APPCAST_URL = "https://update.vivaldi.com/update/1.0/public/appcast.x64.xml"
SPARKLE = "{http://www.andymatuschak.org/xml-namespaces/sparkle}"
# Offline, and installs for all users with --system-level.
SETUP_NAME = "Vivaldi.x64.exe"
# The organization and common name of the certificate Vivaldi signs Vivaldi with.
SIGNER = "Vivaldi Technologies AS"

REPO_ROOT = Path(__file__).resolve().parents[2]
PIN = Path("Vivaldi", "$OEM$", "$$", "Setup", "Files", "Vivaldi.json")

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


def latest_release():
    """Return the version and offline installer URL of the newest stable Vivaldi."""
    item = ET.fromstring(fetch(APPCAST_URL)).find("channel/item")
    # The item's own enclosure is the full installer; the deltas are in a child.
    enclosure = item.find("enclosure") if item is not None else None
    if enclosure is None:
        raise RuntimeError(f"No installer found in {APPCAST_URL}")
    version, url = enclosure.get(f"{SPARKLE}version", ""), enclosure.get("url", "")
    parse_version(version)
    if not re.fullmatch(rf"https://downloads\.vivaldi\.com/stable[\w-]*/Vivaldi\.{re.escape(version)}\.x64\.exe", url):
        raise RuntimeError(f"Unexpected installer URL for Vivaldi {version}: {url!r}")
    return version, url


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
    # osslsigncode 2.13 prints the subject as "CN=Vivaldi Technologies AS,O=...,...",
    # and older versions as ".../O=Vivaldi Technologies AS/CN=Vivaldi Technologies AS".
    fields = dict(re.findall(r"(?:^|[/,]) *(\w+)=([^/,]*)", subject))
    if fields.get("O") != SIGNER or fields.get("CN") != SIGNER:
        raise RuntimeError(f"{setup.name} is signed by {subject}, not Vivaldi Technologies AS.")


def parse_version(version):
    if not VERSION_PATTERN.fullmatch(version):
        raise RuntimeError(f"Unexpected Vivaldi version: {version!r}")
    return tuple(int(part) for part in version.split("."))


def write_outputs(**outputs):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            for key, value in outputs.items():
                f.write(f"{key}={value}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="only report whether there's a newer version")
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
        print(f"Downloading Vivaldi {pin['version']} from {pin['url']}")
        sha256 = download(pin["url"], args.download / SETUP_NAME)
        if sha256 != pin["sha256"]:
            raise RuntimeError(f"{pin['url']} isn't the pinned Vivaldi {pin['version']} anymore.")
        return

    old_version = pin["version"] if pin else None
    version, url = latest_release()
    if old_version and parse_version(version) <= parse_version(old_version):
        print(f"Vivaldi {old_version} is up to date (latest release: {version}).")
        write_outputs(changed="false")
        return
    if args.check:
        print(f"Vivaldi {version} is out (pinned: {old_version}).")
        write_outputs(changed="true")
        return

    with tempfile.TemporaryDirectory() as staging:
        setup = Path(staging) / SETUP_NAME
        sha256 = download(url, setup)
        verify_signature(setup)

    print(f"Updating Vivaldi {old_version} -> {version}")
    pin = {"version": version, "url": url, "sha256": sha256}
    pin_path.parent.mkdir(parents=True, exist_ok=True)
    pin_path.write_text(json.dumps(pin, indent=2) + "\n")
    write_outputs(commit=f"Update Vivaldi to {version}")


if __name__ == "__main__":
    main()
