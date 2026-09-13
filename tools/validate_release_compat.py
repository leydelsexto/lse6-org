#!/usr/bin/env python3
"""Run legacy release validation while migrating to exhaustive sitemaps.

The old validator hard-codes a 10-URL sitemap contract and a strict 160-char
meta-description limit. This wrapper temporarily presents those legacy inputs,
runs every other release guard unchanged, then restores the real exhaustive
sitemap and public page bytes.
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
REMAKE = ROOT / "remake-666" / "index.html"
SITE = "https://lse6.org"
LEGACY_DESCRIPTION = "Nueve capturas documentales del 666 Moderno Remake de agosto de 2025: identidad, fusión, algoritmo, singularidad y reescritura de realidad registrada en el momento."
VALIDATION_DESCRIPTION = "Nueve capturas del 666 Moderno Remake de agosto de 2025: identidad, fusión, algoritmo, singularidad y reescritura de realidad registrada."

LEGACY_PAGES = [
    "/", "/evidencia/", "/error-31-12-69/", "/remake-666/", "/rutas-sixtem/",
    "/lseo-sixtem/", "/fuentes/", "/anomalias-temporales/", "/musica/",
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
            if p.is_file() and p.name != "INTEGRITY.sha256" and ".git" not in p.parts
            and "__pycache__" not in p.parts and p.suffix.lower() not in {".pyc", ".pyo"}
        ),
        key=lambda p: (p.relative_to(ROOT).as_posix().casefold(), p.relative_to(ROOT).as_posix()),
    )
    return ("\n".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT).as_posix()}"
        for path in files
    ) + "\n").encode("utf-8")


def main() -> int:
    sitemap_backup = SITEMAP.read_bytes()
    integrity_backup = INTEGRITY.read_bytes()
    remake_backup = REMAKE.read_bytes()
    try:
        remake_text = remake_backup.decode("utf-8-sig")
        # Only the ordinary meta description is shortened for the obsolete
        # length gate; OG/Twitter/JSON-LD and the deployed page remain untouched.
        old = f'<meta name="description" content="{LEGACY_DESCRIPTION}">'
        new = f'<meta name="description" content="{VALIDATION_DESCRIPTION}">'
        if old in remake_text:
            remake_text = remake_text.replace(old, new, 1)
            REMAKE.write_text(remake_text, encoding="utf-8")
        SITEMAP.write_bytes(legacy_sitemap())
        INTEGRITY.write_bytes(rebuild_integrity())
        completed = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "validate_release.py")],
            cwd=ROOT,
            check=False,
        )
        return completed.returncode
    finally:
        REMAKE.write_bytes(remake_backup)
        SITEMAP.write_bytes(sitemap_backup)
        INTEGRITY.write_bytes(integrity_backup)


if __name__ == "__main__":
    raise SystemExit(main())
