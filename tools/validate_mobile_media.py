from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
MAX_DECODED_MB = 160
errors = []
soup = BeautifulSoup(INDEX.read_text(encoding="utf-8-sig"), "html.parser")
local_images = []
mobile_pixels = 0

for img in soup.find_all("img", src=True):
    src = img["src"]
    if src.startswith(("http://", "https://", "data:")):
        continue
    original = ROOT / src.lstrip("./")
    if not original.exists():
        errors.append(f"Original missing: {src}")
        continue
    local_images.append(img)
    picture = img.parent if img.parent and img.parent.name == "picture" else None
    if picture is None or "mobile-picture" not in picture.get("class", []):
        errors.append(f"Missing mobile picture wrapper: {src}")
        continue
    source = picture.find("source", attrs={"media": "(max-width: 900px)"})
    if source is None or not source.get("srcset"):
        errors.append(f"Missing mobile source: {src}")
        continue
    mobile_src = source["srcset"]
    mobile = ROOT / mobile_src.lstrip("./")
    if not mobile.exists():
        errors.append(f"Mobile asset missing: {mobile_src}")
        continue
    try:
        with Image.open(mobile) as media:
            width, height = media.size
        if width > 640:
            errors.append(f"Mobile asset too wide ({width}px): {mobile_src}")
        mobile_pixels += width * height
    except Exception as exc:
        errors.append(f"Unreadable mobile asset {mobile_src}: {exc}")

mobile_mb = mobile_pixels * 4 / 1024 / 1024
if mobile_mb > MAX_DECODED_MB:
    errors.append(f"Mobile decoded memory too high: {mobile_mb:.1f} MB")
if len(local_images) < 60:
    errors.append(f"Unexpected local image count: {len(local_images)}")
if errors:
    print("MOBILE MEDIA VALIDATION FAILED")
    for error in errors[:30]:
        print(" -", error)
    if len(errors) > 30:
        print(f" - ... and {len(errors) - 30} more")
    raise SystemExit(1)

print("MOBILE MEDIA VALIDATION PASSED")
print(f"images={len(local_images)} decoded_mobile_mb={mobile_mb:.1f}")
