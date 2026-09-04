"""Helpers for digitizing scanned POH performance charts.

The POH PDF is a pure scan (no text layer), so every chart has to be read
visually. This script does the mechanical parts: rendering a page, locating
the grid lines, drawing calibrated overlays that make reading the curves
reliable, and tracing straight guide lines through the grid noise. See
DIGITIZING.md for the full recipe.

Requires: pip install pypdfium2 pillow numpy

Usage:
  python digitize_chart.py render  <pdf> <page> <out.png> [--scale 4] [--rotate -90]
  python digitize_chart.py grid    <img.png> <x0> <y0> <x1> <y1>
  python digitize_chart.py overlay <img.png> <out.png> --ysl Y --px1000 K
                                   --xref X --vref V --ppu P
                                   --vlo A --vhi B --dalo C --dahi D
                                   [--zoom 2.2] [--vstep 1] [--label 5]
  python digitize_chart.py trace   <img.png> --slopes S1,S2,.. --cols X1,X2,..
                                   [--x0 --x1 --y0 --y1] [--thr 120]
  python digitize_chart.py lines   <img.png> --ytop Y --vtop V --pxunit P
                                   --x0c X --pxc C --slopes S1,S2,..
                                   [--tlo -39 --thi 31] [--relmin --relmax] [--mincols 10]
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
    """Draw a calibrated value grid and altitude rows, then crop + zoom.

    ysl     pixel row of the sea-level / standard-temperature intersection
    px1000  pixels per 1000 ft of (density) altitude
    xref    pixel column of a known axis value vref; ppu = pixels per unit
    vlo/vhi value range to draw, dalo/dahi altitude range (ft)
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


def _shift(m, dx, dy):
    out = np.zeros_like(m)
    h, w = m.shape
    out[max(0, -dy):h - max(0, dy), max(0, -dx):w - max(0, dx)] = m[max(0, dy):h - max(0, -dy), max(0, dx):w - max(0, -dx)]
    return out


def directional_mask(img, slopes, thr=120):
    """Dark pixels that continue along a diagonal of one of the given slopes.

    Grid lines are axis-aligned and text is short, so requiring a dark pixel at
    +-9/+-18 px and +-13/+-26 px along the diagonal (slope = dy/dx, positive =
    down-right) keeps mostly the sloping guide lines. Slopes flatter than ~0.4
    px/px start to pass thick horizontal grid lines; use the row/column methods
    instead.
    """
    a = np.asarray(Image.open(img).convert("L"), dtype=np.uint8)
    d = a < thr
    keep = np.zeros_like(d)
    for s in slopes:
        for dx in (9, 13):
            dy = int(round(s * dx))
            keep |= d & _shift(d, dx, dy) & _shift(d, -dx, -dy) & _shift(d, 2 * dx, 2 * dy) & _shift(d, -2 * dx, -2 * dy)
    return keep


def column_crossings(mask, x, y0=0, y1=None):
    """Centres of the mask runs in a 3 px wide column."""
    col = mask[y0:y1, x - 1:x + 2].any(axis=1)
    out, start = [], None
    for i, b in enumerate(col):
        if b and start is None:
            start = i
        if (not b or i == len(col) - 1) and start is not None:
            end = i if b else i - 1
            if end - start >= 1:
                out.append((start + end) / 2 + y0)
            start = None
    return out


def trace(img, slopes, cols, x0=0, x1=None, y0=0, y1=None, thr=120):
    """Print where the sloping guide lines cross each pixel column.

    Pick columns between vertical grid lines (a column on a grid line reports
    every horizontal grid crossing as well). Output is pixel rows; convert with
    the axis calibration.
    """
    mask = directional_mask(img, slopes, thr)
    if x1:
        mask[:, x1:] = False
    mask[:, :x0] = False
    for x in cols:
        ys = column_crossings(mask, int(round(x)), y0, y1)
        print(f"x={x:g}: " + " ".join(f"{y:.0f}" for y in ys))


