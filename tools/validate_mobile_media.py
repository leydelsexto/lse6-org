#!/usr/bin/env python3
"""Validate responsive media on every indexable LSE6.ORG HTML surface."""
from pathlib import Path

from bs4 import BeautifulSoup
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MAX_DECODED_MB_PER_PAGE = 160
PAGES = {
    "index.html": 60,
    "evidencia/index.html": 6,
    "error-31-12-69/index.html": 7,
    "remake-666/index.html": 9,
    "rutas-sixtem/index.html": 6,
    "lseo-sixtem/index.html": 7,
    "fuentes/index.html": 2,
    "anomalias-temporales/index.html": 1,
    "musica/index.html": 7,
}

errors: list[str] = []
page_results: list[str] = []


def local_path(value: str, html_path: Path) -> Path:
    clean = value.split("?", 1)[0]
    if clean.startswith("/"):
        return ROOT / clean.lstrip("/")
    return html_path.parent / clean.lstrip("./")


for relative, minimum_images in PAGES.items():
    html_path = ROOT / relative
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8-sig"), "html.parser")
    local_images = []
    mobile_pixels = 0

    for img in soup.find_all("img", src=True):
        src = img["src"]
        if src.startswith(("http://", "https://", "data:")):
            continue
        original = local_path(src, html_path)
        if not original.exists():
            errors.append(f"{relative}: original missing: {src}")
            continue
        if (ROOT / "assets/images") not in original.resolve().parents:
            continue
        local_images.append(img)
        picture = img.parent if img.parent and img.parent.name == "picture" else None
        if picture is None or "mobile-picture" not in picture.get("class", []):
            errors.append(f"{relative}: missing mobile picture wrapper: {src}")
            continue
        source = picture.find("source", attrs={"media": "(max-width: 900px)"})
        if source is None or not source.get("srcset"):
            errors.append(f"{relative}: missing mobile source: {src}")
            continue
        mobile_src = source["srcset"].split()[0]
        mobile = local_path(mobile_src, html_path)
        if not mobile.exists():
            errors.append(f"{relative}: mobile asset missing: {mobile_src}")
            continue
        try:
            with Image.open(mobile) as media:
                width, height = media.size
            if width > 640:
                errors.append(f"{relative}: mobile asset too wide ({width}px): {mobile_src}")
            mobile_pixels += width * height
        except Exception as exc:
            errors.append(f"{relative}: unreadable mobile asset {mobile_src}: {exc}")

    mobile_mb = mobile_pixels * 4 / 1024 / 1024
    if mobile_mb > MAX_DECODED_MB_PER_PAGE:
        errors.append(f"{relative}: decoded mobile memory too high: {mobile_mb:.1f} MB")
    if len(local_images) < minimum_images:
        errors.append(f"{relative}: unexpected local image count: {len(local_images)} < {minimum_images}")
    page_results.append(f"{relative}={len(local_images)} images/{mobile_mb:.1f} MB")

if errors:
    print("MOBILE MEDIA VALIDATION FAILED")
    for error in errors[:50]:
        print(" -", error)
    if len(errors) > 50:
        print(f" - ... and {len(errors) - 50} more")
    raise SystemExit(1)

print("MOBILE MEDIA VALIDATION PASSED")
print("; ".join(page_results))
