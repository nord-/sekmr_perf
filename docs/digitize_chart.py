"""Helpers for digitizing scanned POH performance charts.

The POH PDF is a pure scan (no text layer), so every chart has to be read
visually. This script does the mechanical parts: rendering a page, locating
the grid lines, and drawing a calibrated overlay (value grid + density
altitude rows) that makes reading the curves reliable. See DIGITIZING.md for
the full recipe.

Requires: pip install pypdfium2 pillow numpy

Usage:
  python digitize_chart.py render  <pdf> <page> <out.png> [--scale 4] [--rotate -90]
  python digitize_chart.py grid    <img.png> <x0> <y0> <x1> <y1>
  python digitize_chart.py overlay <img.png> <out.png> --ysl Y --px1000 K
                                   --xref X --vref V --ppu P
                                   --vlo A --vhi B --dalo C --dahi D
                                   [--zoom 2.2] [--vstep 1] [--label 5]
"""
import argparse
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def render(pdf, page, out, scale=4.0, rotate=-90):
    """Render one PDF page (1-based) to a grayscale PNG, optionally rotated."""
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(pdf)
    img = doc[page - 1].render(scale=scale).to_pil().convert("L")
    if rotate:
        img = img.rotate(rotate, expand=True)
    img.save(out)
    print(out, img.size)


def grid(img, x0, y0, x1, y1, thr_frac=0.45, min_dist=6):
    """Print row/column darkness peaks inside a region of interest.

    Pick a strip that contains only grid (no curves or text). Bold grid lines
    show up as the strongest peaks; their spacing gives px per unit.
    """
    a = 255 - np.asarray(Image.open(img).convert("L"), dtype=float)
    roi = a[y0:y1, x0:x1]

    def peaks(prof, off):
        if prof.max() == 0:
            print("no dark pixels in ROI")
            return []
        thr = prof.max() * thr_frac
        out = []
        for i in range(1, len(prof) - 1):
            if prof[i] >= thr and prof[i] >= prof[i - 1] and prof[i] >= prof[i + 1]:
                if out and i - out[-1][0] < min_dist:
                    if prof[i] > out[-1][1]:
                        out[-1] = (i, prof[i])
                else:
                    out.append((i, prof[i]))
        return [(i + off, round(float(v / prof.max()), 2)) for i, v in out]

    print("ROWS (y, rel strength):", peaks(roi.mean(axis=1), y0))
    print("COLS (x, rel strength):", peaks(roi.mean(axis=0), x0))


def overlay(img, out, ysl, px1000, xref, vref, ppu, vlo, vhi, dalo, dahi,
            zoom=2.2, vstep=1.0, label=5.0):
    """Draw a calibrated value grid and density-altitude rows, then crop + zoom.

    ysl     pixel row of the sea-level / standard-temperature intersection
    px1000  pixels per 1000 ft of density altitude
    xref    pixel column of a known axis value vref; ppu = pixels per unit
    vlo/vhi value range to draw, dalo/dahi density altitude range (ft)
    """
    im = Image.open(img).convert("RGB")
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("arial.ttf", 12)
    except OSError:
        font = ImageFont.load_default()
    x_at = lambda v: xref + (v - vref) * ppu
    y_at = lambda da: ysl - da * px1000 / 1000
    x0, x1, y_top, y_bot = x_at(vlo), x_at(vhi), y_at(dahi), y_at(dalo)

    v = vlo
    while v <= vhi + 1e-9:
        x = x_at(v)
        major = abs(v / label - round(v / label)) < 1e-6
        d.line([(x, y_top), (x, y_bot)], fill=(255, 0, 0) if major else (255, 160, 160), width=1)
        if major:
            d.text((x - 10, y_top + 2), f"{v:g}", fill=(255, 0, 0), font=font)
        v += vstep
    da = dalo
    while da <= dahi:
        y = y_at(da)
        major = da % 1000 == 0
        d.line([(x0, y), (x1, y)], fill=(0, 90, 255) if major else (150, 190, 255), width=1)
        if major:
            d.text((x0 + 2, y - 13), f"{int(da)}", fill=(0, 90, 255), font=font)
        da += 500

    crop = im.crop((int(x0), int(y_top), int(x1), int(y_bot)))
    crop = crop.resize((int(crop.width * zoom), int(crop.height * zoom)), Image.LANCZOS)
    crop.save(out)
    print(out, crop.size)


def main(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("render")
    r.add_argument("pdf"); r.add_argument("page", type=int); r.add_argument("out")
    r.add_argument("--scale", type=float, default=4.0)
    r.add_argument("--rotate", type=int, default=-90, help="degrees; 0 to keep portrait")

    g = sub.add_parser("grid")
    g.add_argument("img")
    for name in ("x0", "y0", "x1", "y1"):
        g.add_argument(name, type=int)

    o = sub.add_parser("overlay")
    o.add_argument("img"); o.add_argument("out")
    for name in ("ysl", "px1000", "xref", "vref", "ppu", "vlo", "vhi", "dalo", "dahi"):
        o.add_argument("--" + name, type=float, required=True)
    o.add_argument("--zoom", type=float, default=2.2)
    o.add_argument("--vstep", type=float, default=1.0, help="minor value grid step (1 kt, 20 RPM, ...)")
    o.add_argument("--label", type=float, default=5.0, help="label every N units")

    a = vars(p.parse_args(argv))
    cmd = a.pop("cmd")
    {"render": render, "grid": grid, "overlay": overlay}[cmd](**a)


if __name__ == "__main__":
    main(sys.argv[1:])
