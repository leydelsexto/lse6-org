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
DESCRIPTION_MIN = 25
DESCRIPTION_MAX = 160
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
SITE = "https://lse6.org/"
ARTIST_ID = "https://lse6.com/#artist"
BRAND_ID = "https://lse6.com/#brand"
SYSTEM_ID = "https://lse6.com/#system"
WEBSITE_ID = "https://lse6.org/#website"
WEBSITE_NAME = "LSE6.ORG · Archivo Vivo"
MAX_BYTES = 25 * 1024 * 1024
FAILURES: list[str] = []
PASSES: list[str] = []
CANONICAL_HTML = {
    "index.html": "https://lse6.org/",
    "evidencia/index.html": "https://lse6.org/evidencia/",
    "error-31-12-69/index.html": "https://lse6.org/error-31-12-69/",
    "remake-666/index.html": "https://lse6.org/remake-666/",
    "rutas-sixtem/index.html": "https://lse6.org/rutas-sixtem/",
    "lseo-sixtem/index.html": "https://lse6.org/lseo-sixtem/",
    "fuentes/index.html": "https://lse6.org/fuentes/",
    "anomalias-temporales/index.html": "https://lse6.org/anomalias-temporales/",
    "musica/index.html": "https://lse6.org/musica/",
}


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
        target = ROOT / raw.lstrip("/")
    else:
        target = (source.parent / raw).resolve()
    if raw.endswith("/") or target.is_dir():
        return target / "index.html"
    return target


