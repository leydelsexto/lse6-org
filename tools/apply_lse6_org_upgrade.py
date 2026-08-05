from __future__ import annotations
import csv, hashlib, html, json, re, urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image

ROOT = Path(r"C:\LSE6_WEB\LSE6_CONSTRUCCION\LSE6_ORG")
CSV_PATH = Path(r"C:\Users\Alexis\Desktop\LSE6_SALTOS_TEMPORALES.csv")
TEMPLATE = ROOT / "tools/templates/index.template.html"
REBUILD = ROOT / "tools/rebuild_release.py"
VALIDATOR = ROOT / "tools/validate_release.py"
CSS = ROOT / "assets/css/styles.css"
YT_JSON = ROOT / "data/youtube-channel.json"
YT_DIR = ROOT / "assets/images/youtube"
DATE_FIELDS = ["CreationTime", "CreationTimeUtc", "LastWriteTime", "LastWriteTimeUtc"]
LABELS = {"CreationTime":"CREACIÓN LOCAL","CreationTimeUtc":"CREACIÓN UTC","LastWriteTime":"MODIFICACIÓN LOCAL","LastWriteTimeUtc":"MODIFICACIÓN UTC"}
CLASSES = {"CreationTime":"create-local","CreationTimeUtc":"create-utc","LastWriteTime":"write-local","LastWriteTimeUtc":"write-utc"}
YEAR_RE = re.compile(r"^\s*\d{1,2}/\d{1,2}/(\d{4})\b")

def year_of(value):
    match = YEAR_RE.match(value or "")
    return int(match.group(1)) if match else None

def public_path(value):
    value = (value or "").replace("\\", "/")
    return re.sub(r"^C:/Users/[^/]+/", "C:/Users/[LOCAL]/", value, flags=re.I)

