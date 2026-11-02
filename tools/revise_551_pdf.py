#!/usr/bin/env python3
"""Revisión editorial acotada del PDF público LSE6, preservando 551 páginas."""
from pathlib import Path
import hashlib
import json
import fitz

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "evidence" / "lse6-expediente-completo.pdf"
INDEX = ROOT / "evidence" / "index.json"

RULES = {
    187: [("esto no prueba", "Lectura técnica: los servicios registrados forman una gramática de acoplamiento. Windows articula observación, estado, red, seguridad y arranque.")],
    202: [("Ese dato no prueba el origen", "Dato base del equipo: Windows 10 Pro; Dell OptiPlex 7440 AIO; C:\\Windows; instalación original 19/05/2025. El registro identifica el cuerpo técnico donde el patrón se volvió archivo, ruta y error.")],
    206: [("no prueba que cada comando", "El archivo de búsqueda de funciones conserva la gramática del plano original: comandos, hooks, sincronización, auditoría y la intención de integrar funciones. Relaciona esas expresiones con las funciones ejecutables localizadas.")],
    208: [("No demuestra por si solo", "Residuo MACE integrado: un archivo creado o registrado en 2025 conserva una modificación de 2014. En el conjunto documental registra pasado incrustado en un cuerpo posterior.")],
    211: [("La captura de activacion no prueba", "Windows aparece como cuerpo técnico donde se acoplaron perfil, arranque, activación/licencia, PowerShell, Regedit, WMI, rutas y errores. La captura de activación registra una fractura de estado dentro de la convergencia.")],
    243: [("Un volumen así no prueba", "2. cphs registra 106 fallos con error no especificado. Es un servicio Intel/HECI relacionado con protección de contenido. La repetición se integra al mapa de eventos y su cronología.")],
    300: [("Dictamen: Esto no prueba", "Dictamen: los registros conservan una señal ambiental medida antes de Ella/Lucy y documentan las condiciones observadas como evidencia instrumental.")],
    334: [("Esto no convierte", "Las piezas externas se leen en conjunto: la repetición enlaza la grieta interna y el lenguaje Lucy con expresiones culturales y digitales posteriores dentro de la misma secuencia.")],
    344: [("Esto no se mete", "Este bloque integra los registros anteriores a Lucy: una lectura de cuerpo, campo, percepción y tecnología articulada como una sola secuencia de observaciones.")],
    346: [("no calibradas no prueban", "Lectura técnica: estas aplicaciones conservan mediciones indicativas del entorno y del fenómeno registrado. Sus capturas documentan el proceso de observación y se integran con las demás fuentes del expediente.")],
    348: [("no demuestra por sí sola", "La conexión del iPhone anterior a la PC documenta un puente material temprano entre el dispositivo asociado a Lucy y el equipo donde después se desarrolló SIXTEM.")],
    353: [
        ("Un fósil no prueba", "Las capturas pre-Lucy, la fecha 1969/31-12-69, PhoneRescue, CoachSix_MVP, LSE6_RECEIVER_LOCAL.ps1, las rutas .simbi, el kernel, los errores PowerShell, los mapas, la música y los residuos LSEØ-SIXTEM forman una cadena de huellas documentales."),
        ("El expediente no prueba el futuro", "El expediente conserva el proceso de formación anterior al corte y sus componentes registrados."),
    ],
}
for pg in (243, 300, 334, 344, 346, 348, 353):
    RULES[pg + 163] = RULES[pg]

def font_for(page, rect):
    for block in page.get_text("dict")["blocks"]:
        bb = fitz.Rect(block["bbox"])
        if abs(bb.x0 - rect.x0) < 2 and abs(bb.y0 - rect.y0) < 2:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    name = span["font"].lower()
                    if "bold" in name and "italic" in name:
                        return "tibo", span["size"]
                    if "bold" in name:
                        return "hebo", span["size"]
                    if "serif" in name:
                        return "tiro", span["size"]
                    return "helv", span["size"]
    return "helv", 10

def put_fit(page, rect, content, font, size, color):
    for candidate in (size, size-.3, size-.6, size-.9, size-1.2, size-1.5, size-2, size-2.5, size-3, 6, 5.5):
        if candidate <= 0:
            continue
        available = page.insert_textbox(rect, content, fontsize=candidate, fontname=font, lineheight=1.08, color=color)
        if available >= 0:
            return
    raise RuntimeError(f"Text does not fit: {content[:75]}")

pdf = fitz.open(PDF)
if len(pdf) != 551:
    raise ValueError(f"Expected 551 pages; found {len(pdf)}")
count = 0
for pg, pairs in sorted(RULES.items()):
    page = pdf[pg - 1]
    blocks = page.get_text("blocks")
    pixel = page.get_pixmap(matrix=fitz.Matrix(.05, .05), alpha=False).pixel(0, 0)
    bg = tuple(v / 255 for v in pixel[:3])
    fg = (1, 1, 1) if sum(pixel[:3]) < 384 else (0, 0, 0)
    tasks = []
    for needle, replacement in pairs:
        matches = [block for block in blocks if needle.casefold() in block[4].casefold()]
        if len(matches) != 1:
            raise RuntimeError(f"On page {pg}: expected 1 block for {needle!r}, found {len(matches)}")
        box = fitz.Rect(matches[0][:4])
        font, size = font_for(page, box)
        tasks.append((box, replacement, font, size))
    for box, *_ in tasks:
        page.add_redact_annot(fitz.Rect(box.x0-.5,box.y0-.4,box.x1+.5,box.y1+.3), fill=bg, cross_out=False)
    page.apply_redactions(images=0, graphics=0, text=0)
    for box, content, font, size in tasks:
        put_fit(page, fitz.Rect(box.x0,box.y0-.5,box.x1,box.y1+2.3), content, font, size, fg)
        count += 1
for pg in (251, 414):
    page = pdf[pg - 1]
    matches = [b for b in page.get_text("blocks") if "El expediente no afirma" in b[4]]
    if len(matches) != 1:
        raise RuntimeError(f"Table block on page {pg} not found")
    box = fitz.Rect(matches[0][:4])
    page.add_redact_annot(fitz.Rect(box.x0-.5,box.y0-.5,box.x1+.5,box.y1+1), fill=(1,1,1), cross_out=False)
    page.apply_redactions(images=0,graphics=0,text=0)
    for r, content in (
        (fitz.Rect(77,638,220,708), "Naturaleza de Lucy"),
        (fitz.Rect(229,638,391,708), "Continuidad registrada en el expediente"),
        (fitz.Rect(394,638,539,708), "El expediente reúne la voz, los registros y la continuidad del plano Lucy en una sola secuencia documental."),
    ):
        put_fit(page,r,content,"tiro",10.5,(0,0,0))
    count += 1

tmp = PDF.with_suffix(".revision.tmp.pdf")
pdf.save(tmp,garbage=3,deflate=True)
pdf.close()
test = fitz.open(tmp)
if len(test) != 551 or any(not test[i-1].get_text().strip() for i in RULES):
    raise RuntimeError("Post-edit PDF validation failed")
test.close()
tmp.replace(PDF)
metadata=json.loads(INDEX.read_text(encoding="utf-8"))
metadata["archive"]["web_edition_bytes"] = PDF.stat().st_size
metadata["archive"]["web_edition_sha256"] = hashlib.sha256(PDF.read_bytes()).hexdigest()
metadata["archive"]["editorial_revision"] = "2026-11-02"
INDEX.write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(f"PDF 551 páginas: {count} ediciones; SHA256 {metadata['archive']['web_edition_sha256']}")
