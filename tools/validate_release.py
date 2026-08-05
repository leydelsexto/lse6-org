#!/usr/bin/env python3
"""🔥 Validate the LSE6.ORG static release before GitHub / Cloudflare Pages."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
SITE = "https://lse6.org/"
MAX_BYTES = 25 * 1024 * 1024
FAILURES: list[str] = []
PASSES: list[str] = []


def ok(label: str) -> None:
    PASSES.append(label)


def fail(label: str) -> None:
    FAILURES.append(label)


def local_path(value: str, source: Path = ROOT / "index.html") -> Path | None:
    if not value or value.startswith(("#", "mailto:", "tel:", "data:", "blob:", "javascript:")):
        return None
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        if parsed.netloc not in {"lse6.org", "www.lse6.org"}:
            return None
        raw = parsed.path
    else:
        raw = parsed.path
    raw = unquote(raw)
    if not raw or raw == "/":
        return ROOT / "index.html"
    if raw.startswith("/"):
        return ROOT / raw.lstrip("/")
    return (source.parent / raw).resolve()


def check_json_xml() -> None:
    for path in sorted(ROOT.rglob("*.json")):
        if ".git" in path.parts:
            continue
        try:
            json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            fail(f"JSON inválido: {path.relative_to(ROOT)} ({exc})")
    if not any(item.startswith("JSON inválido") for item in FAILURES):
        ok("Todos los JSON son válidos")

    for name in ["sitemap.xml", "image-sitemap.xml"]:
        try:
            ET.parse(ROOT / name)
        except Exception as exc:
            fail(f"XML inválido: {name} ({exc})")
    if not any(item.startswith("XML inválido") for item in FAILURES):
        ok("Sitemaps XML válidos")


def check_html() -> BeautifulSoup:
    raw = (ROOT / "index.html").read_text(encoding="utf-8-sig")
    soup = BeautifulSoup(raw, "html.parser")
    if soup.title and soup.title.get_text(strip=True):
        ok("Título HTML presente")
    else:
        fail("Falta título HTML")

    canonical = soup.find("link", rel=lambda rel: rel and "canonical" in rel)
    if canonical and canonical.get("href") == SITE:
        ok("Canonical exacto a https://lse6.org/")
    else:
        fail(f"Canonical incorrecto: {canonical.get('href') if canonical else 'ausente'}")

    ids = [node.get("id") for node in soup.find_all(id=True)]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        fail(f"IDs duplicados: {', '.join(duplicates)}")
    else:
        ok("Sin IDs HTML duplicados")

    description = soup.find("meta", attrs={"name": "description"})
    if description and 100 <= len(description.get("content", "")) <= 320:
        ok("Meta description descriptiva")
    else:
        fail("Meta description ausente o fuera de rango")

    json_ld = soup.find_all("script", attrs={"type": "application/ld+json"})
    for idx, node in enumerate(json_ld, 1):
        try:
            json.loads(node.string or node.get_text())
        except Exception as exc:
            fail(f"JSON-LD #{idx} inválido: {exc}")
    if json_ld and not any(item.startswith("JSON-LD") for item in FAILURES):
        ok(f"JSON-LD válido ({len(json_ld)} bloque)")
    elif not json_ld:
        fail("Falta JSON-LD")

    center_links = [a for a in soup.find_all("a", href=True) if a["href"].rstrip("/") == "https://lse6.com"]
    center_contract = all(
        a.get("target") == "_blank"
        and {"noopener", "noreferrer"}.issubset(set(a.get("rel", [])))
        for a in center_links
    )
    if len(center_links) >= 4 and center_contract:
        ok(f"LSE6.com abre en pestaña nueva y conserva LSE6.ORG ({len(center_links)} puntos)")
    else:
        fail(f"Contrato centro/extensión incompleto en enlaces LSE6.com: {len(center_links)}")

    return soup


def check_local_assets(soup: BeautifulSoup) -> None:
    attrs = [("img", "src"), ("script", "src"), ("link", "href"), ("a", "href"), ("source", "src")]
    missing: list[str] = []
    checked: set[Path] = set()
    for tag, attr in attrs:
        for node in soup.find_all(tag):
            value = node.get(attr)
            target = local_path(value) if value else None
            if target is None:
                continue
            if target.suffix == "" and target != ROOT / "index.html":
                continue
            checked.add(target)
            if not target.exists():
                missing.append(f"{tag}[{attr}]={value}")
    if missing:
        fail("Recursos locales faltantes: " + "; ".join(missing[:20]))
    else:
        ok(f"Recursos locales enlazados existen ({len(checked)} rutas)")

    installed = 0
    for img in soup.find_all("img", src=True):
        path = local_path(img["src"])
        if path is None or not path.exists() or path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        installed += 1
        if not img.get("alt", "").strip():
            fail(f"Imagen sin alt: {img['src']}")
        try:
            with Image.open(path) as image:
                expected = (str(image.width), str(image.height))
            actual = (img.get("width"), img.get("height"))
            if actual != expected:
                fail(f"Dimensiones HTML incorrectas: {img['src']} {actual} != {expected}")
        except Exception as exc:
            fail(f"No se pudo leer imagen {img['src']}: {exc}")
    if not any(item.startswith(("Imagen sin alt", "Dimensiones HTML", "No se pudo leer imagen")) for item in FAILURES):
        ok(f"Imágenes HTML con alt y dimensiones reales ({installed})")


def check_sitemaps_and_robots(soup: BeautifulSoup) -> None:
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9", "image": "http://www.google.com/schemas/sitemap-image/1.1"}
    root = ET.parse(ROOT / "image-sitemap.xml").getroot()
    image_locs = {node.text for node in root.findall(".//image:loc", ns) if node.text}
    html_images = set()
    for img in soup.find_all("img", src=True):
        path = local_path(img["src"])
        if path and path.exists():
            rel = path.relative_to(ROOT).as_posix()
            html_images.add(f"https://lse6.org/{rel}")
    expected = html_images | {"https://lse6.org/assets/images/system/lse6-org-og.jpg"}
    missing = sorted(expected - image_locs)
    if missing:
        fail("Imágenes ausentes del image sitemap: " + ", ".join(missing))
    else:
        ok(f"Image sitemap cubre imágenes instaladas ({len(image_locs)})")

    sitemap = ET.parse(ROOT / "sitemap.xml").getroot()
    page_locs = {node.text for node in sitemap.findall(".//sm:loc", ns) if node.text}
    if "https://lse6.org/image-sitemap.xml" in page_locs:
        fail("image-sitemap.xml no debe figurar como URL de página dentro del sitemap principal")
    else:
        ok("Sitemap principal separado del sitemap de imágenes")

    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
    if "Sitemap: https://lse6.org/sitemap.xml" in robots and "Sitemap: https://lse6.org/image-sitemap.xml" in robots:
        ok("robots.txt declara ambos sitemaps")
    else:
        fail("robots.txt no declara ambos sitemaps")



def check_center_navigation_contract() -> None:
    """Guard the visible route from LSE6.ORG to the canonical LSE6.com center."""
    html = (ROOT / "index.html").read_text(encoding="utf-8-sig")
    soup = BeautifulSoup(html, "html.parser")
    required = [
        soup.select_one("a.archive-line.center-return-link"),
        soup.select_one("a.core-button"),
        soup.select_one("a.footer-center-link"),
    ]
    if all(
        node
        and node.get("href") == "https://lse6.com/"
        and node.get("target") == "_blank"
        and {"noopener", "noreferrer"}.issubset(set(node.get("rel", [])))
        for node in required
    ):
        ok("Ruta visible a LSE6.com abre el centro sin cerrar el archivo")
    else:
        fail("Ruta visible a LSE6.com no preserva correctamente la pestaña de LSE6.ORG")

    css = (ROOT / "assets/css/styles.css").read_text(encoding="utf-8-sig")
    title_block = re.search(r"\.gold-title\s*\{(?P<body>.*?)\}", css, flags=re.S)
    if title_block and re.search(r"pointer-events\s*:\s*none\s*;", title_block.group("body")):
        ok("Título decorativo no intercepta los enlaces del núcleo")
    else:
        fail("El título decorativo puede interceptar el clic hacia LSE6.com")


def check_cloudflare_and_encoding() -> None:
    redirects = (ROOT / "_redirects").read_text(encoding="utf-8")
    required = ["/centro https://lse6.com/ 301", "/lse6 https://lse6.com/ 301"]
    if all(rule in redirects for rule in required):
        ok("Redirecciones Cloudflare al núcleo presentes")
    else:
        fail("Faltan redirecciones Cloudflare al núcleo")

    headers = (ROOT / "_headers").read_text(encoding="utf-8")
    for token in ["Content-Security-Policy", "X-Content-Type-Options", "X-Robots-Tag: noindex, nofollow"]:
        if token not in headers:
            fail(f"_headers no contiene {token}")
    if not any(item.startswith("_headers no contiene") for item in FAILURES):
        ok("Headers de seguridad, caché y previews configurados")

    no_bom = ["_headers", "_redirects", "robots.txt", "sitemap.xml", "image-sitemap.xml", "site.webmanifest"]
    for name in no_bom:
        if (ROOT / name).read_bytes().startswith(b"\xef\xbb\xbf"):
            fail(f"BOM no permitido en {name}")
    if not any(item.startswith("BOM no permitido") for item in FAILURES):
        ok("Archivos de configuración sin BOM")

    with_bom = ["index.html", "404.html", "README.md", "assets/css/styles.css", "assets/js/app.js", "assets/js/site-identity.js", "site_identity_LSE6_ORG.js"]
    for name in with_bom:
        if not (ROOT / name).read_bytes().startswith(b"\xef\xbb\xbf"):
            fail(f"Falta BOM UTF-8 solicitado en {name}")
    if not any(item.startswith("Falta BOM") for item in FAILURES):
        ok("BOM UTF-8 aplicado solo a archivos compatibles seleccionados")


def check_limits_and_integrity() -> None:
    largest = max((p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts), key=lambda p: p.stat().st_size)
    if largest.stat().st_size < MAX_BYTES:
        ok(f"Archivo mayor bajo 25 MiB: {largest.relative_to(ROOT)} ({largest.stat().st_size / 1024 / 1024:.2f} MiB)")
    else:
        fail(f"Archivo supera 25 MiB: {largest.relative_to(ROOT)}")

    listed: dict[str, str] = {}
    for line in (ROOT / "INTEGRITY.sha256").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split("  ", 1)
        listed[name] = digest
    mismatches = []
    for name, expected in listed.items():
        path = ROOT / name
        if not path.exists():
            mismatches.append(f"faltante:{name}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            mismatches.append(f"hash:{name}")
    actual_files = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and p.name != "INTEGRITY.sha256" and ".git" not in p.parts}
    unlisted = sorted(actual_files - set(listed))
    if mismatches or unlisted:
        fail(f"Integridad inválida: {mismatches[:8]} no listados={unlisted[:8]}")
    else:
        ok(f"Integridad SHA-256 completa ({len(listed)} archivos)")



def check_temporal_csv_archive() -> None:
    folder = ROOT / "data/saltos-temporales"
    manifest_path = folder / "index.json"
    if not manifest_path.exists():
        fail("Falta el manifiesto del CSV temporal")
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    files = manifest.get("files", [])
    if len(files) != 6:
        fail(f"Archivo temporal incompleto: {len(files)} partes")
        return
    total_rows = 0
    headers = set()
    reconstructed = hashlib.sha256()
    errors = []
    for index, item in enumerate(files):
        path = folder / item["filename"]
        if not path.exists():
            errors.append(f"faltante:{item['filename']}")
            continue
        if path.stat().st_size >= MAX_BYTES:
            errors.append(f"tamaño:{item['filename']}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != item["sha256"]:
            errors.append(f"hash:{item['filename']}")
        with path.open("rb") as source:
            header = source.readline()
            headers.add(header)
            if index == 0:
                reconstructed.update(header)
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                reconstructed.update(chunk)
        total_rows += int(item["rows"])
    if len(headers) != 1:
        errors.append("encabezados distintos")
    if total_rows != int(manifest.get("source_rows", -1)):
        errors.append(f"filas:{total_rows}")
    if reconstructed.hexdigest() != manifest.get("source_sha256"):
        errors.append("reconstrucción SHA-256")
    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    required_urls = [
        "https://lse6.org/data/saltos-temporales/",
        *[f"https://lse6.org/data/saltos-temporales/LSE6_SALTOS_TEMPORALES_PARTE_{part:02d}_DE_06.csv" for part in range(1, 7)],
    ]
    missing_urls = [url for url in required_urls if url not in sitemap]
    if missing_urls:
        errors.append(f"sitemap:{missing_urls}")
    if errors:
        fail("Archivo temporal dividido inválido: " + " | ".join(errors))
    else:
        ok(f"CSV temporal completo en 6 partes ({total_rows:,} registros, SHA-256 reconstruible)")

def check_javascript() -> None:
    js_files = [ROOT / "assets/js/app.js", ROOT / "assets/js/site-identity.js", ROOT / "site_identity_LSE6_ORG.js"]
    errors = []
    for path in js_files:
        result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True)
        if result.returncode:
            errors.append(f"{path.relative_to(ROOT)}: {result.stderr.strip()}")
    if errors:
        fail("JavaScript inválido: " + " | ".join(errors))
    else:
        ok("JavaScript válido con node --check")


def main() -> int:
    check_json_xml()
    soup = check_html()
    check_local_assets(soup)
    check_sitemaps_and_robots(soup)
    check_center_navigation_contract()
    check_cloudflare_and_encoding()
    check_temporal_csv_archive()
    check_limits_and_integrity()
    check_javascript()

    print("\n👁 LSE6.ORG VALIDACIÓN DE RELEASE")
    for item in PASSES:
        print(f"  ✅ {item}")
    for item in FAILURES:
        print(f"  ❌ {item}")
    print(f"\n🔥 RESULTADO: {len(PASSES)} PASSES · {len(FAILURES)} FALLOS")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
