from pathlib import Path
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
