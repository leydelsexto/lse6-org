#!/usr/bin/env python3
"""Notify IndexNow about changed canonical LSE6.org URLs.

An accepted request means the URLs were submitted for discovery. It does not
mean that any search engine crawled or indexed them.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
SITE = "https://lse6.org"
HOST = "lse6.org"
KEY_FILE = "LSE6-3001FEC3240DA9D0-616-666.txt"
SITEMAPS = ("sitemap.xml",)
ENDPOINT = "https://api.indexnow.org/indexnow"
GLOBAL_FILES = {
    "robots.txt",
    "_headers",
    "_redirects",
    "CNAME",
    "feed.xml",
    KEY_FILE,
    *SITEMAPS,
}
IGNORED_PREFIXES = (".git/", ".github/", "tools/")
IGNORED_FILES = {".gitattributes", ".gitignore", "INTEGRITY.sha256", "README.md"}
PUBLIC_ASSET_SUFFIXES = {
    ".css",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".json",
    ".mp4",
    ".pdf",
    ".png",
    ".svg",
    ".txt",
    ".webm",
    ".webp",
    ".xml",
}


def sitemap_urls_from_bytes(raw: bytes) -> set[str]:
    root = ET.fromstring(raw)
    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    return {
        node.text.strip()
        for node in root.findall(f".//{namespace}loc")
        if node.text and node.text.strip().startswith(f"{SITE}/")
    }


def current_urls() -> set[str]:
    urls: set[str] = set()
    for relative in SITEMAPS:
        urls.update(sitemap_urls_from_bytes((ROOT / relative).read_bytes()))
    return urls


def urls_at_revision(revision: str) -> set[str]:
    if not revision or set(revision) == {"0"}:
        return set()
    urls: set[str] = set()
    for relative in SITEMAPS:
        result = subprocess.run(
            ["git", "show", f"{revision}:{relative}"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0:
            urls.update(sitemap_urls_from_bytes(result.stdout))
    return urls


def changed_paths(before: str, after: str) -> set[str]:
    if not before or set(before) == {"0"}:
        return set()
    result = subprocess.run(
        ["git", "diff", "--name-status", "--find-renames", before, after],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git diff failed")
    paths: set[str] = set()
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        for value in fields[1:]:
            paths.add(PurePosixPath(value).as_posix())
    return paths


def url_for_public_path(path: str, known_urls: set[str]) -> str | None:
    if path == "index.html":
        candidate = f"{SITE}/"
    elif path.endswith("/index.html"):
        candidate = f"{SITE}/{path.removesuffix('index.html')}"
    else:
        candidate = f"{SITE}/{path}"
    return candidate if candidate in known_urls else None


def select_changed_urls(
    paths: set[str], active_urls: set[str], previous_urls: set[str]
) -> set[str]:
    known_urls = active_urls | previous_urls
    selected: set[str] = set()
    submit_all = False
    for path in paths:
        path = PurePosixPath(path).as_posix()
        direct = url_for_public_path(path, known_urls)
        if direct:
            selected.add(direct)
            continue
        if path in GLOBAL_FILES:
            submit_all = True
            continue
        if path in IGNORED_FILES or path.startswith(IGNORED_PREFIXES):
            continue
        if path.endswith(".html"):
            # HTML outside the canonical sitemap is deliberately noindex.
            continue
        if PurePosixPath(path).suffix.lower() in PUBLIC_ASSET_SUFFIXES:
            # Shared assets and data can affect multiple rendered pages.
            submit_all = True
    if submit_all:
        selected.update(active_urls)
    return selected


def read_key() -> str:
    key = (ROOT / KEY_FILE).read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[A-Za-z0-9-]{8,128}", key):
        raise ValueError("IndexNow key must be 8-128 letters, digits, or dashes")
    if KEY_FILE != f"{key}.txt":
        raise ValueError("IndexNow key filename must match the key value")
    return key


def submit(urls: list[str], *, endpoint: str = ENDPOINT) -> int:
    key = read_key()
    payload = {
        "host": HOST,
        "key": key,
        "keyLocation": f"{SITE}/{KEY_FILE}",
        "urlList": urls,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "LSE6-IndexNow/1.0",
        },
        method="POST",
    )
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status = response.status
                if status not in {200, 202}:
                    raise RuntimeError(f"unexpected IndexNow status {status}")
                return status
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in {429, 500, 502, 503, 504}:
                raise
        except urllib.error.URLError as exc:
            last_error = exc
        if attempt < 2:
            time.sleep(2**attempt)
    raise RuntimeError(f"IndexNow submission failed after retries: {last_error}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="submit every canonical sitemap URL")
    parser.add_argument("--before", help="Git revision before the change")
    parser.add_argument("--after", default="HEAD", help="Git revision after the change")
    parser.add_argument("--dry-run", action="store_true", help="print URLs without network access")
    parser.add_argument("--endpoint", default=ENDPOINT, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    active = current_urls()
    if args.all or not args.before or set(args.before) == {"0"}:
        urls = sorted(active)
    else:
        previous = urls_at_revision(args.before)
        paths = changed_paths(args.before, args.after)
        urls = sorted(select_changed_urls(paths, active, previous))
    if not urls:
        print(json.dumps({"state": "no_public_url_changes", "host": HOST, "urlCount": 0}))
        return 0
    if args.dry_run:
        print(json.dumps({"state": "dry_run_not_submitted", "host": HOST, "urlCount": len(urls), "urls": urls}, indent=2))
        return 0
    status = submit(urls, endpoint=args.endpoint)
    print(
        json.dumps(
            {
                "state": "submitted_not_indexed",
                "host": HOST,
                "httpStatus": status,
                "urlCount": len(urls),
                "urls": urls,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
