#!/usr/bin/env python3
"""Bump versions.env to the latest stable Android SDK packages.

Reads Google's SDK repository manifest (the same one sdkmanager uses) and
picks the newest stable release of:

  * command-line tools (build number used in the download URL)
  * platform (highest API level; installs its base release, e.g. android-37.0,
    plus its newest minor SDK release, e.g. android-37.2)
  * build-tools
  * NDK (optionally restricted to ANDROID_NDK_MAJOR, e.g. to stay on an LTS)

Versions are only ever moved forward. When running inside GitHub Actions the
result is exported via $GITHUB_OUTPUT (changed=true|false, message=...).
"""

import argparse
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

REPOSITORY_URL = "https://dl.google.com/android/repository/repository2-3.xml"
VERSIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "versions.env")

KEYS = {
    "ANDROID_SDK_TOOLS_VERSION": "command-line tools",
    "ANDROID_PLATFORM_VERSION": "platform",
    "ANDROID_PLATFORM_PACKAGES": "platform packages",
    "ANDROID_BUILD_TOOLS_VERSION": "build-tools",
    "ANDROID_NDK_VERSION": "NDK",
}


def local(tag):
    return tag.rsplit("}", 1)[-1]


def child(elem, name):
    for c in elem:
        if local(c.tag) == name:
            return c
    return None


def stable_packages(root):
    """Yield (path, revision tuple, element) for stable, non-preview packages."""
    stable_channels = {
        c.get("id") for c in root if local(c.tag) == "channel" and c.text == "stable"
    }
    for pkg in root:
        if local(pkg.tag) != "remotePackage":
            continue
        channel = child(pkg, "channelRef")
        if channel is not None and channel.get("ref") not in stable_channels:
            continue
        rev = child(pkg, "revision")
        if rev is None or child(rev, "preview") is not None:
            continue
        parts = tuple(
            int(child(rev, p).text) if child(rev, p) is not None else 0
            for p in ("major", "minor", "micro")
        )
        yield pkg.get("path"), parts, pkg


def linux_archive_url(pkg):
    for archive in pkg.iter():
        if local(archive.tag) != "archive":
            continue
        host = child(archive, "host-os")
        if host is not None and host.text != "linux":
            continue
        for el in archive.iter():
            if local(el.tag) == "url":
                return el.text
    return None


def latest_versions(root, ndk_major=None):
    best = {}
    platforms = {}  # API major -> {minor: package name}

    def offer(key, sort_key, value):
        if key not in best or sort_key > best[key][0]:
            best[key] = (sort_key, value)

    for path, rev, pkg in stable_packages(root):
        if m := re.fullmatch(r"cmdline-tools;[\d.]+", path):
            url = linux_archive_url(pkg) or ""
            if b := re.search(r"commandlinetools-linux-(\d+)_latest\.zip", url):
                offer("ANDROID_SDK_TOOLS_VERSION", (int(b.group(1)),), b.group(1))
        # "android-36", "android-36.1", "android-37.0" (skips -extNN and canary)
        elif m := re.fullmatch(r"platforms;(android-(\d+)(?:\.(\d+))?)", path):
            platforms.setdefault(int(m.group(2)), {})[int(m.group(3) or 0)] = m.group(1)
        elif m := re.fullmatch(r"build-tools;([\d.]+)", path):
            offer("ANDROID_BUILD_TOOLS_VERSION", rev, m.group(1))
        elif m := re.fullmatch(r"ndk;([\d.]+)", path):
            if ndk_major is None or rev[0] == ndk_major:
                offer("ANDROID_NDK_VERSION", rev, m.group(1))

    if platforms:
        api = max(platforms)
        minors = platforms[api]
        # The base release plus the newest minor SDK release, if there is one.
        packages = dict.fromkeys([minors[min(minors)], minors[max(minors)]])
        best["ANDROID_PLATFORM_VERSION"] = (None, str(api))
        best["ANDROID_PLATFORM_PACKAGES"] = (None, " ".join(packages))

    missing = set(KEYS) - set(best)
    if missing:
        sys.exit(f"Could not determine: {', '.join(sorted(missing))}")
    return {k: v[1] for k, v in best.items()}


def version_key(value):
    return tuple(int(p) for p in re.findall(r"\d+", value))


def read_env(path):
    values = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                values[k.strip()] = v.strip()
    return values


def write_env(path, values):
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    out = []
    for line in lines:
        key = line.split("=", 1)[0].strip()
        out.append(f"{key}={values[key]}" if key in values and "=" in line else line)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")


def github_output(name, value):
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{name}<<__EOF__\n{value}\n__EOF__\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", help="read a local repository XML instead of downloading it")
    parser.add_argument("--versions-file", default=VERSIONS_FILE)
    parser.add_argument("--dry-run", action="store_true", help="report but do not write")
    args = parser.parse_args()

    if args.manifest:
        root = ET.parse(args.manifest).getroot()
    else:
        with urllib.request.urlopen(REPOSITORY_URL, timeout=60) as resp:
            root = ET.fromstring(resp.read())

    current = read_env(args.versions_file)
    ndk_major = current.get("ANDROID_NDK_MAJOR") or None
    latest = latest_versions(root, int(ndk_major) if ndk_major else None)

    updated = dict(current)
    changes = []
    for key, label in KEYS.items():
        old, new = current.get(key, ""), latest[key]
        # Compare the newest entry of space-separated lists (platform packages).
        if not old or version_key(new.split()[-1]) > version_key(old.split()[-1]):
            updated[key] = new
            changes.append(f"{label} {old or '(unset)'} -> {new}")

    for key, label in KEYS.items():
        print(f"{key}={updated[key]}  (latest stable {label}: {latest[key]})")

    if changes:
        message = "Bump " + ", ".join(changes)
        print("\n" + message)
        if not args.dry_run:
            write_env(args.versions_file, updated)
    else:
        message = ""
        print("\nAlready up to date.")

    github_output("changed", "true" if changes else "false")
    github_output("message", message)


if __name__ == "__main__":
    main()