def lines(img, ytop, vtop, pxunit, x0c, pxc, slopes, tlo=-39, thi=31, relmin=0.0, relmax=1e9, mincols=10, tol=0.012):
    """Seed-free straight-line finder for the left panel of a takeoff/landing chart.

    Converts directional-mask crossings at every second degC to chart values
    (value = vtop - (y - ytop)/pxunit), then keeps every line value = a + b*OAT
    supported by at least `mincols` columns and whose relative slope b/a lies
    in [relmin, relmax]. Match the surviving lines to the chart's labels by
    order and by the chart's worked example.
    """
    mask = directional_mask(img, slopes)
    pts = []
    for t in range(tlo, thi + 1, 2):
        x = int(round(x0c + t * pxc))
        pts += [(t, vtop - (y - ytop) / pxunit) for y in column_crossings(mask, x)]
    p = np.array(pts)
    cand = []
    for i in range(len(p)):
        for j in range(i + 1, len(p)):
            t1, v1 = p[i]
            t2, v2 = p[j]
            if abs(t2 - t1) < 24:
                continue
            b = (v2 - v1) / (t2 - t1)
            a = v1 - b * t1
            if a <= 0 or not (relmin <= b / a <= relmax):
                continue
            pred = a + b * p[:, 0]
            sup = np.abs(p[:, 1] - pred) / pred < tol
            cols = len(set(p[sup, 0]))
            if cols >= mincols:
                cand.append((cols, a, b))
    cand.sort(reverse=True)
    found = []
    for cols, a, b in cand:
        if any(abs(a - a2) / a2 < 0.04 and abs((a + 20 * b) - (a2 + 20 * b2)) / (a2 + 20 * b2) < 0.04 for _, a2, b2 in found):
            continue
        pred = a + b * p[:, 0]
        s = p[np.abs(p[:, 1] - pred) / pred < tol]
        (a, b), _, _, _ = np.linalg.lstsq(np.c_[np.ones(len(s)), s[:, 0]], s[:, 1], rcond=None)
        found.append((cols, a, b))
    found.sort(key=lambda f: f[1])
    print("value = a + b*OAT   (cols = supporting OAT columns); values at OAT -40..30:")
    for cols, a, b in found:
        print(f"  a={a:8.1f} b={b:6.2f} cols={cols:2d}  " + " ".join(f"{a + b * t:6.0f}" for t in range(-40, 31, 10)))


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

    t = sub.add_parser("trace")
    t.add_argument("img")
    t.add_argument("--slopes", required=True, help="comma-separated dy/dx in px (positive = down-right)")
    t.add_argument("--cols", required=True, help="comma-separated pixel columns")
    for name in ("x0", "x1", "y0", "y1"):
        t.add_argument("--" + name, type=int, default=None)
    t.add_argument("--thr", type=int, default=120)

    ln = sub.add_parser("lines")
    ln.add_argument("img")
    for name in ("ytop", "vtop", "pxunit", "x0c", "pxc"):
        ln.add_argument("--" + name, type=float, required=True)
    ln.add_argument("--slopes", required=True)
    ln.add_argument("--tlo", type=int, default=-39); ln.add_argument("--thi", type=int, default=31)
    ln.add_argument("--relmin", type=float, default=0.0); ln.add_argument("--relmax", type=float, default=1e9)
    ln.add_argument("--mincols", type=int, default=10)

    a = vars(p.parse_args(argv))
    cmd = a.pop("cmd")
    if "slopes" in a:
        a["slopes"] = [float(v) for v in a["slopes"].split(",")]
    if "cols" in a:
        a["cols"] = [float(v) for v in a["cols"].split(",")]
    if cmd == "trace":
        a = {k: v for k, v in a.items() if v is not None}
    {"render": render, "grid": grid, "overlay": overlay, "trace": trace, "lines": lines}[cmd](**a)


if __name__ == "__main__":
    main(sys.argv[1:])
