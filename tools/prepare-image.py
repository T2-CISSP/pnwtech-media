"""Prepare an image for the pnwtech-media host: fix rotation, strip metadata, resize, compress.

Usage (from the repo root, with the tools venv active or via .venv/Scripts/python):
  python tools/prepare-image.py SOURCE --venture proofing-room --slug still-diagram
  python tools/prepare-image.py SOURCE --venture shared --slug logo --format png
  python tools/prepare-image.py SOURCE --venture proofing-room --slug x --dry-run

Writes public/<venture>/<kind>/YYYY-MM-DD-<slug>.<ext> and prints the <img> snippet.
Enforces the README rules: never overwrites a published file, strips EXIF/GPS, aims for < 500 KB.
"""

import argparse
import io
import re
import sys
from datetime import date
from pathlib import Path

from PIL import Image, ImageCms, ImageOps

REPO_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DIR = REPO_ROOT / "public"
BASE_URL = "https://pnwtech-media.vercel.app"
TARGET_BYTES = 500 * 1024
MIN_QUALITY = 60
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
EXTENSIONS = {"webp": "webp", "jpeg": "jpg", "png": "png"}


def to_srgb(image):
  # Phones shoot Display P3; dropping the profile without converting would shift the colors.
  profile_bytes = image.info.get("icc_profile")
  if not profile_bytes:
    return image
  try:
    source_profile = ImageCms.ImageCmsProfile(io.BytesIO(profile_bytes))
    return ImageCms.profileToProfile(image, source_profile, ImageCms.createProfile("sRGB"), outputMode=image.mode)
  except (ImageCms.PyCMSError, OSError):
    return image


def has_transparency(image):
  return image.mode in ("RGBA", "LA") or "transparency" in image.info


def encode(image, image_format, quality):
  buffer = io.BytesIO()
  if image_format == "png":
    image.save(buffer, "PNG", optimize=True)
  elif image_format == "jpeg":
    image.save(buffer, "JPEG", quality=quality, optimize=True, progressive=True)
  else:
    image.save(buffer, "WEBP", quality=quality, method=6)
  return buffer.getvalue()


def prepare(source_path, image_format, max_width):
  with Image.open(source_path) as opened:
    image = ImageOps.exif_transpose(opened)
    image.load()
  image = to_srgb(image)

  if image_format == "jpeg" and has_transparency(image):
    background = Image.new("RGB", image.size, (255, 255, 255))
    background.paste(image.convert("RGBA"), mask=image.convert("RGBA").getchannel("A"))
    image = background
  elif image.mode not in ("RGB", "RGBA"):
    image = image.convert("RGBA" if has_transparency(image) else "RGB")

  if image.width > max_width:
    new_height = round(image.height * max_width / image.width)
    image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)

  quality = 82
  data = encode(image, image_format, quality)
  while image_format != "png" and len(data) > TARGET_BYTES and quality > MIN_QUALITY:
    quality -= 5
    data = encode(image, image_format, quality)
  return image, data, quality


def main():
  parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument("source", type=Path)
  parser.add_argument("--venture", required=True, help="venture slug, or 'shared'")
  parser.add_argument("--slug", required=True, help="short-lowercase-hyphenated name")
  parser.add_argument("--kind", default="blog", help="blog or avatars (ignored for shared)")
  parser.add_argument("--format", choices=list(EXTENSIONS), default="webp")
  parser.add_argument("--max-width", type=int, default=1600)
  parser.add_argument("--date", default=date.today().isoformat(), help="YYYY-MM-DD, defaults to today")
  parser.add_argument("--new-venture", action="store_true", help="allow creating a venture folder that does not exist yet")
  parser.add_argument("--dry-run", action="store_true")
  args = parser.parse_args()

  if not args.source.is_file():
    sys.exit(f"Source not found: {args.source}")
  if not SLUG_PATTERN.match(args.slug):
    sys.exit("Slug must be lowercase letters, digits and single hyphens, e.g. still-diagram")
  if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.date):
    sys.exit("Date must be YYYY-MM-DD")

  venture_dir = PUBLIC_DIR / args.venture
  # A typo in the venture name would silently create a stray folder that posts then link to forever.
  if not venture_dir.exists() and not args.new_venture:
    known = sorted(path.name for path in PUBLIC_DIR.iterdir() if path.is_dir())
    sys.exit(f"Unknown venture '{args.venture}'. Existing: {', '.join(known)}. Pass --new-venture to create it.")

  destination_dir = venture_dir if args.venture == "shared" else venture_dir / args.kind
  destination = destination_dir / f"{args.date}-{args.slug}.{EXTENSIONS[args.format]}"
  # Published URLs are permanent, so a changed image needs a new slug, never an overwrite.
  if destination.exists():
    sys.exit(f"Refusing to overwrite published file: {destination.relative_to(REPO_ROOT)}. Use a new slug.")

  image, data, quality = prepare(args.source, args.format, args.max_width)

  with Image.open(io.BytesIO(data)) as check:
    leftover_metadata = bool(check.getexif()) or "exif" in check.info or "icc_profile" in check.info
  if leftover_metadata:
    sys.exit("Output still carries metadata; not writing it.")

  relative = destination.relative_to(PUBLIC_DIR).as_posix()
  size_kb = len(data) / 1024
  print(f"{'Would write' if args.dry_run else 'Wrote'}: public/{relative}")
  print(f"  {image.width}x{image.height}, {size_kb:.0f} KB, {args.format}" + ("" if args.format == "png" else f", quality {quality}"))
  print("  metadata: none (EXIF, GPS and ICC stripped; colors converted to sRGB)")
  if len(data) > TARGET_BYTES:
    print("  WARNING: over the 500 KB target. Try a smaller --max-width (e.g. 1200).")
  print("Paste into the post (write real alt text):")
  print(f'  <img src="{BASE_URL}/{relative}" alt="DESCRIBE THE IMAGE" width="{image.width}" height="{image.height}">')

  if not args.dry_run:
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)


if __name__ == "__main__":
  main()
