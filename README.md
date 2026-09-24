# pnwtech-media

Public static asset host for PNWTechnology ventures: blog images, infographics, avatar
renders, video thumbnails. Anything here is public by design. Nothing private, ever.

Design and reasoning: `pnwtech-engineering/playbooks/venture-media-hosting.md`.

## URL pattern

`https://pnwtech-media.vercel.app/<venture>/<kind>/<filename>`

Paste that URL into a Blogger post's raw HTML. No upload step, no API.

## Layout

```
public/
  <venture-slug>/
    blog/        images used in posts
    avatars/     reusable avatar renders
  shared/        portfolio-wide assets
```

Create a venture folder the first time it needs one. Venture slugs match the repo/venture
name (`shipping-with-claude`, `nw-fuel-planner`, `caretier-tires`, `proofing-room`).

## Rules

1. **Never rename or delete a published file.** Posts embed these URLs permanently. A changed
   image gets a new filename; the old one stays.
2. Filenames: `YYYY-MM-DD-short-slug.ext`, lowercase, hyphens.
3. Compress first. WebP or JPEG, aim for under 500 KB. PNG only when transparency or sharp
   line art needs it.
4. Strip EXIF (especially GPS) from photos before committing.
5. Video files do not belong here (GitHub file limits, repo bloat). Host on YouTube; keep only
   the thumbnail here.
6. Only commit assets we have the rights to. Note AI-generated imagery where it matters.
7. In posts, always set `alt` text plus `width` and `height` on the `<img>`.

## Preparing images (`tools/prepare-image.py`)

Runs rules 2 to 4 for you: dated lowercase filename, upright orientation, EXIF/GPS/ICC stripped
(colors converted to sRGB first), resized to at most 1600 px wide, compressed toward 500 KB. It
refuses to overwrite a published file and rejects an unknown venture name (typo guard). It prints
the `<img>` snippet with `width` and `height`; you still write the `alt` text.

One-time setup (Pillow lives in a local venv, nothing here is deployed):

```
python -m venv .venv
.venv/Scripts/python -m pip install -r tools/requirements.txt
```

Use (from the repo root):

```
.venv/Scripts/python tools/prepare-image.py C:/path/photo.jpg --venture proofing-room --slug still-diagram
.venv/Scripts/python tools/prepare-image.py logo.png --venture shared --slug logo --format png
```

Options: `--format webp|jpeg|png` (default webp, keeps transparency; jpeg flattens onto white),
`--kind blog|avatars`, `--max-width`, `--date`, `--new-venture` (first asset for a new venture),
`--dry-run`. Then commit and push as below.

## Publishing

Commit and push to `main`. Vercel deploys automatically; the URL works within a minute.

## Custom domain

Not set up. `pnwtechnology.com`'s live DNS is hosted at NS1 with no known editable login, so a
`media.` subdomain is parked until DNS is moved or another domain is chosen. Until then, URLs
use the `.vercel.app` host, so treat them as long-lived and avoid moving hosts casually.
