# Digitizing POH charts

How the performance tables in this repo were read off the Pilot's Operating Handbook, so the next chart can be done the same way — and so anyone can check the numbers.

## The source

`docs/POH Piper PA 28-181 ARCHER II.pdf` (gitignored — copyrighted, 23 MB, 259 pages, report VB-1120 revised 1985-07-05). It is a pure scan with no text layer: `pdftotext` returns nothing, so nothing can be searched or copied. Every chart has to be rendered as an image and read visually.

Charts digitized so far, with PDF page numbers (the POH's own page numbers are printed on the page):

| Figure | POH page | PDF page | Used for |
|---|---|---|---|
| 5-19 Engine Performance | 5-20 | 105 | `cruiseRPM`, `fuelFlow` |
| 5-21 Speed Power – Performance Cruise | 5-21 | 106 | `cruiseTAS.best_power`, `fullThrottleTAS` |
| 5-23 Speed Power – Economy Cruise | 5-22 | 107 | `cruiseTAS.economy` |

## Tooling

`docs/digitize_chart.py` — three subcommands, needs `pip install pypdfium2 pillow numpy`. Poppler (`pdftoppm`) is not installed on the dev machine, so PDF rendering goes through pypdfium2 instead.

```
python docs/digitize_chart.py render  "<pdf>" 106 p106.png          # 4x scale, rotated -90
python docs/digitize_chart.py grid    p106.png 1700 480 1880 1300   # find grid line pixels
python docs/digitize_chart.py overlay p106.png out.png --ysl 1291 --px1000 65.9 \
        --xref 1275 --vref 100 --ppu 13.28 --vlo 92 --vhi 132 --dalo 0 --dahi 6000
```

## Recipe

### 1. Render

Render the page at `scale=4` (≈1633 × 2400 px) and rotate −90° — the performance charts are printed landscape. At this scale one minor grid square is ≈13.3 px.

### 2. Calibrate the value axis (x)

Run `grid` on a strip that contains only grid lines (no curves, no text — the far right of the right-hand panel usually works). The bold lines show up as the strongest peaks at regular ≈133 px spacing. Match them to the printed axis labels to get `xref`/`vref` (pixel of a known value) and `ppu` (pixels per unit).

**Check which label sits on the first bold line.** The Economy Cruise chart's TAS axis starts at 90 kt where the Performance Cruise chart starts at 100 kt; assuming they were the same put every economy reading 10 kt too high until it was caught against the chart's own worked example.

### 3. Calibrate the altitude axis (y)

The left-hand panel converts OAT + pressure altitude into a vertical position that is linear in **density altitude**. Read the pixel row where the STD. TEMP. line crosses the SEA LEVEL, 4000, 8000 and 12000 ft pressure-altitude lines (zoomed crops of ±60 px around each intersection). The sea-level intersection is `ysl`; the spacing gives `px1000` (≈66 px per 1000 ft at scale 4). Check linearity — the four points should agree within a couple of pixels.

Calibrations found for the three cruise charts (scale 4, rotated −90):

| PDF page | `ysl` | `px1000` | `xref` = value | `ppu` |
|---|---|---|---|---|
| 105 (RPM) | 1243 | 65.9 | 1349 px = 2000 RPM | 0.6625 px/RPM |
| 106 (best power TAS) | 1291 | 65.9 | 1275 px = 100 kt | 13.28 px/kt |
| 107 (economy TAS) | 1237 | 66.0 | 1446 px = 100 kt | 13.26 px/kt |

The scan offsets differ per page, so every page needs its own calibration.

### 4. Read the curves

Automatic curve tracing (thresholding, erosion, darkness profiles) was tried and was not reliable on this scan — the grid lines are nearly as dark as the curves and the curve weight varies. What worked: draw a 1-unit value grid and 500 ft density-altitude rows on top of the image with `overlay`, split into a lower (0–6000 ft) and upper (6000–12000 ft) half at ≈2.2× zoom, and read each curve where it crosses each 1000 ft row. Resolution is about ±0.5 kt / ±5 RPM; call it ±1 kt / ±10 RPM after rounding.

Read the row shared by both halves (6000 ft) in both crops — disagreement there is the quickest sign of a misread.

### 5. Verify against the POH's own examples

Every chart carries a worked example in its margin. Run it through the finished table before trusting anything:

| Example | POH | Table |
|---|---|---|
| 5500 ft / −1 °C / 55 % best power (Fig. 5-21) | 101 kt | 100 kt |
| 6000 ft / 13 °C / 65 % economy (Fig. 5-23) | 116 kt | 116 kt |
| 5500 ft / 4 °C / 65 % (Fig. 5-19) | 2450 RPM | 2440 RPM |

The 1 kt miss on Fig. 5-21 is in the original: the example arrow lands ≈0.7 kt right of the curve it points at.

## What the cruise charts say

- RPM lines (Fig. 5-19) are straight: ≈20.6 RPM per 1000 ft DA from a sea-level base of {55 %: 2167, 60 %: 2246, 65 %: 2328, 70 %: 2397, 75 %: 2466}. The 75 % line ends at ≈8000 ft DA and 70 % at ≈9800 ft — full throttle.
- On both speed-power charts the 75 % curve meets the "2650 RPM or full throttle" line at ≈7500 ft DA and the 65 % curve meets it at 12 000 ft. `maxPowerAvailable()` in the calculator is a straight line through those two points, which also reproduces the 70 % line ending at ≈9800 ft on Fig. 5-19.
- The Economy Cruise chart has no 75 % curve. Fuel flow for 75 % economy (8.8 GPH) is still in the Fig. 5-19 table, so the calculator shows RPM and fuel flow but no TAS for that case.
- Full-throttle TAS (best power) peaks at ≈129 kt around 6000 ft DA; the economy chart's limit line peaks at ≈126 kt around 8000 ft.
