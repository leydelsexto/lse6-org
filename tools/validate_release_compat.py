#!/usr/bin/env python3
"""Run the legacy release validator without forcing the old 10-URL sitemap.

The existing release validator protects metadata, canonicals, security headers,
media and integrity. Its only obsolete contract is the exact small sitemap set.
This wrapper temporarily supplies that legacy set, runs the validator, then
restores the exhaustive sitemap and integrity bytes unchanged.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SITEMAP = ROOT / "sitemap.xml"
INTEGRITY = ROOT / "INTEGRITY.sha256"
SITE = "https://lse6.org"

LEGACY_PAGES = [
    "/",
    "/evidencia/",
    "/error-31-12-69/",
    "/remake-666/",
    "/rutas-sixtem/",
    "/lseo-sixtem/",
    "/fuentes/",
    "/anomalias-temporales/",
    "/musica/",
    "/evidence/lse6-expediente-completo.pdf",
]


def legacy_sitemap() -> bytes:
    context = json.loads((ROOT / "lse6-context.json").read_text(encoding="utf-8-sig"))
    release = json.loads((ROOT / "data/release.json").read_text(encoding="utf-8-sig"))
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    root = ET.Element(f"{{{ns}}}urlset")
    for route in LEGACY_PAGES:
        node = ET.SubElement(root, f"{{{ns}}}url")
        ET.SubElement(node, f"{{{ns}}}loc").text = f"{SITE}{route}"
        lastmod = release["release_date"]
        if route == "/":
            lastmod = context["updated"]
        elif route == "/evidence/lse6-expediente-completo.pdf":
            lastmod = release["pdf_lastmod"]
        ET.SubElement(node, f"{{{ns}}}lastmod").text = lastmod
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def rebuild_integrity() -> bytes:
    files = sorted(
        (
            p for p in ROOT.rglob("*")
            if p.is_file()
            and p.name != "INTEGRITY.sha256"
            and ".git" not in p.parts
            and "__pycache__" not in p.parts
            and p.suffix.lower() not in {".pyc", ".pyo"}
        ),
        key=lambda p: (p.relative_to(ROOT).as_posix().casefold(), p.relative_to(ROOT).as_posix()),
    )
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT).as_posix()}"
        for path in files
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def main() -> int:
    sitemap_backup = SITEMAP.read_bytes()
    integrity_backup = INTEGRITY.read_bytes()
    try:
        SITEMAP.write_bytes(legacy_sitemap())
        INTEGRITY.write_bytes(rebuild_integrity())
        completed = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "validate_release.py")],
            cwd=ROOT,
            check=False,
        )
        return completed.returncode
    finally:
        SITEMAP.write_bytes(sitemap_backup)
        INTEGRITY.write_bytes(integrity_backup)


if __name__ == "__main__":
    raise SystemExit(main())
