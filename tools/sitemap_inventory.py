#!/usr/bin/env python3
"""Generate exhaustive public sitemaps for LSE6.ORG.

The main sitemap is the machine-facing inventory: every deliberately public
route/file except repository plumbing, internal tooling, placeholders and
literal instruction files. The image sitemap mirrors every public image and
associates it with the closest canonical thematic page.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import quote
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://lse6.org"
SITEMAP = ROOT / "sitemap.xml"
IMAGE_SITEMAP = ROOT / "image-sitemap.xml"
INTEGRITY = ROOT / "INTEGRITY.sha256"

EXCLUDED_PREFIXES = (
    ".git/",
    ".github/",
    "tools/",
)
EXCLUDED_EXACT = {
    ".gitattributes",
    ".gitignore",
    ".nojekyll",
    "404.html",
    "CNAME",
    "_headers",
    "_redirects",
    "README.md",
    "assets/images/LEEME_PRIMERO.txt",
    "assets/source-library/README.md",
    "docs/README.md",
    "data/saltos-temporales/README.txt",
}
EXCLUDED_NAMES = {".gitkeep", "Thumbs.db", ".DS_Store"}
PUBLIC_SUFFIXES = {
    ".css", ".csv", ".docx", ".html", ".jpeg", ".jpg", ".js", ".json",
    ".md", ".mp4", ".pdf", ".png", ".sha256", ".svg", ".txt", ".webm",
    ".webmanifest", ".webp", ".xml",
}
IMAGE_SUFFIXES = {".jpeg", ".jpg", ".png", ".svg", ".webp"}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def is_public_path(path: Path) -> bool:
    relative = rel(path)
    if any(relative.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        return False
    if relative in EXCLUDED_EXACT or path.name in EXCLUDED_NAMES:
        return False
    if path.name == "INTEGRITY.sha256":
        return True
    return path.suffix.lower() in PUBLIC_SUFFIXES


def public_files() -> list[Path]:
    return sorted(
        (p for p in ROOT.rglob("*") if p.is_file() and is_public_path(p)),
        key=lambda p: (rel(p).casefold(), rel(p)),
    )


def url_for(path: Path) -> str:
    relative = rel(path)
    if relative == "index.html":
        return f"{SITE}/"
    if relative.endswith("/index.html"):
        relative = relative[: -len("index.html")]
    encoded = quote(relative, safe="/._-~")
    return f"{SITE}/{encoded}"


def public_urls() -> set[str]:
    return {url_for(path) for path in public_files()}


def lastmod_for(path: Path) -> str | None:
    relative = rel(path)
    if relative == "index.html":
        try:
            return json.loads((ROOT / "lse6-context.json").read_text(encoding="utf-8-sig"))["updated"]
        except Exception:
            return None
    if relative == "evidence/lse6-expediente-completo.pdf":
        try:
            return json.loads((ROOT / "data/release.json").read_text(encoding="utf-8-sig"))["pdf_lastmod"]
        except Exception:
            return None
    return None


def build_main_sitemap() -> bytes:
    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    root = ET.Element(f"{{{ns}}}urlset")
    seen: set[str] = set()
    for path in public_files():
        url = url_for(path)
        if url in seen:
            continue
        seen.add(url)
        node = ET.SubElement(root, f"{{{ns}}}url")
        ET.SubElement(node, f"{{{ns}}}loc").text = url
        lastmod = lastmod_for(path)
        if lastmod:
            ET.SubElement(node, f"{{{ns}}}lastmod").text = lastmod
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def image_host(path: Path) -> str:
    value = rel(path).lower()
    mapping = (
        (("/evidencia/", "assets/images/evidencia/", "assets/mobile/evidencia/"), "/evidencia/"),
        (("error-31-12-69",), "/error-31-12-69/"),
        (("remake-666",), "/remake-666/"),
        (("rutas-sixtem",), "/rutas-sixtem/"),
        (("lseo-sixtem",), "/lseo-sixtem/"),
        (("youtube", "canciones"), "/musica/"),
    )
    for needles, host in mapping:
        if any(needle in value for needle in needles):
            return f"{SITE}{host}"
    return f"{SITE}/"


def build_image_sitemap() -> bytes:
    sm = "http://www.sitemaps.org/schemas/sitemap/0.9"
    im = "http://www.google.com/schemas/sitemap-image/1.1"
    ET.register_namespace("", sm)
    ET.register_namespace("image", im)
    root = ET.Element(f"{{{sm}}}urlset")
    groups: dict[str, list[Path]] = {}
    for path in public_files():
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        groups.setdefault(image_host(path), []).append(path)
    for host in sorted(groups):
        node = ET.SubElement(root, f"{{{sm}}}url")
        ET.SubElement(node, f"{{{sm}}}loc").text = host
        for path in groups[host]:
            image = ET.SubElement(node, f"{{{im}}}image")
            ET.SubElement(image, f"{{{im}}}loc").text = url_for(path)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def integrity_bytes() -> bytes:
    files = sorted(
        (
            p for p in ROOT.rglob("*")
            if p.is_file()
            and p.name != "INTEGRITY.sha256"
            and ".git" not in p.parts
            and "__pycache__" not in p.parts
            and p.suffix.lower() not in {".pyc", ".pyo"}
        ),
        key=lambda p: (rel(p).casefold(), rel(p)),
    )
    lines = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {rel(path)}" for path in files]
    return ("\n".join(lines) + "\n").encode("utf-8")


def expected_outputs() -> dict[Path, bytes]:
    # Build sitemaps first; integrity is calculated after their bytes are present.
    return {SITEMAP: build_main_sitemap(), IMAGE_SITEMAP: build_image_sitemap()}


def write_outputs() -> None:
    outputs = expected_outputs()
    for path, data in outputs.items():
        path.write_bytes(data)
    INTEGRITY.write_bytes(integrity_bytes())


def check_outputs() -> list[str]:
    expected = expected_outputs()
    failures: list[str] = []
    for path, data in expected.items():
        if not path.exists() or path.read_bytes() != data:
            failures.append(rel(path))
    current_integrity = INTEGRITY.read_bytes() if INTEGRITY.exists() else b""
    if current_integrity != integrity_bytes():
        failures.append("INTEGRITY.sha256")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv or sys.argv[1:])
    if args.check:
        failures = check_outputs()
        if failures:
            print("STALE_PUBLIC_INVENTORY=" + ",".join(failures))
            return 1
        print(f"PUBLIC_INVENTORY_OK urls={len(public_urls())}")
        return 0
    write_outputs()
    print(f"PUBLIC_INVENTORY_WRITTEN urls={len(public_urls())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
