#!/usr/bin/env python3
"""Update the Google Chrome installer that OpenWin's Chrome edition ships.

Chrome's enterprise MSI is larger than GitHub's 100 MiB file limit, so the
repository keeps only its version, URL and SHA-256 in Chrome.json, and the
release job downloads it when it builds the Chrome edition.

Google publishes only the latest MSI, always at the same URL, and no checksums.
So by default, this checks whether the MSI's ETag changed since the last check
(recorded in .github/chrome-msi.etag), and if it did, downloads the MSI, checks
that it's signed by Google LLC, reads its Chrome version and updates
Chrome.json. With --check, it only reports whether the ETag changed. With
--download, it downloads the pinned MSI instead and checks that it's still the
same file.

Verifying and reading the MSI needs osslsigncode and msiinfo (from msitools).
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

# Offline, installs Chrome for all users, and includes Google's updater.
URL = "https://dl.google.com/dl/chrome/install/googlechromestandaloneenterprise64.msi"
SETUP_NAME = "googlechromestandaloneenterprise64.msi"
# The end of the subject of the certificate Google signs Chrome with.
SIGNER = "/O=Google LLC/CN=Google LLC"

REPO_ROOT = Path(__file__).resolve().parents[2]
PIN = Path("Chrome", "$OEM$", "$$", "Setup", "Files", "Chrome.json")
# The ETag of the MSI last downloaded, kept out of Chrome/ so that recording a
# new one never publishes a release.
ETAG = Path(".github", "chrome-msi.etag")

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


def fetch_etag(url):
    with open_url(urllib.request.Request(url, method="HEAD")) as response:
        etag = response.headers.get("ETag")
    if not etag:
        raise RuntimeError(f"{url} has no ETag")
    return etag


def download(url, dest):
    """Download url to dest and return its SHA-256 and ETag."""
    for attempt in range(4):
        sha256 = hashlib.sha256()
        size = 0
        try:
            with open_url(url) as response, open(dest, "wb") as f:
                etag = response.headers.get("ETag")
                length = int(response.headers.get("Content-Length", -1))
                while chunk := response.read(1024 * 1024):
                    sha256.update(chunk)
                    f.write(chunk)
                    size += len(chunk)
            # A dropped connection can end the download early without an error.
            if length < 0 or size == length:
                return sha256.hexdigest(), etag
            error = f"got {size} of {length} bytes"
        except (OSError, http.client.HTTPException) as e:
            error = e
        if attempt == 3:
            raise RuntimeError(f"Couldn't download {url}: {error}")
        delay = 2 ** (attempt + 1)
        print(f"  {url}: {error}, retrying in {delay}s", file=sys.stderr)
        time.sleep(delay)


def verify_signature(msi):
    result = subprocess.run(["osslsigncode", "verify", "-in", msi], capture_output=True, text=True)
    output = result.stdout + result.stderr
    # The first subject after "Signer's certificate:" is the signing certificate's.
    signer = re.search(r"Signer's certificate:.*?Subject: *([^\n]+)", output, re.DOTALL)
    if result.returncode or "Signature verification: ok" not in output or not signer:
        raise RuntimeError(f"{msi.name} doesn't have a valid signature.\n{output}")
    subject = signer.group(1).strip()
    if not subject.endswith(SIGNER):
        raise RuntimeError(f"{msi.name} is signed by {subject}, not Google LLC.")


def read_version(msi):
    result = subprocess.run(["msiinfo", "export", msi, "Property"], capture_output=True, text=True, check=True)
    match = re.search(r"^ProductVersion\t(\S+)$", result.stdout, re.MULTILINE)
    if not match or not VERSION_PATTERN.fullmatch(match.group(1)):
        raise RuntimeError(f"Can't read the Chrome version of {msi.name}:\n{result.stdout}")
    return match.group(1)


def parse_version(version):
    return tuple(int(part) for part in version.split("."))


def write_outputs(**outputs):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            for key, value in outputs.items():
                f.write(f"{key}={value}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="only report whether the MSI changed")
    parser.add_argument(
        "--download", type=Path, metavar="DIR", help="download the pinned MSI into DIR instead"
    )
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    args = parser.parse_args()

    pin_path = args.root / PIN
    pin = json.loads(pin_path.read_text()) if pin_path.exists() else None
    etag_path = args.root / ETAG
    old_etag = etag_path.read_text().strip() if etag_path.exists() else None

    if args.download:
        if not pin:
            raise RuntimeError(f"{pin_path} not found")
        print(f"Downloading Chrome {pin['version']} from {pin['url']}")
        sha256, _ = download(pin["url"], args.download / SETUP_NAME)
        if sha256 != pin["sha256"]:
            raise RuntimeError(
                f"{pin['url']} isn't the pinned Chrome {pin['version']} anymore. Google has"
                " probably published a newer Chrome: run the workflow again to pin it."
            )
        return

    old_version = pin["version"] if pin else None
    if pin and fetch_etag(URL) == old_etag:
        print(f"Chrome {old_version} is up to date.")
        write_outputs(changed="false")
        return
    if args.check:
        print(f"The Chrome MSI changed since Chrome {old_version} was pinned." if pin else "No Chrome is pinned yet.")
        write_outputs(changed="true")
        return

    # Download and check the MSI, and take its ETag from the same response, as
    # Google's servers don't all switch to a new MSI at the same moment.
    with tempfile.TemporaryDirectory() as staging:
        msi = Path(staging) / SETUP_NAME
        sha256, etag = download(URL, msi)
        verify_signature(msi)
        version = read_version(msi)
    if not etag:
        raise RuntimeError(f"{URL} has no ETag")

    if pin and sha256 == pin["sha256"]:
        if etag == old_etag:
            print(f"{URL} still served the pinned Chrome {old_version}.")
            return
        print(f"Chrome {old_version} is up to date, but its MSI has a new ETag.")
        commit = "Record the new ETag of Chrome's MSI"
    elif old_version and parse_version(version) < parse_version(old_version):
        # A server that hasn't caught up yet can still serve an older MSI.
        print(f"{URL} served Chrome {version}, older than the pinned {old_version}.")
        return
    else:
        print(f"Updating Chrome {old_version} -> {version}")
        pin = {"version": version, "url": URL, "sha256": sha256}
        pin_path.parent.mkdir(parents=True, exist_ok=True)
        pin_path.write_text(json.dumps(pin, indent=2) + "\n")
        commit = f"Update Chrome to {version}"

    etag_path.write_text(etag + "\n")
    write_outputs(commit=commit)


if __name__ == "__main__":
    main()
