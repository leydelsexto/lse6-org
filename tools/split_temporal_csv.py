from __future__ import annotations

import hashlib
import html
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\LSE6_WEB\LSE6_CONSTRUCCION\LSE6_ORG")
SOURCE = Path(r"C:\Users\Alexis\Desktop\LSE6_SALTOS_TEMPORALES.csv")
OUT = ROOT / "data" / "saltos-temporales"
PARTS = 6
MAX_BYTES = 25 * 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_rows(path: Path) -> int:
    with path.open("rb") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def split_archive() -> dict:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("LSE6_SALTOS_TEMPORALES_PARTE_*_DE_06.csv"):
        old.unlink()

    total_rows = count_rows(SOURCE)
    base, remainder = divmod(total_rows, PARTS)
    targets = [base + (1 if index < remainder else 0) for index in range(PARTS)]
    original_sha = sha256_file(SOURCE)
    original_bytes = SOURCE.stat().st_size
    parts = []

    with SOURCE.open("rb") as source:
        header = source.readline()
        if not header:
            raise RuntimeError("CSV sin encabezado")
        start_row = 1
        for index, target_rows in enumerate(targets, start=1):
            filename = f"LSE6_SALTOS_TEMPORALES_PARTE_{index:02d}_DE_06.csv"
            destination = OUT / filename
            with destination.open("wb") as output:
                output.write(header)
                for _ in range(target_rows):
                    row = source.readline()
                    if not row:
                        raise RuntimeError("El CSV terminó antes de completar las seis partes")
                    output.write(row)
            size = destination.stat().st_size
            if size >= MAX_BYTES:
                raise RuntimeError(f"{filename} supera 25 MiB: {size}")
            end_row = start_row + target_rows - 1
            parts.append({
                "part": index,
                "filename": filename,
                "url": f"https://lse6.org/data/saltos-temporales/{filename}",
                "rows": target_rows,
                "row_start": start_row,
                "row_end": end_row,
                "bytes": size,
                "sha256": sha256_file(destination),
            })
            start_row = end_row + 1
        if source.readline():
            raise RuntimeError("Quedaron filas sin repartir")

    reconstructed = hashlib.sha256()
    reconstructed.update(header)
    for item in parts:
        with (OUT / item["filename"]).open("rb") as part:
            part.readline()
            for chunk in iter(lambda: part.read(1024 * 1024), b""):
                reconstructed.update(chunk)
    reconstructed_sha = reconstructed.hexdigest()
    if reconstructed_sha != original_sha:
        raise RuntimeError("Las seis partes no reconstruyen el SHA-256 original")

    header_text = header.decode("utf-8-sig").strip()
    columns = [item.strip().strip('"') for item in header_text.split(",")]
    manifest = {
        "dataset": "LSE6_SALTOS_TEMPORALES.csv",
        "description": "Archivo temporal original dividido en seis CSV válidos e indexables.",
        "source_rows": total_rows,
        "source_bytes": original_bytes,
        "source_sha256": original_sha,
        "reconstructed_sha256": reconstructed_sha,
        "parts": PARTS,
        "header_repeated_in_each_part": True,
        "reconstruction": "Conservar el encabezado de la parte 1 y concatenar las filas de las partes 1 a 6, omitiendo el encabezado repetido de las partes 2 a 6.",
        "columns": columns,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "files": parts,
    }
    (OUT / "index.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    checksum_lines = [f"{item['sha256']}  {item['filename']}" for item in parts]
    checksum_lines.append(f"{original_sha}  LSE6_SALTOS_TEMPORALES.csv [RECONSTRUIDO]")
    (OUT / "SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    reconstruct = '''from pathlib import Path
import hashlib

folder = Path(__file__).resolve().parent
output = folder / "LSE6_SALTOS_TEMPORALES_RECONSTRUIDO.csv"
parts = sorted(folder.glob("LSE6_SALTOS_TEMPORALES_PARTE_*_DE_06.csv"))
if len(parts) != 6:
    raise SystemExit("Se requieren exactamente seis partes")
with output.open("wb") as target:
    for index, part in enumerate(parts):
        with part.open("rb") as source:
            header = source.readline()
            if index == 0:
                target.write(header)
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                target.write(chunk)
digest = hashlib.sha256(output.read_bytes()).hexdigest()
print(output)
print("SHA-256", digest)
'''
    (OUT / "reconstruct_original.py").write_text(reconstruct, encoding="utf-8")
    readme = f'''LSE6_SALTOS_TEMPORALES.csv · ARCHIVO ORIGINAL EN 6 PARTES

Filas de datos: {total_rows:,}
Bytes originales: {original_bytes:,}
SHA-256 original: {original_sha}
Partes: 6 CSV independientes, cada uno con el encabezado original.

Para reconstruir el archivo byte por byte:
    python reconstruct_original.py

El SHA-256 reconstruido debe ser:
    {original_sha}
'''
    (OUT / "README.txt").write_text(readme, encoding="utf-8")

    rows_html = []
    for item in parts:
        rows_html.append(
            "<tr>"
            f"<td>{item['part']:02d}/06</td>"
            f"<td><a href=\"./{html.escape(item['filename'])}\">{html.escape(item['filename'])}</a></td>"
            f"<td>{item['row_start']:,}—{item['row_end']:,}</td>"
            f"<td>{item['rows']:,}</td>"
            f"<td>{item['bytes'] / 1024 / 1024:.2f} MiB</td>"
            f"<td><code>{item['sha256']}</code></td>"
            "</tr>"
        )
    page = f'''<!doctype html>
<html lang="es-MX"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LSE6 · Saltos Temporales · CSV original en 6 partes</title>
<meta name="description" content="LSE6_SALTOS_TEMPORALES.csv dividido en seis partes indexables con hashes y reconstrucción verificable.">
<link rel="canonical" href="https://lse6.org/data/saltos-temporales/">
<style>body{{margin:0;background:#030608;color:#e8f4ff;font-family:Consolas,monospace}}main{{max-width:1400px;margin:auto;padding:32px}}h1{{color:#ff3636}}a{{color:#75ff00}}code{{word-break:break-all;color:#ffc44d}}.meta{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:24px 0}}.meta div,table{{border:1px solid #24404d;background:#061019}}.meta div{{padding:16px}}table{{width:100%;border-collapse:collapse}}th,td{{padding:12px;border-bottom:1px solid #18313d;text-align:left;vertical-align:top}}th{{color:#21dfff}}@media(max-width:900px){{table{{display:block;overflow:auto}}}}</style>
</head><body><main>
<h1>LSE6 · LSE6_SALTOS_TEMPORALES.csv</h1>
<p>Archivo original dividido en seis CSV válidos, descargables, indexables y reconstruibles.</p>
<div class="meta"><div>FILAS<br><strong>{total_rows:,}</strong></div><div>BYTES ORIGINALES<br><strong>{original_bytes:,}</strong></div><div>PARTES<br><strong>6</strong></div><div>SHA-256 ORIGINAL<br><code>{original_sha}</code></div></div>
'''
    page += '''<p><a href="./index.json">ABRIR MANIFIESTO JSON ↗</a> · <a href="./SHA256SUMS.txt">ABRIR HASHES ↗</a> · <a href="./reconstruct_original.py">ABRIR RECONSTRUCTOR ↗</a></p>
<table><thead><tr><th>PARTE</th><th>ARCHIVO</th><th>FILAS ORIGINALES</th><th>REGISTROS</th><th>TAMAÑO</th><th>SHA-256</th></tr></thead><tbody>'''
    page += "".join(rows_html)
    page += '''</tbody></table>
<h2>Reconstrucción exacta</h2>
<p>Conserva el encabezado de la parte 1 y concatena los registros de las seis partes en orden. El script incluido automatiza el proceso y produce el SHA-256 original.</p>
</main></body></html>'''
    (OUT / "index.html").write_text(page, encoding="utf-8")
    return manifest


def main() -> None:
    manifest = split_archive()
    print("CSV_SPLIT_OK")
    print("ROWS", manifest["source_rows"])
    print("SOURCE_SHA256", manifest["source_sha256"])
    for item in manifest["files"]:
        print(item["part"], item["rows"], item["bytes"], item["sha256"])


if __name__ == "__main__":
    main()
