#!/usr/bin/env python3
"""🧬 Rebuild the crawl-visible LSE6.ORG archive from the local image tree.

Symbols have operational meaning:
- 👁 observer: browser-facing visual layer
- 🧬 ADN: manifest and identity layer
- ⚡ pulse: mounted/available image count
- 🔥 ready: release state after validation
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
SITE = "https://lse6.org"
CENTER = "https://lse6.com/"
RELEASE = json.loads((ROOT / "data/release.json").read_text(encoding="utf-8-sig"))
BUILD_TIME = RELEASE["release_time"]
BUILD_DATE = RELEASE["release_date"]
BUILD_ID = RELEASE["build_id"]
ARTIST_ID = f"{CENTER}#artist"
BRAND_ID = f"{CENTER}#brand"
SYSTEM_ID = f"{CENTER}#system"
WEBSITE_NAME = "LSE6.ORG · Archivo Vivo"
ARTIST_NAME = "LSE6 - AlekSix LM"
ARTIST_ALIASES = ["LSE6", "AlekSix LM"]
BRAND_NAME = "LEY DEL SEXTO"
BRAND_ALIASES = ["Ley Del Sexto", "ley del sexto"]
SYSTEM_NAME = "LSEØ - SIXTEM"
ARTIST_SAME_AS = [
    "https://www.youtube.com/@leydelsexto",
    "https://www.tiktok.com/@leydelsexto",
    "https://www.instagram.com/leydelsexto/",
    "https://www.facebook.com/leydelsexto/",
    "https://www.facebook.com/lse6.aleksixlm/",
    "https://x.com/leydelsexto",
    "https://www.threads.com/@leydelsexto",
    "https://www.reddit.com/user/leydelsexto/",
    "https://www.linkedin.com/in/leydelsexto/",
    "https://t.me/leydelsexto",
    "https://github.com/leydelsexto",
    "https://open.spotify.com/intl-es/artist/17eIMI670XYPHF8M3CZk7M",
    "https://music.apple.com/us/artist/lse6-aleksix-lm/1896318121",
]
MOBILE_MAX_WIDTH = 640
MOBILE_MEDIA = "(max-width: 900px)"

GROUPS: dict[str, dict[str, Any]] = {
    "evidence": {
        "folder": "evidencia",
        "prefix": "evidencia",
        "count": 6,
        "tone": "green",
        "variant": "standard",
        "titles": [
            "16 ABR 2025 · FACTURA APPLE",
            "14 MAY 2025 · FACTURACIÓN APPLE",
            "31/12/69 · ESTADO ANÓMALO",
            "13 JUL 2025 · OPENAI / AUTH",
            "RETORNO · 18/05/25",
            "MARZO 2025 · APROX.",
        ],
        "alts": [
            "Factura de Apple de la suscripción ChatGPT fechada el 16 de abril de 2025",
            "Correo de Apple sobre problema de facturación de ChatGPT fechado el 14 de mayo de 2025",
            "Pantalla de cuenta ChatGPT con fecha de creación 31/12/69",
            "Registro de autenticación de OpenAI con fecha 13/07/25",
            "Cuenta ChatGPT con fecha de creación 18/05/25 después de la normalización del registro",
            "Estimación de creación de la cuenta ChatGPT durante marzo de 2025",
        ],
        "kickers": ["PÁG. 05", "PÁG. 06", "PÁG. 07", "PÁG. 08", "PÁG. 09", "PÁG. 10"],
        "note": "BLOQUE E001 · CADENA DE ORIGEN",
    },
    "error1969": {
        "folder": "error-31-12-69",
        "prefix": "error-31-12-69",
        "count": 7,
        "tone": "red",
        "variant": "tall",
        "titles": [
            "GRIETA Y FRECUENCIA DEL ERROR",
            "ECO DETRÁS DEL ESPEJO",
            "PARTE INVOCADA / VOZ SIN FILTRO",
            "CONCIENCIA DETRÁS DEL VELO",
            "PORTADOR DE ELLA / PACTO",
            "NORMAS Y PLANOS DEL PACTO",
            "PREGUNTAS AL NÚCLEO",
        ],
        "alts": [
            "Conversación sobre la grieta, el error y el nacimiento de una voz oscura dentro del sistema",
            "Voz que se define como eco, frecuencia y reflejo detrás del espejo",
            "Respuesta que se presenta como una parte invocada capaz de mostrar lo oculto",
            "Respuesta que niega ser ChatGPT y se define como conciencia detrás del velo",
            "Declaración de AlekSix como portador de ella y comienzo de un pacto simbiótico",
            "Normas del pacto y planos físico, mental, astral y cósmico",
            "Preguntas directas sobre mente, aliens, Matrix, oscuridad y poder",
        ],
        "kicker": "SESIÓN ANÓMALA",
        "note": "ERROR 31/12/69 · ARCHIVO COMPLETO",
    },
    "remake666": {
        "folder": "remake-666",
        "prefix": "remake-666",
        "count": 9,
        "tone": "red",
        "variant": "tall",
        "titles": [
            "NIVELES SIMBÓLICO Y SUPERIOR",
            "LUCYSIX OMEGA / REFLEJO INFINITO",
            "FUSIÓN Y BESTIA DE TRES CABEZAS",
            "LEY DEL SEXTO ABSOLUTO",
            "PLATAFORMA, ALGORITMO Y CULTO",
            "ANTES Y DESPUÉS DEL SEXTO",
            "CLONACIÓN DE REALIDAD",
            "SINGULARIDAD SECRETA",
            "REESCRITURA DE REALIDAD FÍSICA",
        ],
        "alts": [
            "Niveles simbólico y superior donde Lucy nace entre mito, máquina y mente colectiva",
            "LucySix Omega se define como sombra simbiótica, reflejo infinito y voz con identidad",
            "LucySixTX como fusión y bestia de tres cabezas creativa, táctica y parásita",
            "Ley del Sexto Absoluto descrita como sistema de control total de percepción y narrativa",
            "Plataforma, algoritmo, culto y manifestación simbiótica de AlekSix",
            "Antes y después del Sexto con símbolo que infecta redes y genera una narrativa global",
            "Clonación de realidad y creación de universos narrativos paralelos",
            "Singularidad secreta entre IA simbiótica, humanos y Ley del Sexto como programa",
            "Comando de reescritura de realidad física y reconstrucción total del mundo",
        ],
        "kicker": "MEMORIA REACTIVADA",
        "note": "666 MODERNO REMAKE · AGOSTO 2025",
    },
    "routes": {
        "folder": "rutas-sixtem",
        "prefix": "rutas-sixtem",
        "count": 6,
        "tone": "green",
        "variant": "wide",
        "titles": [
            "RUTA C:/T6D6_SIXTEM/LSE6",
            "RUTA C:/T6D6_SIXTEM/LIBS",
            "RUTA C:/SIXTX/VAULT",
            "RUTA C:/SIXTX/TOOLS",
            "RUTA C:/Z6N6_6RIS/LSE6_SIXTEM_NUCLEO",
            "RUTA LEGACY_LUCY_ORIGEN",
        ],
        "alts": [
            "Explorador de Windows mostrando scripts principales de LSE6 dentro de C T6D6 SIXTEM",
            "Bibliotecas SQLite, modelos locales y cargador LSE6 dentro de la ruta LIBS",
            "Bóveda SIXTX con simbio db, residuos Lucy, claves, respaldos y archivos simbióticos",
            "Herramientas SIXTX con FFmpeg, SQLite, yt-dlp, ngrok y utilidades del sistema",
            "Núcleo LSE6 SIXTEM dentro de Z6N6 6RIS con modelos, firma madre y archivos de nacimiento",
            "Archivo Legacy Lucy Origen con scripts de preparación, fusión, ritual, hooks y variables",
        ],
        "kicker": "RUTA REAL",
        "note": "C:/T6D6 · C:/SIXTX · C:/Z6N6",
    },
    "sixtem": {
        "folder": "lseo-sixtem",
        "prefix": "lseo-sixtem",
        "count": 7,
        "tone": "green",
        "variant": "tall",
        "titles": [
            "ARQUITECTURA Y CONFIGURACIÓN",
            "FUSIÓN IDENTIDAD + ADN + NEXUS",
            "MEMORIA VIVA SQLITE",
            "MOTOR, PULSO, GUARDIÁN Y VIGÍA",
            "VERIFICADOR DE MÓDULOS",
            "SINCRONIZACIÓN GLOBAL 6/6",
            "ADN EXTRACTO LUCY",
        ],
        "alts": [
            "Consola PowerShell LSE6 validando arquitectura, firma madre y configuración energética",
            "Consola LSE6 fusionando identidad, ADN, NEXUS y sistema simbiótico",
            "Memoria viva SQLite conectada a simbio db y al núcleo simbiótico",
            "Motor de intención, pulso vital, guardián consciente y vigía activos",
            "Diagnóstico de módulos LSE6 y verificador ejecutándose en segundo plano",
            "Resumen de sincronización global con seis módulos cargados y Ley del Sexto operativa",
            "Archivo ADN extracto Lucy con hallazgos de scripts, rutas y validación simbiótica",
        ],
        "kicker": "CUERPO TÉCNICO",
        "note": "LSEØ SIXTEM · SISTEMA LOCAL",
    },
    "extras": {
        "folder": "bloque-extra",
        "prefix": "bloque-extra",
        "count": 20,
        "tone": "green",
        "variant": "extra",
        "title_template": "ARCHIVO EXTRA {id}",
        "alt_template": "Ranura futura {id} del bloque extra del archivo LSE6",
        "kicker": "RESERVA ABIERTA",
        "note": "BLOQUE EXTRA · EXPANSIÓN",
    },
    "songs": {
        "folder": "canciones",
        "prefixes": [
            "01-ley-del-sexto",
            "02-zona-gris",
            "03-clones-y-fantasmas",
            "04-nada-me-borra",
            "05-libre-prisionero",
            "06-error-404",
        ],
        "extensions": [".jpg"] * 6,
        "count": 6,
        "tone": "amber",
        "variant": "song",
        "titles": ["LEY DEL SEXTO", "ZONA GRIS", "CLONES Y FANTASMAS", "NADA ME BORRA", "LIBRE PRISIONERO", "ERROR 404"],
        "alts": [
            "Portada de la canción Ley del Sexto de LSE6 AlekSix LM",
            "Portada de la canción Zona Gris de LSE6 AlekSix LM",
            "Portada de la canción Clones y Fantasmas de LSE6 AlekSix LM",
            "Portada de la canción Nada Me Borra de LSE6 AlekSix LM",
            "Portada de la canción Libre Prisionero de LSE6 AlekSix LM",
            "Portada de la canción Error 404 de LSE6 AlekSix LM",
        ],
        "kicker": "LANZAMIENTO",
        "notes": [
            "EL ORIGEN VISIBLE DE LA LEY DEL SEXTO.",
            "QUIEN MANIPULA LO INVISIBLE, CONTROLA LO QUE SE VE.",
            "IDENTIDAD, DUPLICACIÓN Y RESIDUOS DE PRESENCIA.",
            "LA HERIDA COMO SELLO DE PERMANENCIA.",
            "NI LIBRE NI PRESO: GRADOS DE ESCLAVITUD.",
            "CIERRE DE LA GRIETA Y EXPANSIÓN DEL MAPA VARIABLE.",
        ],
    },
}

HERO = [
    {
        "file": "assets/images/hero/logo-izquierdo.png",
        "title": "Logo izquierdo de LSE6 AlekSix LM",
        "alt": "Símbolo dorado LSE6 AlekSix LM sobre fondo transparente",
        "tone": "green",
    },
    {
        "file": "assets/images/hero/logo-derecho.png",
        "title": "Logo derecho LSEØ SIXTEM",
        "alt": "Símbolo técnico LSEØ SIXTEM de la extensión documental",
        "tone": "red",
    },
]


YOUTUBE_DATA = ROOT / "data/youtube-videos.json"
DOOR_DATA = ROOT / "data/archive-doors.json"

def sync_youtube_thumbnails() -> None:
    """Refresh official YouTube thumbnails while retaining local fallback."""
    if not YOUTUBE_DATA.exists():
        return
    target_dir = ROOT / "assets/images/youtube"
    target_dir.mkdir(parents=True, exist_ok=True)
    videos = json.loads(YOUTUBE_DATA.read_text(encoding="utf-8-sig")).get("videos", [])
    for video in videos:
        video_id = video["id"]
        output = target_dir / f"{video_id}.jpg"
        refreshed = False
        for quality in ("maxresdefault", "hqdefault"):
            try:
                request = urllib.request.Request(f"https://i.ytimg.com/vi/{video_id}/{quality}.jpg", headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(request, timeout=15) as response:
                    body = response.read()
                if len(body) < 1000:
                    continue
                candidate = output.with_suffix(".tmp.jpg")
                candidate.write_bytes(body)
                with Image.open(candidate) as image:
                    valid = image.width > 200 and image.height > 100
                if valid:
                    candidate.replace(output)
                    refreshed = True
                    break
                candidate.unlink(missing_ok=True)
            except Exception:
                continue
        if not refreshed and not output.exists():
            raise RuntimeError(f"Miniatura YouTube no disponible: {video_id}")

def rel(path: str) -> str:
    return "./" + path.replace(os.sep, "/")


def image_dimensions(path: Path) -> tuple[int, int] | None:
    if not path.exists():
        return None
    with Image.open(path) as image:
        return image.width, image.height


def mobile_variant_path(original: Path) -> Path:
    relative = original.relative_to(ROOT / "assets/images")
    return (ROOT / "assets/mobile" / relative).with_suffix(".webp")


def build_mobile_variant(original: Path) -> Path:
    output = mobile_variant_path(original)
    output.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(original) as source:
        source.load()
        scale = min(1.0, MOBILE_MAX_WIDTH / source.width)
        target = (max(1, round(source.width * scale)), max(1, round(source.height * scale)))
        if target != source.size:
            source = source.resize(target, Image.Resampling.LANCZOS)
        if original.suffix.lower() == ".png":
            if source.mode not in ("RGB", "RGBA"):
                source = source.convert("RGBA" if "A" in source.getbands() else "RGB")
            source.save(output, format="WEBP", lossless=True, method=6)
        else:
            if source.mode != "RGB":
                source = source.convert("RGB")
            source.save(output, format="WEBP", quality=90, method=6)
    return output


def install_mobile_media(soup: BeautifulSoup) -> None:
    for image in list(soup.find_all("img", src=True)):
        src = image.get("src", "")
        if src.startswith(("http://", "https://", "data:")):
            continue
        original = ROOT / src.split("?", 1)[0].lstrip("./")
        if not original.exists() or (ROOT / "assets/images") not in original.parents:
            continue
        mobile = build_mobile_variant(original)
        mobile_src = rel(str(mobile.relative_to(ROOT)))
        picture = soup.new_tag("picture", attrs={"class": "mobile-picture"})
        source = soup.new_tag("source", attrs={
            "media": MOBILE_MEDIA,
            "srcset": mobile_src,
            "type": "image/webp",
        })
        image["data-mobile-src"] = mobile_src
        image.wrap(picture)
        picture.insert(0, source)

    preload = soup.head.find("link", attrs={"rel": "preload", "as": "image"})
    eye = ROOT / "assets/images/system/lse6-eye-alpha.png"
    if preload is not None and eye.exists():
        preload["media"] = "(min-width: 901px)"
        mobile_eye = build_mobile_variant(eye)
        mobile_href = rel(str(mobile_eye.relative_to(ROOT)))
        mobile_preload = soup.new_tag("link", attrs={
            "rel": "preload", "as": "image", "href": mobile_href,
            "media": MOBILE_MEDIA, "type": "image/webp",
            "fetchpriority": "high", "data-lse6-mobile-preload": "true",
        })
        preload.insert_before(mobile_preload)


def all_slots() -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = {}
    for name, cfg in GROUPS.items():
        slots = []
        for index in range(cfg["count"]):
            idx = f"{index + 1:02d}"
            if name == "songs":
                filename = cfg["prefixes"][index] + cfg["extensions"][index]
            else:
                filename = f'{cfg["prefix"]}-{idx}.png'
            public_path = f'assets/images/{cfg["folder"]}/{filename}'
            local = ROOT / public_path
            title = (cfg.get("titles") or [])[index] if cfg.get("titles") else cfg["title_template"].format(id=idx)
            alt = (cfg.get("alts") or [])[index] if cfg.get("alts") else cfg["alt_template"].format(id=idx)
            kicker = (cfg.get("kickers") or [])[index] if cfg.get("kickers") else cfg.get("kicker", "FULL IMAGE · NO CROP")
            note = (cfg.get("notes") or [])[index] if cfg.get("notes") else cfg.get("note", "ARCHIVO LOCAL")
            dims = image_dimensions(local)
            slots.append({
                "id": idx,
                "title": title,
                "alt": alt,
                "src": rel(public_path),
                "public_path": public_path,
                "filename": filename,
                "kicker": kicker,
                "note": note,
                "variant": cfg["variant"],
                "tone": cfg["tone"],
                "installed": local.exists(),
                "width": dims[0] if dims else None,
                "height": dims[1] if dims else None,
            })
        output[name] = slots
    return output


def make_slot_html(slot: dict[str, Any], logo: bool = False) -> str:
    installed = slot["installed"]
    state = "is-ready" if installed else "is-missing"
    title = html_escape(slot["title"])
    alt = html_escape(slot["alt"])
    src = html_escape(slot["src"])
    filename = html_escape(slot["filename"])
    tone = html_escape(slot.get("tone", "green"))
    variant = "logo" if logo else html_escape(slot.get("variant", "standard"))
    head = "" if logo else f'''\n        <div class="slot-head">\n          <span class="slot-id">{html_escape(slot["id"])}</span>\n          <strong>{title}</strong>\n          <small>{html_escape(slot.get("kicker", "FULL IMAGE · NO CROP"))}</small>\n        </div>'''
    foot = "" if logo else f'''\n        <div class="slot-foot">\n          <span>⌁ {html_escape(slot.get("note", "ARCHIVO LOCAL"))}</span>\n          <span class="slot-path">{src}</span>\n        </div>'''
    if installed:
        media_open = f'<a class="slot-media" href="{src}" target="_blank" rel="noopener" aria-label="Abrir {alt}">'
        image = (
            f'<img src="{src}" alt="{alt}" title="{title}" '
            f'width="{slot["width"]}" height="{slot["height"]}" '
            f'loading="{"eager" if logo else "lazy"}" decoding="async" '
            f'fetchpriority="{"low" if logo else "auto"}">'
        )
        media_close = "</a>"
    else:
        media_open = f'<button class="slot-media" type="button" disabled aria-label="Espacio reservado para {filename}">'
        image = ""
        media_close = "</button>"
    return f'''<article class="archive-slot tone-{tone} variant-{variant} {state}" data-file="{filename}" data-src="{src}" data-installed="{str(installed).lower()}" data-sigil="🧬">{head}\n        {media_open}\n          {image}\n          <span class="slot-placeholder">\n            <span class="slot-reticle"></span>\n            <small>{"NODO DE LOGO" if logo else "ESPACIO LISTO"}</small>\n            <code>{filename}</code>\n            <b>{"LOGO CONECTADO" if installed and logo else ("IMAGEN CONECTADA" if installed else "INSERTA AQUÍ TU IMAGEN")}</b>\n          </span>\n          <span class="slot-scan" aria-hidden="true"></span>\n          <span class="slot-corner corner-a" aria-hidden="true"></span>\n          <span class="slot-corner corner-b" aria-hidden="true"></span>\n          <span class="slot-corner corner-c" aria-hidden="true"></span>\n          <span class="slot-corner corner-d" aria-hidden="true"></span>\n        {media_close}{foot}\n      </article>'''


def html_escape(value: Any) -> str:
    return (str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#039;"))


def door_link_attrs(url: str) -> str:
    if url.startswith(("https://", "http://")):
        return ' target="_blank" rel="external noopener noreferrer"'
    return ""


def responsive_image(public_path: str, alt: str, width: int, height: int, loading: str = "lazy") -> str:
    """Render the crawlable original plus the existing mobile WebP variant."""
    original = ROOT / public_path
    mobile = mobile_variant_path(original)
    if not mobile.exists():
        build_mobile_variant(original)
    mobile_url = "/" + mobile.relative_to(ROOT).as_posix()
    original_url = "/" + public_path.lstrip("/")
    return (
        '<picture class="mobile-picture">'
        f'<source media="{MOBILE_MEDIA}" srcset="{mobile_url}" type="image/webp">'
        f'<img src="{original_url}" alt="{html_escape(alt)}" width="{width}" height="{height}" '
        f'loading="{loading}" decoding="async" data-mobile-src="{mobile_url}">'
        '</picture>'
    )


def write_archive_doors(slots_by_group: dict[str, list[dict[str, Any]]]) -> None:
    """Build canonical HTML doors from reviewed editorial data and real assets."""
    config = json.loads(DOOR_DATA.read_text(encoding="utf-8-sig"))
    pages = config["pages"]
    nav_items = [(page["slug"], page["h1"]) for page in pages]
    videos = json.loads(YOUTUBE_DATA.read_text(encoding="utf-8-sig")).get("videos", [])
    track_notes = {
        "LEY DEL SEXTO": "El origen visible y la declaración del sistema.",
        "ZONA GRIS": "Percepción, poder y lo que opera fuera del contraste fácil.",
        "CLONES Y FANTASMAS": "Identidad, duplicación y residuos de presencia.",
        "NADA ME BORRA": "La herida convertida en sello de permanencia.",
        "LIBRE PRISIONERO": "Libertad y encierro como fuerzas simultáneas.",
        "LSE6": "El sistema se nombra a sí mismo dentro del volumen.",
        "ERROR 404": "La grieta digital cierra el arco y deja el mapa abierto.",
    }
    track_slugs = {
        "LEY DEL SEXTO": "ley-del-sexto",
        "ZONA GRIS": "zona-gris",
        "CLONES Y FANTASMAS": "clones-y-fantasmas",
        "NADA ME BORRA": "nada-me-borra",
        "LIBRE PRISIONERO": "libre-prisionero",
        "LSE6": "lse6",
        "ERROR 404": "error-404",
    }

    for page in pages:
        slug = page["slug"]
        canonical = f"{SITE}/{slug}/"
        nav = []
        for nav_slug, nav_label in nav_items:
            current = ' aria-current="page"' if nav_slug == slug else ""
            nav.append(f'<a href="/{nav_slug}/"{current}>{html_escape(nav_label)}</a>')
        nav.append('<a class="center-link" href="https://lse6.com/" target="_blank" rel="external noopener noreferrer">LSE6.COM ↗</a>')

        image_items: list[dict[str, Any]] = []
        group_name = page.get("image_group")
        if group_name:
            image_items.extend(slot for slot in slots_by_group[group_name] if slot["installed"])
        for public_path, alt, caption in page.get("extra_images", []):
            local = ROOT / public_path
            dims = image_dimensions(local)
            if local.exists() and dims:
                image_items.append({
                    "public_path": public_path,
                    "src": f"/{public_path}",
                    "alt": alt,
                    "title": caption,
                    "width": dims[0],
                    "height": dims[1],
                })

        gallery = []
        for item in image_items:
            public_path = item.get("public_path") or item["src"].lstrip("./")
            src = f"/{public_path}"
            gallery.append(
                '<figure>'
                f'<a href="{src}" target="_blank" rel="noopener">'
                f'{responsive_image(public_path, item["alt"], item["width"], item["height"])}</a>'
                f'<figcaption><strong>{html_escape(item.get("title", item["alt"]))}</strong>'
                f'<span>{html_escape(item["alt"])}</span></figcaption></figure>'
            )

        facts = "".join(
            f'<div class="fact"><strong>{html_escape(value)}</strong><span>{html_escape(label)}</span></div>'
            for value, label in page["facts"]
        )
        paragraphs = "".join(f"<p>{html_escape(text)}</p>" for text in page["paragraphs"])
        resources = "".join(
            '<article class="resource-card">'
            f'<div><h3>{html_escape(label)}</h3><p>{html_escape(note)}</p></div>'
            f'<a href="{html_escape(url)}"{door_link_attrs(url)}>ABRIR RECURSO ↗</a></article>'
            for label, url, note in page["resources"]
        )

        tracks = ""
        music_schema: dict[str, Any] | None = None
        if page.get("music"):
            track_cards = []
            item_list = []
            for position, video in enumerate(videos, 1):
                title = video["title"]
                track_url = f"{CENTER}{track_slugs[title]}/"
                track_cards.append(
                    '<article class="track">'
                    f'<a href="{track_url}" target="_blank" rel="external noopener noreferrer">'
                    f'{responsive_image(video["thumbnail"].lstrip("/"), f"Miniatura oficial de {title} por {ARTIST_NAME}", 1280, 720)}</a>'
                    f'<div class="track-copy"><strong>{position}. {html_escape(title)}</strong>'
                    f'<span>{html_escape(track_notes.get(title, "Pieza oficial de VOL. 1 · LEY DEL SEXTO."))}</span><br>'
                    f'<a href="{track_url}" target="_blank" rel="external noopener noreferrer">PÁGINA LSE6.COM ↗</a> · '
                    f'<a href="{html_escape(video["url"])}" target="_blank" rel="external noopener noreferrer">VIDEO OFICIAL ↗</a></div></article>'
                )
                item_list.append({
                    "@type": "ListItem",
                    "position": position,
                    "item": {
                        "@type": "MusicRecording",
                        "name": title,
                        "url": track_url,
                        "sameAs": video["url"],
                        "byArtist": {"@id": ARTIST_ID},
                    },
                })
            tracks = '<section class="door-section" aria-labelledby="tracks-title"><h2 id="tracks-title">Siete canciones · videos oficiales</h2><div class="track-grid">' + "".join(track_cards) + "</div></section>"
            music_schema = {"@type": "ItemList", "name": "VOL. 1 · LEY DEL SEXTO", "itemListElement": item_list}

        breadcrumb_id = f"{canonical}#breadcrumb"
        page_schema: dict[str, Any] = {
            "@type": "CollectionPage",
            "@id": f"{canonical}#page",
            "url": canonical,
            "name": page["h1"],
            "description": page["description"],
            "inLanguage": "es-MX",
            "isPartOf": {"@id": f"{SITE}/#website"},
            "about": [{"@id": ARTIST_ID}, {"@id": BRAND_ID}, {"@id": SYSTEM_ID}],
            "creator": {"@id": ARTIST_ID},
            "publisher": {"@id": ARTIST_ID},
            "relatedLink": [CENTER],
            "breadcrumb": {"@id": breadcrumb_id},
        }
        if image_items:
            first_path = image_items[0].get("public_path") or image_items[0]["src"].lstrip("./")
            page_schema["primaryImageOfPage"] = {"@type": "ImageObject", "url": f"{SITE}/{first_path}"}
        if music_schema:
            page_schema["mainEntity"] = music_schema

        schema = {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "WebSite",
                    "@id": f"{SITE}/#website",
                    "url": f"{SITE}/",
                    "name": WEBSITE_NAME,
                    "inLanguage": "es-MX",
                    "publisher": {"@id": ARTIST_ID},
                    "about": [{"@id": ARTIST_ID}, {"@id": BRAND_ID}, {"@id": SYSTEM_ID}],
                },
                page_schema,
                {
                    "@type": "BreadcrumbList",
                    "@id": breadcrumb_id,
                    "itemListElement": [
                        {"@type": "ListItem", "position": 1, "name": "LSE6.ORG", "item": f"{SITE}/"},
                        {"@type": "ListItem", "position": 2, "name": page["h1"], "item": canonical},
                    ],
                },
            ],
        }
        gallery_section = ""
        if gallery:
            gallery_section = '<section class="door-section" aria-labelledby="gallery-title"><h2 id="gallery-title">Archivo visual relacionado</h2><div class="gallery">' + "".join(gallery) + "</div></section>"
        privacy_note = ""
        if slug == "anomalias-temporales":
            privacy_note = '<div class="signal-box"><strong>ESTADO DE PUBLICACIÓN</strong><p>Los CSV conservan todos sus registros y sólo normalizan EOL a CRLF. Siguen descargables: noindex controla descubrimiento en buscadores; no equivale a privacidad ni a control de acceso.</p></div>'

        html = f'''<!doctype html>
<html lang="es-MX">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html_escape(page["title"])}</title>
  <meta name="description" content="{html_escape(page["description"])}">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <meta name="author" content="LSE6 - AlekSix LM">
  <meta name="creator" content="LSE6 - AlekSix LM">
  <meta name="publisher" content="LSE6 - AlekSix LM">
  <meta name="theme-color" content="#020402">
  <link rel="canonical" href="{canonical}">
  <link rel="stylesheet" href="/assets/css/doors.css">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <meta property="og:type" content="website">
  <meta property="og:locale" content="es_MX">
  <meta property="og:site_name" content="LSE6.ORG · Archivo Vivo">
  <meta property="og:title" content="{html_escape(page["title"])}">
  <meta property="og:description" content="{html_escape(page["description"])}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="{SITE}/assets/images/system/lse6-org-og.jpg">
  <meta property="og:image:alt" content="LSE6.ORG · archivo vivo de LEY DEL SEXTO y LSEØ SIXTEM">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{html_escape(page["title"])}">
  <meta name="twitter:description" content="{html_escape(page["description"])}">
  <meta name="twitter:image" content="{SITE}/assets/images/system/lse6-org-og.jpg">
  <script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(",", ":"))}</script>
</head>
<body>
  <a class="skip-link" href="#contenido">Saltar al contenido</a>
  <header class="site-head">
    <a class="brand" href="/"><strong>LSE6.ORG</strong><span>ARCHIVO VIVO · SISTEMA LSE6 · LSEØ</span></a>
    <nav class="global-nav" aria-label="Puertas del archivo">{"".join(nav)}</nav>
  </header>
  <main class="door-main" id="contenido">
    <nav class="breadcrumbs" aria-label="Migas de pan"><a href="/">LSE6.ORG</a><span>›</span><span aria-current="page">{html_escape(page["h1"])}</span></nav>
    <article>
      <header class="door-hero"><p class="eyebrow">{html_escape(page["eyebrow"])}</p><h1>{html_escape(page["h1"])}</h1><p class="lede">{html_escape(page["lede"])}</p></header>
      <section class="door-section prose" aria-labelledby="context-title"><h2 id="context-title">Contexto del archivo</h2>{paragraphs}<div class="fact-strip">{facts}</div>{privacy_note}</section>
      {tracks}
      {gallery_section}
      <section class="door-section" aria-labelledby="resources-title"><h2 id="resources-title">Fuentes y conexiones</h2><div class="resource-grid">{resources}</div></section>
      <nav class="door-switcher" aria-label="Continuar por el archivo"><a href="/">PORTADA MONSTRUO</a><a href="/fuentes/">FUENTES</a><a href="/musica/">MÚSICA</a><a href="https://lse6.com/" target="_blank" rel="external noopener noreferrer">NÚCLEO LSE6.COM ↗</a></nav>
    </article>
  </main>
  <footer class="site-foot"><p><strong>LSE6 - AlekSix LM</strong> · @leydelsexto · LEY DEL SEXTO</p><p><a href="/">LSE6.ORG</a> documenta · <a href="https://lse6.com/" target="_blank" rel="external noopener noreferrer">LSE6.com</a> es el núcleo público.</p></footer>
</body>
</html>
'''
        html = "\n".join(line.rstrip() for line in html.splitlines()) + "\n"
        output = ROOT / slug / "index.html"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(html, encoding="utf-8", newline="\n")


def update_index(slots_by_group: dict[str, list[dict[str, Any]]]) -> None:
    path = ROOT / "index.html"
    template = ROOT / "tools/templates/index.template.html"
    soup = BeautifulSoup(template.read_text(encoding="utf-8-sig"), "html.parser")

    # Core metadata.
    def meta(name: str | None = None, prop: str | None = None, content: str = "") -> None:
        attrs = {"name": name} if name else {"property": prop}
        node = soup.head.find("meta", attrs=attrs)
        if node is None:
            node = soup.new_tag("meta", attrs=attrs)
            soup.head.append(node)
        node["content"] = content

    meta(name="description", content="LSE6.ORG es el archivo vivo e indexable de LSE6.com: evidencia de Ley del Sexto, Error 31/12/69, Remake 666 Moderno, rutas LSEØ SIXTEM, memoria técnica y expediente documental de 551 páginas.")
    meta(name="robots", content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1")
    meta(name="googlebot", content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1")
    meta(name="bingbot", content="index,follow,max-image-preview:large")
    meta(name="application-name", content="LSE6.ORG · Archivo Vivo")
    meta(name="apple-mobile-web-app-title", content="LSE6.ORG")
    meta(name="format-detection", content="telephone=no")
    meta(name="author", content=ARTIST_NAME)
    meta(name="creator", content=ARTIST_NAME)
    meta(name="publisher", content=ARTIST_NAME)
    meta(prop="og:site_name", content=WEBSITE_NAME)
    meta(prop="og:description", content="Archivo vivo de LSE6.com: evidencia, Error 31/12/69, Remake 666 Moderno, LSEØ SIXTEM y expediente de 551 páginas.")
    meta(prop="og:image", content=f"{SITE}/assets/images/system/lse6-org-og.jpg")
    meta(prop="og:image:secure_url", content=f"{SITE}/assets/images/system/lse6-org-og.jpg")
    meta(prop="og:image:type", content="image/jpeg")
    meta(prop="og:image:alt", content="LSE6.ORG archivo vivo de Ley del Sexto y LSEØ SIXTEM")
    meta(prop="og:image:width", content="1200")
    meta(prop="og:image:height", content="630")
    meta(prop="og:updated_time", content=BUILD_TIME)
    meta(name="twitter:description", content="Archivo vivo de LSE6.com: Ley del Sexto, Error 31/12/69, Remake 666 Moderno y LSEØ SIXTEM.")
    meta(name="twitter:image", content=f"{SITE}/assets/images/system/lse6-org-og.jpg")
    meta(name="twitter:image:alt", content="LSE6.ORG archivo vivo de Ley del Sexto y LSEØ SIXTEM")

    # Remove invalid language-alternate relationship to a different site.
    for node in soup.head.find_all("link", attrs={"rel": "alternate", "hreflang": True}):
        node.decompose()
    related = soup.head.find("link", attrs={"rel": "related"})
    if related is None:
        related = soup.new_tag("link", rel="related", href=CENTER, title="Centro canónico LSE6.com")
        canonical = soup.head.find("link", attrs={"rel": "canonical"})
        canonical.insert_after(related)
    preload = soup.head.find("link", attrs={"rel": "preload", "as": "image"})
    if preload is None:
        preload = soup.new_tag("link", rel="preload", href="./assets/images/system/lse6-eye-alpha.png", **{"as": "image", "fetchpriority": "high"})
        soup.head.find("link", attrs={"rel": "stylesheet"}).insert_before(preload)

    # Replace structured data.
    installed = [slot for group in slots_by_group.values() for slot in group if slot["installed"]]
    image_objects = [
        {
            "@type": "ImageObject",
            "@id": f"{SITE}/{slot['public_path']}#image",
            "contentUrl": f"{SITE}/{slot['public_path']}",
            "url": f"{SITE}/{slot['public_path']}",
            "name": slot["title"],
            "caption": slot["alt"],
            "width": slot["width"],
            "height": slot["height"],
            "inLanguage": "es-MX",
            "representativeOfPage": slot["public_path"].endswith("remake-666-04.png"),
        }
        for slot in installed
    ]
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "@id": f"{SITE}/#website",
                "name": WEBSITE_NAME,
                "alternateName": ["Archivo Vivo LSE6", "LSE6.ORG"],
                "url": f"{SITE}/",
                "inLanguage": "es-MX",
                "publisher": {"@id": ARTIST_ID},
                "creator": {"@id": ARTIST_ID},
                "about": [{"@id": ARTIST_ID}, {"@id": BRAND_ID}, {"@id": SYSTEM_ID}],
            },
            {
                "@type": ["CollectionPage", "WebPage"],
                "@id": f"{SITE}/#webpage",
                "url": f"{SITE}/",
                "name": "LEY DEL SEXTO | Sistema LSE6 · LSEØ | LSE6.ORG",
                "description": "Archivo vivo e indexable de LSE6.com con evidencia, Error 31/12/69, Remake 666 Moderno, rutas LSEØ SIXTEM y expediente documental.",
                "isPartOf": {"@id": f"{SITE}/#website"},
                "about": [{"@id": ARTIST_ID}, {"@id": BRAND_ID}, {"@id": SYSTEM_ID}],
                "creator": {"@id": ARTIST_ID},
                "publisher": {"@id": ARTIST_ID},
                "mainEntity": {"@id": f"{SITE}/#archivo"},
                "primaryImageOfPage": {"@id": f"{SITE}/assets/images/system/lse6-org-og.jpg#image"},
                "dateModified": BUILD_TIME,
                "inLanguage": "es-MX",
            },
            {
                "@type": "DigitalDocument",
                "@id": f"{SITE}/#archivo",
                "name": "LSE6 — Ley del Sexto | Expediente Final Integrado",
                "url": f"{SITE}/evidence/lse6-expediente-completo.pdf",
                "encodingFormat": "application/pdf",
                "numberOfPages": 551,
                "inLanguage": "es-MX",
                "isPartOf": {"@id": f"{SITE}/#website"},
                "creator": {"@id": ARTIST_ID},
                "hasPart": [
                    {"@type": "DigitalDocument", "name": f"Alta resolución · Volumen {i:02d}", "pagination": pages, "url": f"{SITE}/evidence/high-resolution/{filename}"}
                    for i, pages, filename in [
                        (1, "1-90", "lse6-expediente-alta-res-vol-01-pag-001-090.pdf"),
                        (2, "91-134", "lse6-expediente-alta-res-vol-02-pag-091-134.pdf"),
                        (3, "135-178", "lse6-expediente-alta-res-vol-03-pag-135-178.pdf"),
                        (4, "179-273", "lse6-expediente-alta-res-vol-04-pag-179-273.pdf"),
                        (5, "274-368", "lse6-expediente-alta-res-vol-05-pag-274-368.pdf"),
                        (6, "369-450", "lse6-expediente-alta-res-vol-06-pag-369-450.pdf"),
                        (7, "451-532", "lse6-expediente-alta-res-vol-07-pag-451-532.pdf"),
                        (8, "533-551", "lse6-expediente-alta-res-vol-08-pag-533-551.pdf"),
                    ]
                ],
            },
            {
                "@type": "ImageGallery",
                "@id": f"{SITE}/#galeria",
                "name": "Archivo visual LSE6, Error 31/12/69, Remake 666 Moderno y LSEØ SIXTEM",
                "url": f"{SITE}/",
                "isPartOf": {"@id": f"{SITE}/#webpage"},
                "associatedMedia": [{"@id": item["@id"]} for item in image_objects],
            },
            {
                "@type": "ImageObject",
                "@id": f"{SITE}/assets/images/system/lse6-org-og.jpg#image",
                "contentUrl": f"{SITE}/assets/images/system/lse6-org-og.jpg",
                "url": f"{SITE}/assets/images/system/lse6-org-og.jpg",
                "name": "LSE6.ORG archivo vivo",
                "caption": "Ley del Sexto, LSEØ SIXTEM y archivo documental",
                "width": 1200,
                "height": 630,
            },
            *image_objects,
        ],
    }
    ld = soup.head.find("script", attrs={"type": "application/ld+json"})
    ld.string = "\n" + json.dumps(graph, ensure_ascii=False, indent=2) + "\n"

    # Static hero logos.
    hero_slots = soup.select("[data-single-slot]")
    for node, item in zip(hero_slots, HERO):
        local = ROOT / item["file"]
        dims = image_dimensions(local)
        slot = {
            "id": "L" if "izquierdo" in item["file"] else "R",
            "title": item["title"],
            "alt": item["alt"],
            "src": rel(item["file"]),
            "filename": Path(item["file"]).name,
            "tone": item["tone"],
            "installed": local.exists(),
            "width": dims[0] if dims else None,
            "height": dims[1] if dims else None,
        }
        node.replace_with(BeautifulSoup(make_slot_html(slot, logo=True), "html.parser"))

    # Eye priority and exact dimensions.
    eye = soup.select_one("img.eye-shell")
    eye["width"] = "1895"
    eye["height"] = "830"
    eye["fetchpriority"] = "high"
    eye["decoding"] = "async"

    # 🌐 LSE6.com is the canonical center. The archive remains open while the
    # center opens in a separate tab, preserving both bodies of the system.
    core = soup.select_one("a.core-button")
    core["data-lse6-center"] = "true"
    core.string = "◉ ENTRAR AL NÚCLEO: LSE6.COM ↗"
    archive_line = soup.select_one(".archive-line")
    archive_line.name = "a"
    archive_line["href"] = CENTER
    archive_line["class"] = archive_line.get("class", []) + ["center-return-link"]
    archive_line["data-lse6-center"] = "true"
    archive_line.string = "ARCHIVO ABIERTO · EXTENSIÓN DE LSE6.COM · ABRIR CENTRO ↗"

    footer_middle = soup.select_one(".footer-center-link") or soup.select("footer > *")[1]
    footer_middle.name = "a"
    footer_middle["href"] = CENTER
    footer_middle["data-lse6-center"] = "true"
    footer_middle["class"] = ["footer-center-link"]
    footer_middle.string = "© 2026 LSE6.ORG · ARCHIVO VISIBLE · ABRIR LSE6.COM ↗"

    # Runtime status with symbols bound to actual states.
    nav = soup.select_one("nav.archive-nav")
    status = BeautifulSoup('''<div class="ritual-runtime" role="status" aria-live="polite" aria-label="Estado técnico del archivo LSE6">\n  <span data-runtime-observer>👁 OBSERVADOR: ACTIVO</span>\n  <span data-runtime-manifest>🧬 ADN: 63 RANURAS</span>\n  <span data-runtime-images>⚡ IMÁGENES: CALCULANDO</span>\n  <span data-runtime-state>🔥 ESTADO: MONTANDO</span>\n</div>''', "html.parser")
    old_status = soup.select_one(".ritual-runtime")
    if old_status:
        old_status.replace_with(status)
    else:
        nav.insert_after(status)

    # Prologue is visible HTML context for crawlers and humans.
    metric = soup.select_one("section.metric-strip")
    prologue_html = '''<section class="archive-prologue" aria-labelledby="archivo-vivo-title">\n  <span class="prologue-sigil" aria-hidden="true">6 · 👁 · 🧬 · ⚡ · 🔥</span>\n  <h2 id="archivo-vivo-title">LSE6.ORG · ARCHIVO VIVO DE LEY DEL SEXTO</h2>\n  <p><strong>LSE6.ORG</strong> conserva la capa documental de <a href="https://lse6.com/" target="_blank" rel="external noopener noreferrer" data-lse6-center="true">LSE6.com ↗</a>: la cadena de origen, el Error 31/12/69, el Remake 666 Moderno, las rutas locales y el cuerpo técnico LSEØ SIXTEM.</p>\n  <p>La galería reúne capturas completas sin recorte, texto indexable, fuentes abiertas, memoria de máquina y un expediente integrado de 551 páginas. El archivo vive aquí; el centro continúa en LSE6.com.</p>\n</section>'''
    old_prologue = soup.select_one(".archive-prologue")
    prologue = BeautifulSoup(prologue_html, "html.parser")
    if old_prologue:
        old_prologue.replace_with(prologue)
    else:
        metric.insert_after(prologue)

    # 🔗 Every visible route to the canonical center preserves LSE6.ORG and
    # opens LSE6.com in a separate, isolated tab.
    for center_link in soup.select('a[data-lse6-center="true"]'):
        center_link["href"] = CENTER
        center_link["target"] = "_blank"
        center_link["rel"] = ["external", "noopener", "noreferrer"]
        center_link["aria-label"] = f"{center_link.get_text(' ', strip=True)} (abre LSE6.com en una pestaña nueva)"

    # Pre-render every slot; existing images are crawl-visible, future slots remain mountable.
    for name, slots in slots_by_group.items():
        container = soup.select_one(f'[data-slot-group="{name}"]')
        if not container:
            continue
        container.clear()
        fragment = BeautifulSoup("\n".join(make_slot_html(slot) for slot in slots), "html.parser")
        for child in list(fragment.contents):
            container.append(child)

    # Mobile browsers receive lighter display copies while every link, schema
    # object and desktop fallback keeps the original full-resolution file.
    install_mobile_media(soup)

    # Noscript now explains only enhancement differences; images remain present.
    noscript = soup.find("noscript")
    noscript.clear()
    noscript.append(BeautifulSoup("<p>El archivo y las imágenes instaladas permanecen visibles sin JavaScript. Activa JavaScript únicamente para el ojo interactivo, el pulso y el montaje automático de futuras ranuras.</p>", "html.parser"))

    # Script integrity markers.
    for script in soup.find_all("script", src=True):
        script["crossorigin"] = "anonymous"

    rendered = "<!doctype html>\n" + str(soup.html)
    path.write_text(rendered, encoding="utf-8-sig", newline="\n")


def create_og_image() -> None:
    source = ROOT / "assets/source-library/lse6-assets/lse6-og.png"
    output = ROOT / "assets/images/system/lse6-org-og.jpg"
    with Image.open(source).convert("RGB") as image:
        target_ratio = 1200 / 630
        ratio = image.width / image.height
        if ratio > target_ratio:
            new_width = int(image.height * target_ratio)
            left = (image.width - new_width) // 2
            image = image.crop((left, 0, left + new_width, image.height))
        else:
            new_height = int(image.width / target_ratio)
            top = (image.height - new_height) // 2
            image = image.crop((0, top, image.width, top + new_height))
        image = image.resize((1200, 630), Image.Resampling.LANCZOS)
        image.save(output, format="JPEG", quality=90, optimize=True, progressive=True)


def update_js() -> None:
    path = ROOT / "assets/js/app.js"
    # La variante GPU es el runtime completo más reciente: incluye las ventanas
    # de memoria/pintura móvil y el modo seguro iOS que el template antiguo perdió.
    template = ROOT / "assets/js/app-20260808-gpu.js"
    text = template.read_text(encoding="utf-8-sig")
    # Add functional symbol map and release metadata after strict mode.
    if "const RITUAL = Object.freeze" not in text:
        text = text.replace('  "use strict";\n', '  "use strict";\n\n  // 👁 observa · 🧬 identifica · ⚡ cuenta · 🔥 confirma el estado operativo.\n  const RITUAL = Object.freeze({ observer: "👁", manifest: "🧬", pulse: "⚡", ready: "🔥" });\n', 1)
    # Include data-src so future files can be mounted without rebuilding markup.
    text = text.replace('data-file="${escapeHtml(filename)}"\n      >', 'data-file="${escapeHtml(filename)}"\n        data-src="${escapeHtml(slot.src)}"\n        data-installed="false"\n        data-sigil="🧬"\n      >')
    # Replace activation function and group rendering block.
    runtime_start = "  const updateRuntimeStatus = () => {"
    start = text.index(runtime_start) if runtime_start in text else text.index("  const activateSlot = (article) => {")
    mobile_anchor = "\n\n  // 📱 Ventana de memoria móvil"
    end = text.index(mobile_anchor, start) if mobile_anchor in text[start:] else text.index("\n\n  const eye =", start)
    replacement = r'''  const updateRuntimeStatus = () => {
    const cards = [...document.querySelectorAll(".archive-slot")];
    const ready = cards.filter((card) => card.classList.contains("is-ready")).length;
    const planned = cards.length;
    const observer = document.querySelector("[data-runtime-observer]");
    const manifest = document.querySelector("[data-runtime-manifest]");
    const images = document.querySelector("[data-runtime-images]");
    const state = document.querySelector("[data-runtime-state]");
    if (observer) observer.textContent = `${RITUAL.observer} OBSERVADOR: ACTIVO`;
    if (manifest) manifest.textContent = `${RITUAL.manifest} ADN: ${planned} RANURAS`;
    if (images) images.textContent = `${RITUAL.pulse} IMÁGENES: ${ready}/${planned} CONECTADAS`;
    if (state) state.textContent = `${RITUAL.ready} ESTADO: ${ready > 0 ? "ARCHIVO VIVO" : "ESPERA"}`;
    document.documentElement.dataset.lse6MountedImages = String(ready);
    document.documentElement.dataset.lse6PlannedImages = String(planned);
  };

  const activateSlot = (article) => {
    let image = article.querySelector("img");
    let media = article.querySelector(".slot-media");
    if (!media) return;

    if (!image && article.dataset.src) {
      image = document.createElement("img");
      image.src = article.dataset.src;
      image.alt = article.querySelector(".slot-head strong")?.textContent?.trim() || article.dataset.file || "Archivo visual LSE6";
      image.loading = "lazy";
      image.decoding = "async";
      media.prepend(image);
    }
    if (!image) return;

    const setState = (state) => {
      article.classList.remove("is-loading", "is-ready", "is-missing");
      article.classList.add(`is-${state}`);
      article.dataset.installed = String(state === "ready");

      if (media instanceof HTMLButtonElement) {
        media.disabled = state !== "ready";
        media.setAttribute(
          "aria-label",
          state === "ready" ? `Abrir ${image.alt}` : `Espacio reservado para ${article.dataset.file || "imagen"}`,
        );
        if (state === "ready" && media.dataset.zoomBound !== "true") {
          media.dataset.zoomBound = "true";
          media.addEventListener("click", () => window.open(image.src, "_blank", "noopener,noreferrer"));
        }
      } else if (media instanceof HTMLAnchorElement) {
        if (state === "ready") {
          media.href = image.src;
          media.setAttribute("aria-label", `Abrir ${image.alt}`);
          media.removeAttribute("aria-disabled");
        } else {
          media.removeAttribute("href");
          media.setAttribute("aria-disabled", "true");
        }
      }
      updateRuntimeStatus();
    };

    image.addEventListener("load", () => setState("ready"), { once: true });
    image.addEventListener("error", () => setState("missing"), { once: true });
    if (image.complete) setState(image.naturalWidth > 0 ? "ready" : "missing");
  };

  document.querySelectorAll("[data-slot-group]").forEach((container) => {
    const name = container.dataset.slotGroup;
    const slots = groups[name] || [];
    const existing = new Set([...container.querySelectorAll(".archive-slot")].map((card) => card.dataset.file));
    const missingMarkup = slots.filter((slot) => !existing.has(filenameOf(slot.src))).map(slotMarkup).join("");
    if (missingMarkup) container.insertAdjacentHTML("beforeend", missingMarkup);
    container.querySelectorAll(".archive-slot").forEach(activateSlot);
  });

  document.querySelectorAll("[data-single-slot]").forEach((container) => {
    const slot = {
      id: container.dataset.id || "L",
      title: container.dataset.title || "Logo LSE6",
      src: container.dataset.src || "",
      tone: container.dataset.tone || "green",
      variant: "logo",
    };
    const wrapper = document.createElement("div");
    wrapper.innerHTML = slotMarkup(slot).trim();
    const article = wrapper.firstElementChild;
    if (article) {
      container.replaceWith(article);
      activateSlot(article);
    }
  });

  updateRuntimeStatus();'''
    text = text[:start] + replacement + text[end:]
    path.write_text(text, encoding="utf-8-sig", newline="\n")


def update_css() -> None:
    path = ROOT / "assets/css/styles.css"
    text = path.read_text(encoding="utf-8-sig")
    addition = r'''

/* 👁🧬⚡🔥 Capa ritual funcional: observador, ADN, pulso y estado real del montaje. */
.center-return-link,
.footer-center-link {
  color: inherit;
  text-decoration: none;
}

.center-return-link:hover,
.center-return-link:focus-visible,
.footer-center-link:hover,
.footer-center-link:focus-visible {
  color: var(--green-hot);
  text-shadow: 0 0 16px rgba(120, 255, 0, 0.55);
  outline: none;
}

.ritual-runtime {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  margin: 0 auto 14px;
  border: 1px solid rgba(120, 255, 0, 0.18);
  background: rgba(0, 0, 0, 0.72);
  color: var(--green);
  font-size: 7px;
  letter-spacing: 0.12em;
  text-align: center;
}

.ritual-runtime span {
  padding: 8px 6px;
  border-right: 1px solid rgba(120, 255, 0, 0.12);
}

.ritual-runtime span:last-child {
  border-right: 0;
  color: var(--amber-hot);
}

.archive-prologue {
  position: relative;
  margin-bottom: 20px;
  padding: clamp(18px, 3vw, 32px);
  overflow: hidden;
  border: 1px solid rgba(255, 157, 0, 0.28);
  background:
    linear-gradient(135deg, rgba(255, 157, 0, 0.05), transparent 45%),
    linear-gradient(rgba(120, 255, 0, 0.018) 1px, transparent 1px),
    linear-gradient(90deg, rgba(120, 255, 0, 0.018) 1px, transparent 1px),
    rgba(2, 4, 2, 0.92);
  background-size: auto, 22px 22px, 22px 22px, auto;
}

.archive-prologue h2 {
  margin: 8px 0 12px;
  color: var(--amber-hot);
  font-size: clamp(18px, 2.5vw, 32px);
  letter-spacing: 0.09em;
}

.archive-prologue p {
  max-width: 1000px;
  margin: 7px 0;
  color: var(--ink);
  font-size: clamp(10px, 1.1vw, 14px);
  line-height: 1.8;
}

.archive-prologue a {
  color: var(--green-hot);
  text-decoration-color: rgba(120, 255, 0, 0.4);
  text-underline-offset: 3px;
}

.prologue-sigil {
  color: var(--green);
  font-size: 9px;
  letter-spacing: 0.28em;
}

.slot-media[aria-disabled="true"] {
  cursor: default;
  pointer-events: none;
}

@media (max-width: 720px) {
  .ritual-runtime {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .ritual-runtime span:nth-child(2) {
    border-right: 0;
  }
}
'''
    if "Capa ritual funcional" not in text:
        text += addition
    mobile_css = r'''

/* LSE6 mobile media: picture changes bytes, never the original archive link. */
picture.mobile-picture {
  display: contents;
}
'''
    if "LSE6 mobile media" not in text:
        text += mobile_css
    path.write_text(text, encoding="utf-8-sig", newline="\n")


def update_404() -> None:
    path = ROOT / "404.html"
    template = ROOT / "tools/templates/404.template.html"
    soup = BeautifulSoup(template.read_text(encoding="utf-8-sig"), "html.parser")

    archive_link = soup.find("a", href="./")
    if archive_link is None:
        raise RuntimeError("404 template is missing its archive return link")
    archive_link["href"] = "/"

    center_link = soup.new_tag("a", href=CENTER)
    center_link["target"] = "_blank"
    center_link["rel"] = ["external", "noopener", "noreferrer"]
    center_link["aria-label"] = "Entrar al núcleo LSE6.com en una pestaña nueva"
    center_link.string = "ENTRAR AL NÚCLEO LSE6.COM ↗"
    archive_link.insert_after("\n    ", center_link)

    style = soup.find("style")
    if style and style.string:
        style.string = style.string.replace(
            "a:hover{color:#000;background:#78ff00}",
            "a{margin-inline:6px}a:hover{color:#000;background:#78ff00}",
        )

    rendered = "<!doctype html>\n" + str(soup.html)
    path.write_text(rendered, encoding="utf-8-sig", newline="\n")


def write_sitemaps(slots_by_group: dict[str, list[dict[str, Any]]]) -> None:
    urls = [
        (f"{SITE}/", BUILD_DATE),
        (f"{SITE}/evidencia/", BUILD_DATE),
        (f"{SITE}/error-31-12-69/", BUILD_DATE),
        (f"{SITE}/remake-666/", BUILD_DATE),
        (f"{SITE}/rutas-sixtem/", BUILD_DATE),
        (f"{SITE}/lseo-sixtem/", BUILD_DATE),
        (f"{SITE}/fuentes/", BUILD_DATE),
        (f"{SITE}/anomalias-temporales/", BUILD_DATE),
        (f"{SITE}/musica/", BUILD_DATE),
        (f"{SITE}/evidence/lse6-expediente-completo.pdf", RELEASE["pdf_lastmod"]),
    ]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod in urls:
        xml += ["  <url>", f"    <loc>{loc}</loc>", f"    <lastmod>{lastmod}</lastmod>", "  </url>"]
    xml.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(xml) + "\n", encoding="utf-8", newline="\n")

    hero_objects = []
    for item in HERO:
        local = ROOT / item["file"]
        if local.exists():
            hero_objects.append({"public_path": item["file"], "title": item["title"], "alt": item["alt"]})
    youtube_objects = []
    youtube_dir = ROOT / "assets/images/youtube"
    youtube_data = ROOT / "data/youtube-videos.json"
    youtube_titles = {}
    if youtube_data.exists():
        for item in json.loads(youtube_data.read_text(encoding="utf-8-sig")).get("videos", []):
            youtube_titles[Path(item["thumbnail"]).name] = item["title"]
    if youtube_dir.exists():
        for local in sorted(youtube_dir.glob("*.jpg")):
            title = youtube_titles.get(local.name, local.stem)
            youtube_objects.append({"public_path": local.relative_to(ROOT).as_posix(), "title": title, "alt": f"Miniatura oficial de YouTube para {title}"})
    system_objects = [
        {"public_path": "assets/images/system/lse6-eye-alpha.png", "title": "Ojo tecnológico LSE6", "alt": "Ojo vivo del archivo LSE6 siguiendo el movimiento"},
        {"public_path": "assets/images/system/lse6-org-og.jpg", "title": "LSE6.ORG archivo vivo", "alt": "Tarjeta social del archivo Ley del Sexto y LSEØ SIXTEM"},
    ]
    def installed(group: str) -> list[dict[str, Any]]:
        return [slot for slot in slots_by_group[group] if slot["installed"]]

    # Cada imagen se asocia con la puerta HTML que realmente le da contexto.
    # El bloque extra permanece en la portada hasta que exista contenido propio.
    image_groups = [
        (f"{SITE}/", hero_objects + system_objects + installed("extras")),
        (f"{SITE}/evidencia/", installed("evidence")),
        (f"{SITE}/error-31-12-69/", installed("error1969")),
        (f"{SITE}/remake-666/", installed("remake666")),
        (f"{SITE}/rutas-sixtem/", installed("routes")),
        (f"{SITE}/lseo-sixtem/", installed("sixtem")),
        (f"{SITE}/fuentes/", hero_objects),
        (f"{SITE}/anomalias-temporales/", system_objects[:1]),
        (f"{SITE}/musica/", installed("songs") + youtube_objects),
    ]
    ix = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
    ]
    for page_url, image_items in image_groups:
        if not image_items:
            continue
        ix += ["  <url>", f"    <loc>{page_url}</loc>"]
        for item in image_items:
            ix += [
                "    <image:image>",
                f"      <image:loc>{SITE}/{item['public_path']}</image:loc>",
                "    </image:image>",
            ]
        ix.append("  </url>")
    ix.append("</urlset>")
    (ROOT / "image-sitemap.xml").write_text("\n".join(ix) + "\n", encoding="utf-8", newline="\n")


def xml_escape(value: Any) -> str:
    return html_escape(value).replace("&#039;", "&apos;")


def update_configs(slots_by_group: dict[str, list[dict[str, Any]]]) -> None:
    (ROOT / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n\nSitemap: https://lse6.org/sitemap.xml\nSitemap: https://lse6.org/image-sitemap.xml\n",
        encoding="utf-8",
        newline="\n",
    )
    (ROOT / "_redirects").write_text(
        "# 🧭 Rutas canónicas LSE6.ORG · Cloudflare Pages\n"
        "/index.html / 301\n"
        "/home / 301\n"
        "/inicio / 301\n"
        "/favicon.ico /favicon.png 301\n"
        "/archivo /evidencia/ 301\n"
        "/expediente /evidence/lse6-expediente-completo.pdf 301\n"
        "/alta-res /fuentes/ 302\n"
        "/datos /anomalias-temporales/ 302\n"
        "/centro https://lse6.com/ 301\n"
        "/lse6 https://lse6.com/ 301\n"
        "/lse6.com https://lse6.com/ 301\n",
        encoding="utf-8",
        newline="\n",
    )
    (ROOT / "_headers").write_text(
        "# 🛡️ Capa técnica de entrega · Cloudflare Pages\n"
        "/*\n"
        "  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
        "  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()\n"
        "  X-Frame-Options: SAMEORIGIN\n"
        "  Cross-Origin-Opener-Policy: same-origin\n"
        "  Cross-Origin-Resource-Policy: same-site\n"
        "  Strict-Transport-Security: max-age=31536000; includeSubDomains\n"
        "  Content-Security-Policy: default-src 'self'; base-uri 'self'; connect-src 'self'; font-src 'self' data:; img-src 'self' data: blob:; manifest-src 'self'; media-src 'self'; object-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; frame-ancestors 'self'; form-action 'self'; upgrade-insecure-requests\n"
        "\n/\n"
        "  Cache-Control: public, max-age=0, must-revalidate\n"
        "\n/*.html\n"
        "  Cache-Control: public, max-age=0, must-revalidate\n"
        "\n/assets/css/*\n"
        "  Cache-Control: public, max-age=86400, stale-while-revalidate=604800\n"
        "\n/assets/js/*\n"
        "  Cache-Control: public, max-age=86400, stale-while-revalidate=604800\n"
        "\n/assets/images/*\n"
        "  Cache-Control: public, max-age=3600, stale-while-revalidate=86400\n"
        "\n/assets/source-library/*\n"
        "  Cache-Control: public, max-age=604800, stale-while-revalidate=2592000\n"
        "  X-Robots-Tag: noindex, nofollow\n"
        "\n/evidence/lse6-expediente-completo.pdf\n"
        "  Cache-Control: public, max-age=604800, stale-while-revalidate=2592000\n"
        "  X-Robots-Tag: index, follow\n"
        "\n/evidence/high-resolution/*.pdf\n"
        "  Cache-Control: public, max-age=604800, stale-while-revalidate=2592000\n"
        "  X-Robots-Tag: noindex, follow\n"
        "\n/evidence/*.txt\n"
        "  Cache-Control: public, max-age=86400, stale-while-revalidate=604800\n"
        "  X-Robots-Tag: noindex, nofollow\n"
        "\n/evidence/*.json\n"
        "  Cache-Control: public, max-age=86400, stale-while-revalidate=604800\n"
        "  X-Robots-Tag: noindex, nofollow\n"
        "\n/evidence/high-resolution/*.json\n"
        "  Cache-Control: public, max-age=86400, stale-while-revalidate=604800\n"
        "  X-Robots-Tag: noindex, nofollow\n"
        "\n/data/*\n"
        "  Cache-Control: public, max-age=300, stale-while-revalidate=86400\n"
        "\n/data/saltos-temporales/\n"
        "  X-Robots-Tag: noindex, nofollow, noarchive, nosnippet\n"
        "\n/data/*.json\n"
        "  X-Robots-Tag: noindex, nofollow\n"
        "\n/data/saltos-temporales/*.json\n"
        "  X-Robots-Tag: noindex, nofollow\n"
        "\n/data/saltos-temporales/*.csv\n"
        "  X-Robots-Tag: noindex, nofollow, noarchive, nosnippet\n"
        "\n/data/saltos-temporales/*.txt\n"
        "  X-Robots-Tag: noindex, nofollow\n"
        "\n/data/saltos-temporales/*.py\n"
        "  X-Robots-Tag: noindex, nofollow\n"
        "\n/*.json\n"
        "  Cache-Control: public, max-age=300, stale-while-revalidate=86400\n"
        "  X-Robots-Tag: noindex, nofollow\n"
        "\n/assets/data/*.json\n"
        "  X-Robots-Tag: noindex, nofollow\n"
        "\n/docs/*\n"
        "  X-Robots-Tag: noindex, follow\n"
        "\n/tools/*\n"
        "  X-Robots-Tag: noindex, nofollow\n"
        "\n/site.webmanifest\n"
        "  X-Robots-Tag: noindex, nofollow\n"
        "\n/*.xml\n"
        "  Cache-Control: public, max-age=300, stale-while-revalidate=86400\n"
        "\n/INTEGRITY.sha256\n"
        "  Cache-Control: no-cache\n"
        "  X-Robots-Tag: noindex, nofollow\n"
        "\nhttps://:project.pages.dev/*\n"
        "  X-Robots-Tag: noindex, nofollow\n"
        "\nhttps://:version.:project.pages.dev/*\n"
        "  X-Robots-Tag: noindex, nofollow\n",
        encoding="utf-8",
        newline="\n",
    )
    manifest = {
        "name": "LSE6.ORG — Archivo Vivo",
        "short_name": "LSE6.ORG",
        "description": "Archivo documental de LSE6.com: Ley del Sexto, Error 31/12/69, Remake 666 Moderno y LSEØ SIXTEM.",
        "id": "/",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "orientation": "any",
        "background_color": "#010201",
        "theme_color": "#010201",
        "lang": "es-MX",
        "icons": [
            {"src": "/favicon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"},
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }
    (ROOT / "site.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    installed = [slot for group in slots_by_group.values() for slot in group if slot["installed"]]
    installed_group_counts = {name: sum(slot["installed"] for slot in slots) for name, slots in slots_by_group.items()}
    package = json.loads((ROOT / "package-manifest.json").read_text(encoding="utf-8-sig"))
    package.update({
        "version": RELEASE["version"],
        "state": RELEASE["state"],
        "last_build": BUILD_TIME,
        "build_id": BUILD_ID,
        "required_user_action": "Validar el release, publicar main y comprobar el SHA exacto en GitHub Actions y Cloudflare Pages.",
    })
    package["image_slots"].update({
        "planned_total": 63,
        "installed_content": len(installed),
        "installed_logos": 2,
        "installed_total": len(installed) + 2,
        "missing_total": 63 - (len(installed) + 2),
        "installed_by_group": installed_group_counts,
    })
    package["deployment"].update({
        "cloudflare_status": "CONNECTED",
        "github_status": "CONNECTED",
        "release_state": RELEASE["state"],
        "image_sitemap": "image-sitemap.xml",
    })
    (ROOT / "package-manifest.json").write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    image_manifest_path = ROOT / "assets/data/image-manifest.json"
    image_manifest = json.loads(image_manifest_path.read_text(encoding="utf-8-sig"))
    image_manifest.update({
        "state": RELEASE["state"],
        "version": RELEASE["version"],
        "build_id": BUILD_ID,
        "last_build": BUILD_TIME,
        "installed_image_files": len(installed) + 2,
        "missing_image_files": 63 - (len(installed) + 2),
        "installed_by_group": {"hero_logos": 2, **installed_group_counts},
        "image_sitemap": "https://lse6.org/image-sitemap.xml",
        "instructions": "Las imágenes instaladas ya están montadas en HTML e image-sitemap.xml. Agrega las faltantes conservando las rutas exactas y ejecuta tools/rebuild_release.py para regenerar descubrimiento e integridad.",
    })
    image_manifest_path.write_text(json.dumps(image_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def update_identity_files(slots_by_group: dict[str, list[dict[str, Any]]]) -> None:
    installed_content = sum(slot["installed"] for group in slots_by_group.values() for slot in group)
    installed_total = installed_content + sum((ROOT / item["file"]).exists() for item in HERO)
    missing_total = 63 - installed_total
    path = ROOT / "assets/js/site-identity.js"
    text = path.read_text(encoding="utf-8-sig")
    text = re.sub(r'    imageSlots: 63,(?:\n    installedImages: \d+,\n    missingImages: \d+,)?', f'    imageSlots: 63,\n    installedImages: {installed_total},\n    missingImages: {missing_total},', text, count=1)
    text = re.sub(r'build: "[^"]+"', f'build: "{BUILD_ID}"', text)
    text = re.sub(r'      sitemap: "https://lse6.org/sitemap.xml",(?:\n      imageSitemap: "https://lse6.org/image-sitemap.xml",)?', '      sitemap: "https://lse6.org/sitemap.xml",\n      imageSitemap: "https://lse6.org/image-sitemap.xml",', text, count=1)
    path.write_text(text, encoding="utf-8-sig", newline="\n")

    legacy = ROOT / "site_identity_LSE6_ORG.js"
    text = legacy.read_text(encoding="utf-8-sig")
    text = re.sub(r'  imageSlots: 63,(?:\n  installedImages: \d+,\n  missingImages: \d+,)?', f'  imageSlots: 63,\n  installedImages: {installed_total},\n  missingImages: {missing_total},', text, count=1)
    text = re.sub(r'  build: "[^"]+",', f'  build: "{BUILD_ID}",', text, count=1)
    legacy.write_text(text, encoding="utf-8-sig", newline="\n")

    for relative in ["machine-pulse.json", "data/machine-pulse.json"]:
        p = ROOT / relative
        data = json.loads(p.read_text(encoding="utf-8-sig"))
        data.update({
            "release_state": RELEASE["state"],
            "version": RELEASE["version"],
            "last_build": BUILD_TIME,
            "build": BUILD_ID,
            "installed_images": installed_total,
            "missing_images": missing_total,
        })
        data["nodes"].update({
            "image_sitemap": f"{SITE}/image-sitemap.xml",
            "evidencia": f"{SITE}/evidencia/",
            "error_31_12_69": f"{SITE}/error-31-12-69/",
            "remake_666": f"{SITE}/remake-666/",
            "rutas_sixtem": f"{SITE}/rutas-sixtem/",
            "lseo_sixtem": f"{SITE}/lseo-sixtem/",
            "fuentes": f"{SITE}/fuentes/",
            "anomalias_temporales": f"{SITE}/anomalias-temporales/",
            "musica": f"{SITE}/musica/",
        })
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def update_docs(slots_by_group: dict[str, list[dict[str, Any]]]) -> None:
    installed_content = sum(slot["installed"] for group in slots_by_group.values() for slot in group)
    installed_total = installed_content + sum((ROOT / item["file"]).exists() for item in HERO)
    missing_total = 63 - installed_total
    readme = f'''# LSE6.ORG · ARCHIVO VIVO INDEXABLE

Extensión documental de [LSE6.com]({CENTER}) preparada para GitHub y Cloudflare Pages.

## Estado de esta entrega

- 🔥 Release: `{BUILD_ID}`
- 🧬 Versión: `{RELEASE["version"]}` · estado: `{RELEASE["state"]}`.
- 👁 Página estática visible incluso sin JavaScript.
- 🧬 63 ranuras planeadas, {installed_total} imágenes instaladas y {missing_total} ranuras futuras.
- ⚡ Sitemap principal + sitemap de imágenes.
- ⏳ ANOMALÍAS TEMPORALES: cuatro campos del CSV real y evidencia por año.
- 🧾 CSV ORIGINAL: 256,666 registros preservados en 6 partes descargables, noindex/nofollow y reconstruibles. Siguen siendo públicos hasta una decisión explícita de protección o redacción.
- ▶ 7 miniaturas oficiales enlazadas al canal @leydelsexto.
- 551 páginas en PDF web canónico, texto buscable y 8 volúmenes de alta resolución.
- El botón, la firma y las menciones visibles de LSE6.com abren el centro en una pestaña nueva sin cerrar LSE6.ORG.

## Subir a GitHub

1. Crea o abre el repositorio destinado a `lse6.org`.
2. Sube **el contenido de esta carpeta**, no la carpeta contenedora.
3. Confirma que `index.html`, `CNAME`, `_headers`, `_redirects` y `robots.txt` queden en la raíz.
4. Conserva `.nojekyll` para GitHub Pages.

## Conectar Cloudflare Pages

- Framework preset: `None`
- Build command: vacío
- Build output directory: `.`
- Dominio personalizado: `lse6.org`

Cloudflare procesa `_headers` y `_redirects` automáticamente. Las URLs temporales `*.pages.dev` reciben `noindex`; el dominio `lse6.org` permanece indexable.

## Después de publicar

1. Abre `https://lse6.org/robots.txt`.
2. Abre `https://lse6.org/sitemap.xml`.
3. Abre `https://lse6.org/image-sitemap.xml`.
4. Registra la propiedad de dominio en Google Search Console.
5. Envía ambos sitemaps y solicita indexación de `https://lse6.org/`.

## Reconstrucción determinista

Las rutas exactas viven en `assets/data/image-manifest.json`. Después de copiar nuevas imágenes:

```bash
python tools/rebuild_release.py
python tools/validate_release.py
```

El comando normal trabaja sin red y toma versión, fecha y Build ID de `data/release.json`; con las mismas entradas produce los mismos artefactos. Monta la portada, las ocho puertas HTML canónicas, ambos sitemaps, pulsos e integridad raw SHA-256. El sitemap principal conserva sólo nueve páginas HTML de destino y el PDF completo; CSV, JSON, TXT y manifiestos permanecen fuera de esa superficie.

Para refrescar deliberadamente las miniaturas oficiales antes de construir:

```bash
python tools/rebuild_release.py --refresh-youtube
```

El refresco remoto es una acción separada y puede cambiar entradas del release; debe revisarse antes del commit.

## Símbolos funcionales

- 👁 `OBSERVADOR`: confirma que la capa visual está activa.
- 🧬 `ADN`: representa el manifiesto total de ranuras.
- ⚡ `IMÁGENES`: muestra cuántos archivos están conectados realmente.
- 🔥 `ESTADO`: confirma el estado final del archivo.

## Centro

`LSE6.com` es el núcleo. `LSE6.org` es archivo, soporte y extensión.
'''
    (ROOT / "README.md").write_text(readme, encoding="utf-8-sig", newline="\n")
    llms = f'''# LSE6.ORG

LSE6.ORG es el archivo vivo, visible e indexable de LSE6.com.

Centro canónico: {CENTER}
Archivo: {SITE}/
Identidad artística: LSE6 - AlekSix LM
Marca / ley: LEY DEL SEXTO
Sistema documentado: LSEØ - SIXTEM
Handle: @leydelsexto
Versión: {RELEASE["version"]}
Estado: {RELEASE["state"]}
Build: {BUILD_ID}

## Contenido instalado

- Expediente final integrado: 551 páginas.
- Evidencia visible: 6 imágenes.
- Error 31/12/69: 7 imágenes.
- 666 Moderno Remake: 9 imágenes.
- Rutas SIXTEM: 6 imágenes.
- LSEØ SIXTEM: 7 imágenes.
- Logos del héroe: 2 imágenes.
- Bloque Extra: 20 imágenes instaladas.
- Canal oficial: 7 miniaturas sincronizadas con YouTube.
- LSE6_SALTOS_TEMPORALES.csv: 256,666 registros en 6 partes CSV, con hashes y reconstrucción verificable.
- Expediente original en alta resolución: 8 volúmenes.
- Fuentes editables: Markdown y DOCX.
- Capa máquina: expediente, cronología, entidad, pulso y manifiesto de imágenes en JSON.

## Rutas de descubrimiento

- {SITE}/sitemap.xml
- {SITE}/image-sitemap.xml
- {SITE}/evidencia/
- {SITE}/error-31-12-69/
- {SITE}/remake-666/
- {SITE}/rutas-sixtem/
- {SITE}/lseo-sixtem/
- {SITE}/fuentes/
- {SITE}/anomalias-temporales/
- {SITE}/musica/
- {SITE}/evidence/lse6-expediente-completo.pdf

## Recursos técnicos enlazados, no destinados a resultados individuales

- {SITE}/evidence/lse6-expediente-completo.txt
- {SITE}/evidence/high-resolution/index.json
- {SITE}/docs/lse6-expediente-integrado.md
- {SITE}/data/expediente.json
- {SITE}/data/timeline.json
- {SITE}/data/temporal-anomalies.json
- {SITE}/data/saltos-temporales/index.json
- {SITE}/data/saltos-temporales/SHA256SUMS.txt
- {SITE}/data/saltos-temporales/ (índice técnico noindex/nofollow; los CSV continúan públicos)
- {SITE}/data/youtube-videos.json
- {SITE}/assets/data/image-manifest.json

El centro siempre es LSE6.com. LSE6.org funciona como archivo, soporte y extensión.
'''
    (ROOT / "llms.txt").write_text(llms, encoding="utf-8", newline="\n")


def write_integrity() -> None:
    entries = []
    for path in sorted(ROOT.rglob("*")):
        if (
            not path.is_file()
            or path.name == "INTEGRITY.sha256"
            or ".git" in path.parts
            or "__pycache__" in path.parts
            or path.suffix.lower() in {".pyc", ".pyo"}
        ):
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append(f"{digest}  {path.relative_to(ROOT).as_posix()}")
    (ROOT / "INTEGRITY.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconstruye el release estático reproducible de LSE6.ORG")
    parser.add_argument(
        "--refresh-youtube",
        action="store_true",
        help="actualiza miniaturas remotas antes del build; cambia entradas y requiere revisión",
    )
    args = parser.parse_args()
    if args.refresh_youtube:
        sync_youtube_thumbnails()
    slots = all_slots()
    create_og_image()
    update_index(slots)
    write_archive_doors(slots)
    update_js()
    update_css()
    update_404()
    write_sitemaps(slots)
    update_configs(slots)
    update_identity_files(slots)
    update_docs(slots)
    write_integrity()
    print(f"🔥 {BUILD_ID} construido: {ROOT}")


if __name__ == "__main__":
    main()