def analyze_csv():
    counts = {field: Counter() for field in DATE_FIELDS}
    samples = defaultdict(list)
    rows = 0
    digest = hashlib.sha256()
    with CSV_PATH.open("rb") as raw:
        for chunk in iter(lambda: raw.read(1024 * 1024), b""):
            digest.update(chunk)
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        for row in csv.DictReader(handle):
            rows += 1
            years = {}
            for field in DATE_FIELDS:
                year = year_of(row.get(field, ""))
                years[field] = year
                if year is not None:
                    counts[field][year] += 1
            wanted = {y for y in years.values() if y is not None and (y <= 2018 or y in {2020, 2021, 2023})}
            for year in wanted:
                if len(samples[year]) < 4:
                    samples[year].append({
                        "name": row.get("Name", ""),
                        "path": public_path(row.get("FullName", "")),
                        "creation": row.get("CreationTime", ""),
                        "creation_utc": row.get("CreationTimeUtc", ""),
                        "write": row.get("LastWriteTime", ""),
                        "write_utc": row.get("LastWriteTimeUtc", ""),
                    })
    years = sorted(set().union(*(set(counter) for counter in counts.values())))
    payload = {
        "source": {"filename": CSV_PATH.name, "rows": rows, "bytes": CSV_PATH.stat().st_size, "sha256": digest.hexdigest()},
        "fields": {field: {str(year): counts[field][year] for year in years if counts[field][year]} for field in DATE_FIELDS},
        "summary": {
            "creation_local_total": sum(counts["CreationTime"].values()),
            "creation_utc_total": sum(counts["CreationTimeUtc"].values()),
            "write_local_total": sum(counts["LastWriteTime"].values()),
            "write_utc_total": sum(counts["LastWriteTimeUtc"].values()),
            "write_local_pre_2019": sum(value for year, value in counts["LastWriteTime"].items() if year < 2019),
        },
        "years": years,
        "samples": {str(year): items for year, items in sorted(samples.items())},
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    path = ROOT / "data/temporal-anomalies.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload

def temporal_html(payload):
    counts = {field: {int(k): v for k, v in payload["fields"][field].items()} for field in DATE_FIELDS}
    summary = payload["summary"]
    timelines = []
    for field in DATE_FIELDS:
        field_counts = counts[field]
        maximum = max(field_counts.values(), default=1)
        rows = []
        for year in sorted(field_counts):
            value = field_counts[year]
            width = max(0.35, value / maximum * 100)
            rows.append(
                f'<div class="temporal-line-year">'
                f'<span>{year}</span>'
                f'<i style="--temporal-width:{width:.6f}%"></i>'
                f'<b>{value:,}</b>'
                f'</div>'
            )
        timelines.append(
            f'<article class="temporal-timeline {CLASSES[field]}">'
            f'<header><span>{LABELS[field]}</span><strong>{sum(field_counts.values()):,} REGISTROS</strong></header>'
            f'<div class="temporal-line-list">{"".join(rows)}</div>'
            f'</article>'
        )
    cards = []
    for year, items in payload["samples"].items():
        entries = []
        for item in items:
            entries.append(
                '<li>'
                f'<b>{html.escape(item["name"])}</b>'
                f'<code>{html.escape(item["path"])}</code>'
                f'<span>C: {html.escape(item["creation"])} · CUTC: {html.escape(item["creation_utc"])}</span>'
                f'<span>W: {html.escape(item["write"])} · WUTC: {html.escape(item["write_utc"])}</span>'
                '</li>'
            )
        cards.append(
            f'<article class="temporal-evidence-card"><h3>{year}</h3><ul>{"".join(entries)}</ul></article>'
        )
    source = payload["source"]
    return f'''<section id="anomalias-temporales" class="archive-panel panel-red temporal-panel">
<div class="section-signal" aria-hidden="true"><i></i><i></i><i></i></div>
<header class="panel-heading"><div><span>CSV REAL / CUATRO LÍNEAS TEMPORALES / SIN INTERPRETACIÓN</span><h2>ANOMALÍAS TEMPORALES</h2></div><strong>{source["rows"]:,} REGISTROS</strong></header>
<div class="temporal-source"><span>{source["filename"]}</span><code>SHA-256 {source["sha256"]}</code></div>
<div class="temporal-summary">
<article><span>FILAS DEL CSV</span><strong>{source["rows"]:,}</strong></article>
<article><span>CREACIÓN LOCAL</span><strong>{summary["creation_local_total"]:,}</strong></article>
<article><span>CREACIÓN UTC</span><strong>{summary["creation_utc_total"]:,}</strong></article>
<article><span>MODIFICACIÓN LOCAL</span><strong>{summary["write_local_total"]:,}</strong></article>
<article><span>MODIFICACIÓN UTC</span><strong>{summary["write_utc_total"]:,}</strong></article>
</div>
<div class="temporal-separation-note">CREACIÓN y MODIFICACIÓN se muestran en líneas distintas. Cada panel contiene únicamente los años presentes en esa columna.</div>
<div class="temporal-timelines">{"".join(timelines)}</div>
<div class="temporal-evidence-grid">{"".join(cards)}</div>
<div class="temporal-data-links">
<a class="temporal-data-link" href="./data/temporal-anomalies.json" target="_blank" rel="noopener">ABRIR DATOS ESTRUCTURADOS ↗</a>
<a class="temporal-data-link temporal-csv-link" href="./data/saltos-temporales/" target="_blank" rel="noopener">ABRIR CSV ORIGINAL EN 6 PARTES ↗</a>
</div></section>'''


SONGS = {
    "pdcQBdp-xhg": "LEY DEL SEXTO",
    "Re5mvPwaoG4": "ZONA GRIS",
    "jdpOHKF_dXQ": "CLONES Y FANTASMAS",
    "9wk6CUoYwFo": "NADA ME BORRA",
    "M0N5CoOKyEY": "LIBRE PRISIONERO",
    "v40hHkTtdig": "LSE6",
    "Fafu9xC-npY": "ERROR 404",
}

def download_thumb(video_id):
    YT_DIR.mkdir(parents=True, exist_ok=True)
    output = YT_DIR / f"{video_id}.jpg"
    for quality in ("maxresdefault", "hqdefault"):
        try:
            request = urllib.request.Request(f"https://i.ytimg.com/vi/{video_id}/{quality}.jpg", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=25) as response:
                body = response.read()
            if len(body) > 1000:
                output.write_bytes(body)
                with Image.open(output) as image:
                    if image.width > 200 and image.height > 100:
                        return output
        except Exception:
            pass
    raise RuntimeError(f"No se pudo descargar miniatura {video_id}")

def youtube_html():
    channel = json.loads(YT_JSON.read_text(encoding="utf-8"))
    ids = {entry.get("id") for entry in channel.get("entries", [])}
    cards, inventory = [], []
    for video_id, title in SONGS.items():
        if video_id not in ids:
            raise RuntimeError(f"Video ausente del canal: {video_id}")
        thumb = download_thumb(video_id)
        with Image.open(thumb) as image:
            width, height = image.size
        url = f"https://www.youtube.com/watch?v={video_id}"
        src = f"./assets/images/youtube/{video_id}.jpg"
        cards.append(f'''<article class="youtube-card"><a class="youtube-thumb" href="{url}" target="_blank" rel="external noopener noreferrer"><img src="{src}" alt="Miniatura oficial de YouTube para {title}" width="{width}" height="{height}" loading="lazy" decoding="async"><span class="youtube-play">▶</span></a><div class="youtube-card-body"><small>@LEYDELSEXTO · YOUTUBE</small><h3>{title}</h3><a href="{url}" target="_blank" rel="external noopener noreferrer">ABRIR EN YOUTUBE ↗</a></div></article>''')
        inventory.append({"id": video_id, "title": title, "url": url, "thumbnail": src[2:]})
    (ROOT / "data/youtube-videos.json").write_text(json.dumps({"channel":"https://www.youtube.com/@leydelsexto","videos":inventory}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return f'''<section id="youtube" class="archive-panel panel-amber youtube-panel"><div class="section-signal" aria-hidden="true"><i></i><i></i><i></i></div><header class="panel-heading"><div><span>CANAL OFICIAL / MINIATURA SINCRONIZADA / SALIDA DIRECTA</span><h2>MÚSICA · MINIATURAS YOUTUBE</h2></div><strong>{len(cards)} VIDEOS</strong></header><div class="youtube-grid">{"".join(cards)}</div><a class="youtube-channel-link" href="https://www.youtube.com/@leydelsexto" target="_blank" rel="external noopener noreferrer">ABRIR CANAL @LEYDELSEXTO ↗</a></section>'''

def patch_template(temporal, youtube):
    soup = BeautifulSoup(TEMPLATE.read_text(encoding="utf-8-sig"), "html.parser")
    nav = soup.select_one("nav.archive-nav")
    for selector in ('a[href="#anomalias-temporales"]','a[href="#youtube"]'):
        old = nav.select_one(selector)
        if old: old.decompose()
    extra_link = nav.select_one('a[href="#extra"]')
    link = soup.new_tag("a", href="#anomalias-temporales"); link.string = "ANOMALÍAS"; extra_link.insert_before(link)
    ylink = soup.new_tag("a", href="#youtube"); ylink.string = "YOUTUBE"
    music = nav.select_one('a[href="#musica"]')
    if music: music.replace_with(ylink)
    else: extra_link.insert_after(ylink)
    for section_id in ("anomalias-temporales", "youtube"):
        old = soup.select_one(f"#{section_id}")
        if old: old.decompose()
    extra = soup.select_one("#extra")
    extra.insert_before(BeautifulSoup(temporal, "html.parser"))
    old_music = soup.select_one("#musica")
    new_youtube = BeautifulSoup(youtube, "html.parser")
    if old_music: old_music.replace_with(new_youtube)
    else: extra.insert_after(new_youtube)
    metric = soup.select_one(".metric-strip .metric:nth-of-type(5) strong")
    if metric: metric.string = "7"
    label = soup.select_one(".metric-strip .metric:nth-of-type(5) span")
    if label: label.string = "VIDEOS"
    TEMPLATE.write_text("<!doctype html>\n" + str(soup.html), encoding="utf-8-sig", newline="\n")

def patch_rebuild():
    text = REBUILD.read_text(encoding="utf-8-sig")
    text = re.sub(r'BUILD_TIME = "[^"]+"\nBUILD_ID = "[^"]+"', 'BUILD_TIME = datetime.now().astimezone().isoformat(timespec="seconds")\nBUILD_ID = "LSE6_ORG_TEMPORAL_YOUTUBE_" + datetime.now().strftime("%Y%m%d_%H%M%S")', text, count=1)
    text = text.replace("entran al centro en la misma pestaña", "abren el centro en una pestaña nueva sin cerrar LSE6.ORG")
    text = text.replace("- Ranuras futuras: Bloque Extra 20 y Núcleo Musical 6.", "- Bloque Extra: 20 imágenes instaladas.\n- Canal oficial: 7 miniaturas sincronizadas con YouTube.")
    text = text.replace('(f"{SITE}/assets/data/image-manifest.json", "weekly", "0.6"),', '(f"{SITE}/assets/data/image-manifest.json", "weekly", "0.6"),\n        (f"{SITE}/data/temporal-anomalies.json", "weekly", "0.8"),\n        (f"{SITE}/data/youtube-videos.json", "weekly", "0.8"),')
    marker = '    image_items = hero_objects + installed + [\n'
    if "youtube_objects = []" not in text:
        replacement = '''    youtube_objects = []
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
    image_items = hero_objects + installed + youtube_objects + [
'''
        text = text.replace(marker, replacement, 1)
    REBUILD.write_text(text, encoding="utf-8-sig", newline="\n")

def patch_validator():
    text = VALIDATOR.read_text(encoding="utf-8-sig")
    marker = 'ROOT = Path(__file__).resolve().parents[1]\n'
    if "sys.stdout.reconfigure" not in text:
        text = text.replace(marker, marker + 'if hasattr(sys.stdout, "reconfigure"):\n    sys.stdout.reconfigure(encoding="utf-8", errors="replace")\nif hasattr(sys.stderr, "reconfigure"):\n    sys.stderr.reconfigure(encoding="utf-8", errors="replace")\n', 1)
    VALIDATOR.write_text(text, encoding="utf-8-sig", newline="\n")

def patch_css():
    text = CSS.read_text(encoding="utf-8-sig")
    if "LSE6 TEMPORAL + YOUTUBE 2026" in text:
        return
    css = '''
/* LSE6 TEMPORAL + YOUTUBE 2026 */
.temporal-source{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;padding:12px;border:1px solid rgba(255,36,29,.25);background:#050101;color:var(--red-hot);font-size:9px}.temporal-source code{color:var(--muted);word-break:break-all}.temporal-legend,.temporal-bars{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.temporal-legend{margin:14px 0;font-size:8px;text-align:center}.temporal-legend span{padding:8px;border:1px solid currentColor}.create-local{color:#78ff00}.create-utc{color:#d5c887}.write-local{color:#ff241d}.write-utc{color:#ff9d00}.temporal-chart{display:grid;gap:7px;padding:14px;border:1px solid rgba(255,36,29,.25);background:#020101}.temporal-year{display:grid;grid-template-columns:64px 1fr;gap:10px;align-items:center}.temporal-year>strong{color:var(--amber-hot)}.temporal-measure{display:grid;grid-template-columns:1fr auto;grid-template-rows:auto 4px;gap:3px 8px;min-width:0}.temporal-measure span,.temporal-measure b{font-size:6px}.temporal-measure i{grid-column:1/-1;width:var(--temporal-width);height:4px;background:currentColor;box-shadow:0 0 9px currentColor}.temporal-evidence-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:14px}.temporal-evidence-card{border:1px solid rgba(255,36,29,.25);background:#030101;padding:12px;min-width:0}.temporal-evidence-card h3{color:var(--red-hot);font-size:22px}.temporal-evidence-card ul{display:grid;gap:10px;margin:0;padding:0;list-style:none}.temporal-evidence-card li{display:grid;gap:3px}.temporal-evidence-card b{font-size:8px}.temporal-evidence-card code,.temporal-evidence-card span{font-size:6px;word-break:break-all}.temporal-data-link,.youtube-channel-link{display:block;margin-top:14px;padding:12px;border:1px solid var(--green);color:var(--green);text-align:center;text-decoration:none}.youtube-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.youtube-card{overflow:hidden;border:1px solid rgba(255,157,0,.32);background:#030201}.youtube-thumb{position:relative;display:block;aspect-ratio:16/9;overflow:hidden;background:#000}.youtube-thumb img{width:100%;height:100%;object-fit:cover}.youtube-play{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);padding:10px 18px;background:rgba(255,0,0,.82);color:#fff}.youtube-card-body{display:grid;gap:8px;padding:13px}.youtube-card-body h3{margin:0;color:var(--amber-hot)}.youtube-card-body a{padding:9px;border:1px solid rgba(120,255,0,.5);color:var(--green);text-align:center;text-decoration:none}@media(max-width:900px){.temporal-evidence-grid,.youtube-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.temporal-bars{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:560px){.temporal-legend,.temporal-evidence-grid,.youtube-grid,.temporal-bars{grid-template-columns:1fr}}
'''
    CSS.write_text(text + css, encoding="utf-8-sig", newline="\n")

def main():
    payload = analyze_csv()
    patch_template(temporal_html(payload), youtube_html())
    patch_rebuild()
    patch_validator()
    patch_css()
    print("UPGRADE_SOURCE_READY", payload["source"]["rows"], payload["years"], len(SONGS))

if __name__ == "__main__":
    main()