def check_canonical_html_pages() -> None:
    titles: dict[str, str] = {}
    descriptions: dict[str, str] = {}
    errors: list[str] = []
    checked_links = 0
    checked_images = 0
    for relative, expected_canonical in CANONICAL_HTML.items():
        path = ROOT / relative
        if not path.exists():
            errors.append(f"falta:{relative}")
            continue
        soup = BeautifulSoup(path.read_text(encoding="utf-8-sig"), "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        description_node = soup.find("meta", attrs={"name": "description"})
        description = description_node.get("content", "").strip() if description_node else ""
        canonical_node = soup.find("link", rel=lambda rel: rel and "canonical" in rel)
        canonical = canonical_node.get("href") if canonical_node else ""
        h1s = soup.find_all("h1")
        robots = soup.find("meta", attrs={"name": "robots"})
        if not title:
            errors.append(f"title:{relative}")
        elif title in titles:
            errors.append(f"title-duplicado:{relative}={titles[title]}")
        else:
            titles[title] = relative
        if not (DESCRIPTION_MIN <= len(description) <= DESCRIPTION_MAX):
            errors.append(f"description:{relative}:{len(description)}")
        elif description in descriptions:
            errors.append(f"description-duplicada:{relative}={descriptions[description]}")
        else:
            descriptions[description] = relative
        if canonical != expected_canonical:
            errors.append(f"canonical:{relative}:{canonical}")
        if len(h1s) != 1 or not h1s[0].get_text(strip=True):
            errors.append(f"h1:{relative}:{len(h1s)}")
        if robots and "noindex" in robots.get("content", "").lower():
            errors.append(f"noindex:{relative}")
        visible_words = len(soup.get_text(" ", strip=True).split())
        if visible_words < 180:
            errors.append(f"thin:{relative}:{visible_words}")

        for prop in ["og:title", "og:description", "og:url", "og:image"]:
            if not soup.find("meta", attrs={"property": prop}, content=True):
                errors.append(f"{prop}:{relative}")
        for name in ["twitter:card", "twitter:title", "twitter:description", "twitter:image"]:
            if not soup.find("meta", attrs={"name": name}, content=True):
                errors.append(f"{name}:{relative}")
        if not soup.find(lambda tag: tag.name == "script" and tag.get("type") == "application/ld+json"):
            errors.append(f"jsonld-ausente:{relative}")
        for node in soup.find_all("script", attrs={"type": "application/ld+json"}):
            try:
                json.loads(node.string or node.get_text())
            except Exception as exc:
                errors.append(f"jsonld:{relative}:{exc}")
        if relative != "index.html":
            if not soup.find("nav", attrs={"aria-label": "Migas de pan"}):
                errors.append(f"breadcrumbs:{relative}")
            center = soup.find("a", href="https://lse6.com/")
            if not center:
                errors.append(f"lse6com:{relative}")

        for tag, attr in [("a", "href"), ("img", "src"), ("script", "src"), ("link", "href")]:
            for node in soup.find_all(tag):
                value = node.get(attr)
                target = local_path(value, path) if value else None
                if target is None:
                    continue
                checked_links += 1
                if not target.exists():
                    errors.append(f"enlace:{relative}:{value}")
        for image in soup.find_all("img", src=True):
            target = local_path(image["src"], path)
            if not target or not target.exists():
                continue
            checked_images += 1
            if not image.get("alt", "").strip():
                errors.append(f"alt:{relative}:{image['src']}")
            try:
                with Image.open(target) as opened:
                    expected_dims = (str(opened.width), str(opened.height))
                if (image.get("width"), image.get("height")) != expected_dims:
                    errors.append(f"dimensiones:{relative}:{image['src']}")
            except Exception as exc:
                errors.append(f"imagen:{relative}:{image['src']}:{exc}")
    if errors:
        fail("Puertas HTML canónicas inválidas: " + " | ".join(errors[:30]))
    else:
        ok(f"Puertas HTML completas, únicas y enlazadas ({len(CANONICAL_HTML)} páginas, {checked_links} referencias, {checked_images} imágenes)")


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
    if description and DESCRIPTION_MIN <= len(description.get("content", "")) <= DESCRIPTION_MAX:
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


def jsonld_graph(path: Path) -> list[dict]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8-sig"), "html.parser")
    nodes: list[dict] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        payload = json.loads(script.string or script.get_text())
        if isinstance(payload, dict):
            graph = payload.get("@graph", [payload])
            if isinstance(graph, list):
                nodes.extend(item for item in graph if isinstance(item, dict))
    return nodes


def walk_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_dicts(child)


def ref_ids(value) -> set[str]:
    return {
        item["@id"]
        for item in walk_dicts(value)
        if isinstance(item.get("@id"), str)
    }


def check_entity_contract() -> None:
    errors: list[str] = []
    expected_about = {ARTIST_ID, BRAND_ID, SYSTEM_ID}
    paths = [ROOT / relative for relative in CANONICAL_HTML]
    technical_path = ROOT / "data/saltos-temporales/index.html"

    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        graph = jsonld_graph(path)
        websites = [node for node in graph if node.get("@id") == WEBSITE_ID]
        if len(websites) != 1:
            errors.append(f"website:{relative}:{len(websites)}")
            continue
        website = websites[0]
        if website.get("name") != WEBSITE_NAME:
            errors.append(f"website-name:{relative}:{website.get('name')}")
        if website.get("publisher") != {"@id": ARTIST_ID}:
            errors.append(f"website-publisher:{relative}")
        if ref_ids(website.get("about")) != expected_about:
            errors.append(f"website-about:{relative}:{sorted(ref_ids(website.get('about')))}")

        pages = [
            node for node in graph
            if node.get("@id") in {f"{SITE}#webpage", f"{CANONICAL_HTML[relative]}#page"}
        ]
        if len(pages) != 1:
            errors.append(f"page:{relative}:{len(pages)}")
        else:
            page = pages[0]
            if page.get("creator") != {"@id": ARTIST_ID} or page.get("publisher") != {"@id": ARTIST_ID}:
                errors.append(f"page-authorship:{relative}")
            if ref_ids(page.get("about")) != expected_about:
                errors.append(f"page-about:{relative}:{sorted(ref_ids(page.get('about')))}")

        for node in walk_dicts(graph):
            if node.get("@type") == "Organization" and node.get("name") == "LEY DEL SEXTO":
                errors.append(f"brand-as-organization:{relative}")

    home_graph = jsonld_graph(ROOT / "index.html")
    if any(node.get("@id") in {ARTIST_ID, BRAND_ID, SYSTEM_ID} for node in home_graph):
        errors.append("org-redeclares-com-entities")

    music_graph = jsonld_graph(ROOT / "musica/index.html")
    recordings = [node for node in walk_dicts(music_graph) if node.get("@type") == "MusicRecording"]
    if len(recordings) != 7 or any(node.get("byArtist") != {"@id": ARTIST_ID} for node in recordings):
        errors.append(f"music-byArtist:{len(recordings)}")

    technical_soup = BeautifulSoup(technical_path.read_text(encoding="utf-8-sig"), "html.parser")
    robots = technical_soup.find("meta", attrs={"name": "robots"})
    robots_tokens = set((robots.get("content", "") if robots else "").lower().split(","))
    if not {"noindex", "nofollow"}.issubset(robots_tokens):
        errors.append("dataset-robots")
    technical_graph = jsonld_graph(technical_path)
    if any(node.get("@id") == "https://lse6.org/#lse6-artist" for node in walk_dicts(technical_graph)):
        errors.append("dataset-local-artist")
    for node in walk_dicts(technical_graph):
        if node.get("@type") in {"CollectionPage", "Dataset"}:
            if node.get("creator") != {"@id": ARTIST_ID} or node.get("publisher") != {"@id": ARTIST_ID}:
                errors.append(f"dataset-authorship:{node.get('@type')}")
        if node.get("@type") == "DataDownload":
            errors.append("dataset-machine-distribution")

    entity = json.loads((ROOT / "data/entity-schema.json").read_text(encoding="utf-8-sig"))
    if entity.get("creator") != {"@id": ARTIST_ID} or entity.get("publisher") != {"@id": ARTIST_ID}:
        errors.append("entity-schema-authorship")
    if ref_ids(entity.get("about")) != expected_about:
        errors.append("entity-schema-about")

    legacy_hits = []
    for path in [*paths, technical_path, ROOT / "tools/templates/index.template.html"]:
        if "https://lse6.org/#lse6-artist" in path.read_text(encoding="utf-8-sig"):
            legacy_hits.append(path.relative_to(ROOT).as_posix())
    if legacy_hits:
        errors.append("legacy-local-artist:" + ",".join(legacy_hits))

    # The legacy identity bundle is still public. Execute its exported builder so
    # it cannot silently resurrect the retired person/organization/law graph.
    legacy_script = ROOT / "site_identity_LSE6_ORG.js"
    probe = (
        "globalThis.console.log=()=>{};"
        "const api=require(process.argv[1]);"
        "process.stdout.write(JSON.stringify(api.buildWebsiteJsonLd()));"
    )
    legacy_payload = None
    try:
        completed = subprocess.run(
            ["node", "-e", probe, str(legacy_script)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
        if completed.returncode != 0:
            errors.append(f"legacy-js-execution:{completed.stderr.strip()[:160]}")
        else:
            legacy_payload = json.loads(completed.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        errors.append(f"legacy-js-execution:{type(exc).__name__}")

    if isinstance(legacy_payload, dict):
        legacy_graph = legacy_payload.get("@graph", [])
        if not isinstance(legacy_graph, list):
            errors.append("legacy-js-graph")
            legacy_graph = []
        definitions = {
            node.get("@id"): node
            for node in legacy_graph
            if isinstance(node, dict) and isinstance(node.get("@id"), str)
        }
        allowed_definitions = {WEBSITE_ID, f"{SITE}#archivo"}
        if set(definitions) != allowed_definitions:
            errors.append(f"legacy-js-definitions:{sorted(definitions)}")
        legacy_website = definitions.get(WEBSITE_ID, {})
        legacy_archive = definitions.get(f"{SITE}#archivo", {})
        if legacy_website.get("name") != WEBSITE_NAME:
            errors.append("legacy-js-website-name")
        if legacy_website.get("publisher") != {"@id": ARTIST_ID}:
            errors.append("legacy-js-website-publisher")
        if ref_ids(legacy_website.get("about")) != expected_about:
            errors.append("legacy-js-website-about")
        if legacy_archive.get("creator") != {"@id": ARTIST_ID} or legacy_archive.get("publisher") != {"@id": ARTIST_ID}:
            errors.append("legacy-js-archive-authorship")
        if ref_ids(legacy_archive.get("about")) != expected_about:
            errors.append("legacy-js-archive-about")
        forbidden_refs = {
            "https://lse6.com/#organization",
            "https://lse6.com/#person",
            "https://lse6.com/#law",
            "https://lse6.com/#website",
        }
        collisions = ref_ids(legacy_payload) & forbidden_refs
        if collisions:
            errors.append(f"legacy-js-retired-ids:{sorted(collisions)}")

    if errors:
        fail("Contrato artista/marca/sistema inválido: " + " | ".join(errors[:30]))
    else:
        ok("Entidad única: artista, marca y sistema se referencian por IDs canónicos sin colisiones")


def check_canonical_context_contract() -> None:
    errors: list[str] = []
    context_path = ROOT / "lse6-context.json"
    try:
        context = json.loads(context_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Contexto canónico ilegible: {exc}")
        return

    frame = context.get("canonical_initial_frame", "").strip()
    updated = context.get("updated", "").strip()
    if not frame:
        errors.append("canonical_initial_frame-vacío")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", updated):
        errors.append("updated-inválido")

    soup = BeautifulSoup((ROOT / "index.html").read_text(encoding="utf-8-sig"), "html.parser")
    frame_meta = soup.find("meta", attrs={"name": "LSE6_CANONICAL_INITIAL_FRAME"})
    if not frame_meta or frame_meta.get("content", "").strip() != frame:
        errors.append("index-meta-frame")
    context_link = soup.find("link", href="./lse6-context.json")
    if not context_link or "alternate" not in (context_link.get("rel") or []):
        errors.append("index-context-link")
    prologue = soup.select_one('[data-lse6-perception-canon="true"]')
    normalize = lambda value: " ".join(value.split())
    if not prologue or normalize(frame) not in normalize(prologue.get_text(" ", strip=True)):
        errors.append("index-visible-frame")

    llms = (ROOT / "llms.txt").read_text(encoding="utf-8-sig")
    if frame not in llms:
        errors.append("llms-frame")
    if f"{SITE}lse6-context.json" not in llms:
        errors.append("llms-context-url")

    try:
        sitemap_root = ET.parse(ROOT / "sitemap.xml").getroot()
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        home = next(
            (
                node
                for node in sitemap_root.findall("sm:url", namespace)
                if (node.findtext("sm:loc", default="", namespaces=namespace)).strip() == SITE
            ),
            None,
        )
        lastmod = home.findtext("sm:lastmod", default="", namespaces=namespace).strip() if home is not None else ""
        if lastmod != updated:
            errors.append(f"sitemap-home-lastmod:{lastmod or 'missing'}")
    except (OSError, ET.ParseError) as exc:
        errors.append(f"sitemap-ilegible:{exc}")

    headers = (ROOT / "_headers").read_text(encoding="utf-8-sig")
    if "<https://lse6.org/feed.xml>" not in headers:
        errors.append("headers-rss-link")
    if "<https://web.brid.gy/r/https://lse6.org/>" not in headers:
        errors.append("headers-bridgy-link")
    redirects = (ROOT / "_redirects").read_text(encoding="utf-8-sig")
    for route in ("/.well-known/host-meta", "/.well-known/webfinger", "/.well-known/atproto-did"):
        if route not in redirects:
            errors.append(f"redirect:{route}")

    if errors:
        fail("Contrato de contexto canónico inválido: " + " | ".join(errors))
    else:
        ok("Marco canónico visible y de máquina sincronizado con contexto, sitemap, RSS y Bridgy")


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
    image_children = root.findall(".//image:image/*", ns)
    non_loc_children = [node.tag for node in image_children if not node.tag.endswith("}loc")]
    if non_loc_children:
        fail(f"Image sitemap contiene etiquetas distintas de image:loc: {sorted(set(non_loc_children))}")
    else:
        ok("Image sitemap usa sólo image:loc")
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

    grouped = {}
    for url_node in root.findall("sm:url", ns):
        page = url_node.find("sm:loc", ns)
        if page is not None and page.text:
            grouped[page.text] = {node.text for node in url_node.findall(".//image:loc", ns) if node.text}
    expected_prefixes = {
        "https://lse6.org/evidencia/": "/assets/images/evidencia/",
        "https://lse6.org/error-31-12-69/": "/assets/images/error-31-12-69/",
        "https://lse6.org/remake-666/": "/assets/images/remake-666/",
        "https://lse6.org/rutas-sixtem/": "/assets/images/rutas-sixtem/",
        "https://lse6.org/lseo-sixtem/": "/assets/images/lseo-sixtem/",
    }
    bad_groups = []
    for page, prefix in expected_prefixes.items():
        values = grouped.get(page, set())
        if not values or any(prefix not in value for value in values):
            bad_groups.append(page)
    music_values = grouped.get("https://lse6.org/musica/", set())
    if not music_values or not any("/assets/images/youtube/" in value for value in music_values):
        bad_groups.append("https://lse6.org/musica/")
    if bad_groups:
        fail(f"Asociación temática del image sitemap inválida: {bad_groups}")
    else:
        ok("Image sitemap agrupa evidencia, sistema y música por su puerta temática")

    sitemap = ET.parse(ROOT / "sitemap.xml").getroot()
    page_locs = {node.text for node in sitemap.findall(".//sm:loc", ns) if node.text}
    expected_pages = {
        "https://lse6.org/",
        "https://lse6.org/evidencia/",
        "https://lse6.org/error-31-12-69/",
        "https://lse6.org/remake-666/",
        "https://lse6.org/rutas-sixtem/",
        "https://lse6.org/lseo-sixtem/",
        "https://lse6.org/fuentes/",
        "https://lse6.org/anomalias-temporales/",
        "https://lse6.org/musica/",
        "https://lse6.org/evidence/lse6-expediente-completo.pdf",
    }
    if page_locs != expected_pages:
        fail(f"Contrato del sitemap principal inválido: faltan={sorted(expected_pages - page_locs)} sobran={sorted(page_locs - expected_pages)}")
    else:
        ok("Sitemap principal contiene sólo páginas canónicas y el PDF completo")

    release = json.loads((ROOT / "data/release.json").read_text(encoding="utf-8-sig"))
    lastmods = {
        node.find("sm:loc", ns).text: node.find("sm:lastmod", ns).text
        for node in sitemap.findall("sm:url", ns)
        if node.find("sm:loc", ns) is not None and node.find("sm:lastmod", ns) is not None
    }
    if lastmods.get("https://lse6.org/evidence/lse6-expediente-completo.pdf") != release["pdf_lastmod"]:
        fail("El PDF canónico no conserva su lastmod real")
    elif any(node.find("sm:changefreq", ns) is not None or node.find("sm:priority", ns) is not None for node in sitemap.findall("sm:url", ns)):
        fail("Sitemap principal conserva etiquetas changefreq/priority sin valor operativo")
    else:
        ok("Lastmod del PDF es veraz y el sitemap omite etiquetas ignoradas")

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
    for token in [
        "Content-Security-Policy",
        "X-Content-Type-Options",
        "/tools/*",
        "/data/saltos-temporales/*.csv",
        "/data/saltos-temporales/",
        "/assets/data/*.json",
        "/*.json",
        "/INTEGRITY.sha256",
        "/evidence/lse6-expediente-completo.pdf",
        "/evidence/high-resolution/*.pdf",
        "X-Robots-Tag: noindex, nofollow",
    ]:
        if token not in headers:
            fail(f"_headers no contiene {token}")
    if not any(item.startswith("_headers no contiene") for item in FAILURES):
        ok("Headers de seguridad, caché y previews configurados")

    csv_block = re.search(r"(?ms)^/data/saltos-temporales/\*\.csv\s*$\n(?P<body>(?:^[ \t].*$\n?)*)", headers)
    data_page_block = re.search(r"(?ms)^/data/saltos-temporales/\s*$\n(?P<body>(?:^[ \t].*$\n?)*)", headers)
    if (
        not csv_block
        or "X-Robots-Tag: noindex, nofollow, noarchive, nosnippet" not in csv_block.group("body")
        or not data_page_block
        or "X-Robots-Tag: noindex, nofollow, noarchive, nosnippet" not in data_page_block.group("body")
    ):
        fail("CSV e índice técnico no aplican la mitigación noindex/nofollow completa")
    elif "\n/evidence/*\n" in headers:
        fail("_headers conserva una regla amplia de evidencia que colisiona con el PDF canónico")
    else:
        ok("Superficie técnica reduce descubrimiento sin colisionar con el PDF canónico")

    json_blocks = [
        re.search(r"(?ms)^/\*\.json\s*$\n(?P<body>(?:^[ \t].*$\n?)*)", headers),
        re.search(r"(?ms)^/assets/data/\*\.json\s*$\n(?P<body>(?:^[ \t].*$\n?)*)", headers),
    ]
    if any(
        block is None or "X-Robots-Tag: noindex, nofollow" not in block.group("body")
        for block in json_blocks
    ):
        fail("JSON técnicos no aplican noindex/nofollow de forma consistente")
    else:
        ok("JSON técnicos aplican noindex/nofollow sin contradicciones")

    template = BeautifulSoup((ROOT / "tools/templates/index.template.html").read_text(encoding="utf-8-sig"), "html.parser")
    base = template.find("base", href="/")
    template_bots = [
        template.find("meta", attrs={"name": name})
        for name in ("robots", "googlebot", "bingbot")
    ]
    template_is_noindex = all(
        node
        and {"noindex", "nofollow"}.issubset(
            {token.strip().lower() for token in node.get("content", "").split(",")}
        )
        for node in template_bots
    )
    if base and template_is_noindex:
        ok("Template público resuelve sus rutas desde la raíz y permanece cubierto por noindex")
    elif not template_is_noindex:
        fail("Template técnico públicamente accesible no aplica noindex/nofollow")
    else:
        fail("Template público carece de base raíz para sus referencias relativas")

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
    listed_names = list(listed)
    expected_order = sorted(listed_names, key=lambda name: (name.casefold(), name))
    if listed_names != expected_order:
        fail("INTEGRITY.sha256 no usa orden portable entre Windows y Linux")
    else:
        ok("INTEGRITY.sha256 usa orden portable casefold con desempate exacto")
    mismatches = []
    for name, expected in listed.items():
        path = ROOT / name
        if not path.exists():
            mismatches.append(f"faltante:{name}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            mismatches.append(f"hash:{name}")
    actual_files = {
        p.relative_to(ROOT).as_posix()
        for p in ROOT.rglob("*")
        if p.is_file()
        and p.name != "INTEGRITY.sha256"
        and ".git" not in p.parts
        and "__pycache__" not in p.parts
        and p.suffix.lower() not in {".pyc", ".pyo"}
    }
    unlisted = sorted(actual_files - set(listed))
    if mismatches or unlisted:
        fail(f"Integridad inválida: {mismatches[:8]} no listados={unlisted[:8]}")
    else:
        ok(f"Integridad SHA-256 raw completa ({len(listed)} archivos)")



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
    sha_sums = {}
    for line in (folder / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, filename = line.split("  ", 1)
            sha_sums[filename] = digest
    integrity = {}
    for line in (ROOT / "INTEGRITY.sha256").read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, filename = line.split("  ", 1)
            integrity[filename] = digest
    for index, item in enumerate(files):
        path = folder / item["filename"]
        if not path.exists():
            errors.append(f"faltante:{item['filename']}")
            continue
        if path.stat().st_size >= MAX_BYTES:
            errors.append(f"tamaño:{item['filename']}")
        raw = path.read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if b"\n" in raw and (b"\r\n" not in raw or b"\n" in raw.replace(b"\r\n", b"")):
            errors.append(f"eol-no-crlf:{item['filename']}")
        if actual != item["sha256"]:
            errors.append(f"index-hash:{item['filename']}")
        if actual != sha_sums.get(item["filename"]):
            errors.append(f"sha256sums-hash:{item['filename']}")
        integrity_name = path.relative_to(ROOT).as_posix()
        if actual != integrity.get(integrity_name):
            errors.append(f"integrity-hash:{item['filename']}")
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
    if errors:
        fail("Archivo temporal dividido inválido: " + " | ".join(errors))
    else:
        ok(f"CSV temporal completo en 6 partes ({total_rows:,} registros; index, SHA256SUMS e integridad raw coinciden)")

    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    if "data/saltos-temporales/*.csv -text" in attributes:
        ok("Git preserva exactamente los bytes CRLF canónicos del dataset")
    else:
        fail(".gitattributes no protege los bytes canónicos del dataset")

    bad_gitkeep = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob(".gitkeep")
        if b"\r\n" in path.read_bytes()
    ]
    if bad_gitkeep:
        fail(".gitkeep no canónicos bajo eol=lf: " + ", ".join(bad_gitkeep))
    else:
        ok("Marcadores .gitkeep son estables bajo checkout LF")


def check_release_metadata() -> None:
    release = json.loads((ROOT / "data/release.json").read_text(encoding="utf-8-sig"))
    errors: list[str] = []
    required = {"version", "build_id", "release_time", "release_date", "pdf_lastmod", "state"}
    if not required.issubset(release):
        errors.append("release-fields")

    package = json.loads((ROOT / "package-manifest.json").read_text(encoding="utf-8-sig"))
    for key, release_key in [("version", "version"), ("state", "state"), ("build_id", "build_id"), ("last_build", "release_time")]:
        if package.get(key) != release.get(release_key):
            errors.append(f"package:{key}")

    expected_nodes = {
        "evidencia": f"{SITE}evidencia/",
        "error_31_12_69": f"{SITE}error-31-12-69/",
        "remake_666": f"{SITE}remake-666/",
        "rutas_sixtem": f"{SITE}rutas-sixtem/",
        "lseo_sixtem": f"{SITE}lseo-sixtem/",
        "fuentes": f"{SITE}fuentes/",
        "anomalias_temporales": f"{SITE}anomalias-temporales/",
        "musica": f"{SITE}musica/",
    }
    for relative in ["machine-pulse.json", "data/machine-pulse.json"]:
        pulse = json.loads((ROOT / relative).read_text(encoding="utf-8-sig"))
        for key, release_key in [("version", "version"), ("release_state", "state"), ("build", "build_id"), ("last_build", "release_time")]:
            if pulse.get(key) != release.get(release_key):
                errors.append(f"{relative}:{key}")
        if any(pulse.get("nodes", {}).get(key) != value for key, value in expected_nodes.items()):
            errors.append(f"{relative}:doors")

    image_manifest = json.loads((ROOT / "assets/data/image-manifest.json").read_text(encoding="utf-8-sig"))
    for key, release_key in [("version", "version"), ("state", "state"), ("build_id", "build_id"), ("last_build", "release_time")]:
        if image_manifest.get(key) != release.get(release_key):
            errors.append(f"image-manifest:{key}")

    for relative in ["README.md", "llms.txt"]:
        text = (ROOT / relative).read_text(encoding="utf-8-sig")
        for value in [release.get("version"), release.get("state"), release.get("build_id")]:
            if not value or value not in text:
                errors.append(f"{relative}:{value}")

    generator = (ROOT / "tools/rebuild_release.py").read_text(encoding="utf-8-sig")
    if "if args.refresh_youtube:" not in generator or "sync_youtube_thumbnails()" not in generator:
        errors.append("refresh-flag")
    main_block = generator[generator.index("def main() -> None:"):]
    if main_block.count("sync_youtube_thumbnails()") != 1:
        errors.append("network-default-build")

    if errors:
        fail("Metadatos de release desalineados: " + " | ".join(errors))
    else:
        ok("Release, pulsos, manifiestos y documentación comparten una fuente determinista")

def check_javascript() -> None:
    js_files = [path for path in ROOT.rglob("*.js") if ".git" not in path.parts]
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
    check_canonical_html_pages()
    check_entity_contract()
    check_canonical_context_contract()
    check_local_assets(soup)
    check_sitemaps_and_robots(soup)
    check_center_navigation_contract()
    check_cloudflare_and_encoding()
    check_temporal_csv_archive()
    check_release_metadata()
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
