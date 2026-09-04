# Digitizing POH charts

How the performance tables in this repo were read off the Pilot's Operating Handbook, so the next chart can be done the same way — and so anyone can check the numbers.

## The source

`docs/POH Piper PA 28-181 ARCHER II.pdf` (gitignored — copyrighted, 23 MB, 259 pages, report VB-1120 revised 1985-07-05). It is a pure scan with no text layer: `pdftotext` returns nothing, so nothing can be searched or copied. Every chart has to be rendered as an image and read visually or with the pixel tools below.

Charts digitized so far, with PDF page numbers (the POH's own page numbers are printed on the page):

| Figure | PDF page | Used for |
|---|---|---|
| 5-7 Takeoff over 50 ft, 0° flaps | 99 | `CHARTS.TB3` |
| 5-9 Takeoff over 50 ft, 25° flaps | 100 | `CHARTS.TB4` |
| 5-11 Takeoff ground roll, 0° flaps | 101 | `CHARTS.TB1` |
| 5-13 Takeoff ground roll, 25° flaps | 102 | `CHARTS.TB2` |
| 5-15 Climb Performance (rate of climb) | 103 | `rocChart` |
| 5-17 Time, Distance and Fuel to Climb | 104 | `climbChart` |
| 5-19 Engine Performance | 105 | `cruiseRPM`, `fuelFlow` |
| 5-21 Speed Power – Performance Cruise | 106 | `cruiseTAS.best_power`, `fullThrottleTAS` |
| 5-23 Speed Power – Economy Cruise | 107 | `cruiseTAS.economy` |
| 5-31 Time, Distance and Fuel to Descend | 111 | `DESCENT_PER_1000FT` |
| 5-35 Landing over 50 ft | 113 | `CHARTS.LB2` |
| 5-37 Landing ground roll | 114 | `CHARTS.LB1` |

## Tooling

`docs/digitize_chart.py` — five subcommands, needs `pip install pypdfium2 pillow numpy`. Poppler (`pdftoppm`) is not installed on the dev machine, so PDF rendering goes through pypdfium2 instead.

```
python docs/digitize_chart.py render  "<pdf>" 106 p106.png          # 4x scale, rotated -90
python docs/digitize_chart.py grid    p106.png 1700 480 1880 1300   # find grid line pixels
python docs/digitize_chart.py overlay p106.png out.png --ysl 1291 --px1000 65.9 \
        --xref 1275 --vref 100 --ppu 13.28 --vlo 92 --vhi 132 --dalo 0 --dahi 6000
python docs/digitize_chart.py trace   p99.png --slopes 0.35,0.45,0.55 --cols 1893,2098 \
        --x0 1877 --x1 2110 --y0 373 --y1 1254                        # sloping guide lines
python docs/digitize_chart.py lines   p101.png --ytop 524 --vtop 2400 --pxunit 0.368 \
        --x0c 765 --pxc 7.25 --slopes=-0.7,-0.9,-1.1,-1.3,-1.5 --relmin 0.008 --relmax 0.022
```

## General recipe

### 1. Render

Render the page at `scale=4` (≈1633 × 2400 px) and rotate −90° — the performance charts are printed landscape. At this scale one minor grid square is ≈13.3–14.6 px depending on the chart.

### 2. Calibrate the value axis

Run `grid` on a strip that contains only grid lines (no curves, no text). The bold lines show up as the strongest peaks at regular spacing. Match them to the printed axis labels to get a reference pixel for a known value and the pixels per unit.

**Check which label sits on the first bold line.** The Economy Cruise chart's TAS axis starts at 90 kt where the Performance Cruise chart starts at 100 kt; assuming they were the same put every economy reading 10 kt too high until it was caught against the chart's own worked example.

### 3. Calibrate the altitude axis

Charts with a left-hand OAT panel put altitude on a vertical scale that is linear in pixels. Read the pixel row where the STD. TEMP. line crosses the sea level, 4000, 8000 and 12000 ft pressure-altitude lines (zoomed ±60 px tiles around each intersection). The sea-level intersection is `ysl`, the spacing gives `px1000`; check the four points agree within a couple of pixels. The scan offsets differ per page, so every page needs its own calibration.

### 4. Read the curves

Automatic curve tracing by thresholding alone is not reliable on this scan — the grid lines are nearly as dark as the curves. Two things worked:

- **Visual read-off on an overlay.** `overlay` draws a 1-unit value grid and altitude rows on the image at ~2.2× zoom. Read each curve where it crosses each row. Precision about ±0.5 kt / ±5 RPM / ±0.5 min.
- **Directional tracing** (`trace`, `lines`). Sloping guide lines survive a filter that requires a dark pixel ±9 and ±18 px along the line's own slope, while the axis-aligned grid and short text do not. Sample the surviving mask at pixel columns *between* grid lines. Slopes flatter than ~0.4 px/px let thick horizontal grid lines through; for those (climb/descent left panels) fall back to tiles and the chart's own worked example.

### 5. Verify against the POH's own examples

Every chart carries a worked example in its margin. Run it through the finished tables before trusting anything — and check that the components agree, not only the product (see "Compensating errors" below).

## Cruise charts (Fig. 5-19, 5-21, 5-23)

Calibrations found (scale 4, rotated −90):

| PDF page | `ysl` | `px1000` | `xref` = value | `ppu` |
|---|---|---|---|---|
| 105 (RPM) | 1243 | 65.9 | 1349 px = 2000 RPM | 0.6625 px/RPM |
| 106 (best power TAS) | 1291 | 65.9 | 1275 px = 100 kt | 13.28 px/kt |
| 107 (economy TAS) | 1237 | 66.0 | 1446 px = 100 kt | 13.26 px/kt |

| Example | POH | Table |
|---|---|---|
| 5500 ft / −1 °C / 55 % best power (Fig. 5-21) | 101 kt | 100 kt |
| 6000 ft / 13 °C / 65 % economy (Fig. 5-23) | 116 kt | 116 kt |
| 5500 ft / 4 °C / 65 % (Fig. 5-19) | 2450 RPM | 2440 RPM |

RPM lines are straight (≈20.6 RPM per 1000 ft DA); the 75 % curve meets the full-throttle line at ≈7500 ft DA and 65 % at 12 000 ft on both speed-power charts; the Economy chart has no 75 % curve.

## Takeoff and landing charts (Fig. 5-7, 5-9, 5-11, 5-13, 5-35, 5-37)

Three panels each: (1) pressure-altitude lines against OAT, (2) weight guide lines from the 2550 lbs reference down to 2000 lbs, (3) wind guide lines from the zero-wind reference, headwind to 15 kt and tailwind to 5 kt. The OAT axis runs −40..+30 °C only.

The model in `pa28_takeoff_landing.html` follows the panels: `distance = line(PA, OAT) × wt^((2550−W)/100) × (1 ∓ k·wind) × surface`.

- **Pressure-altitude lines are straight in OAT** — `lines` finds them without seeds (values `a + b·OAT` at 1000 ft steps). Identify the survivors by order and by the worked example; the sea-level line often needs a targeted refit because the "SEA LEVEL" label sits on it. The lines are only drawn down to about 875 ft (Fig. 5-11) / 810 ft (Fig. 5-13); below that the calculator extrapolates and flags.
- **Weight guide lines are a constant ratio per 100 lbs** regardless of distance level (checked on 6–8 lines per chart): 0.895 (Fig. 5-7), 0.918 (5-9), 0.909 (5-11), 0.918 (5-13), 0.974 (5-35), 0.96 (5-37). Takeoff distance therefore falls by ~40 % from 2550 to 2000 lbs; landing over 50 ft only ~13 % because the 66 KIAS approach speed is fixed.
- **Wind guide lines are straight**, so the factor is linear per knot: headwind 1.18 % (5-7), 1.5 % (5-9), 1.6 % (5-11), 1.7 % (5-13), 1.5 % (5-35), 1.75 % (5-37); tailwind 4.3–6 %/kt, charted to 5 kt only. On the ground-roll charts the lowest lines have a somewhat larger relative slope than the proportional model gives (≈−5 % at 15 kt for the shortest distances).

Calibrations (scale 4, rotated −90; `ytop` = pixel row of the top distance label, `pxunit` = px/ft):

| PDF page | `ytop` = value | `pxunit` | OAT 0 °C at | px/°C | 2500 lbs at | px/lb | zero wind at | px/kt |
|---|---|---|---|---|---|---|---|---|
| 99 (Fig. 5-7) | 373 = 4500 | 0.2937 | 931 | 7.31 | 1370 | 0.733 | 1882 | 14.6 |
| 100 (Fig. 5-9) | 525 = 3400 | 0.3642 | 896 | 7.30 | 1336 | 0.731 | 1849 | 14.6 |
| 101 (Fig. 5-11) | 524 = 2400 | 0.368 | 765 | 7.25 | 1129 | 0.7375 | 1645 | 14.67 |
| 102 (Fig. 5-13) | 553 = 2400 | 0.366 | 882 | 7.29 | 1322 | 0.731 | 1835 | 14.6 |
| 113 (Fig. 5-35) | 404 = 1800 | 1.495 | 763 | 7.25 | 1129 | 0.73 | 1643 | 14.67 |
| 114 (Fig. 5-37) | 462 = 1200 | 1.463 | 884 | 7.28 | 1250 | 0.73 | 1762 | 14.7 |

| Example | POH | Model |
|---|---|---|
| Fig. 5-7: 2000 ft / 21 °C / 2400 lbs / 15 kt HW | 1900 | 1870 |
| Fig. 5-9: 2000 ft / 21 °C / 2400 lbs / 8 kt HW | 1860 | 1853 |
| Fig. 5-11: 2000 ft / 21 °C / 2400 lbs / 8 kt HW | 1100 | 1117 |
| Fig. 5-13: 2000 ft / 21 °C / 2400 lbs / 10 kt HW | 950 | 952 |
| Fig. 5-35: 2300 ft / 21 °C / 2264 lbs / 5 kt HW | 1290 | 1285 |
| Fig. 5-37: 2300 ft / 21 °C / 2264 lbs / 5 kt HW | 825 | 826 |

Sea level, ISA, 2550 lbs, zero wind against Piper's specification sheet: takeoff ground roll 25° flaps 853 ft (spec 870), over 50 ft 1616 ft (spec 1625), landing ground roll 915 ft (spec 925), landing over 50 ft 1412 ft (spec 1390).

### Compensating errors

The previous tables matched all six worked examples within 1 % and were still wrong by 8–12 % elsewhere: the base tables were 5–9 % low at warm temperatures, the takeoff weight factors half as strong as the chart (0.73 vs ≈0.58 at 2000 lbs), and the headwind factors 3–5 % too strong — three errors that cancelled exactly at the example points. Always check the panels separately: read the base distance at the reference line, the weight-corrected distance at the zero-wind line, and the final value, and compare each against the model.

## Climb and descent charts (Fig. 5-15, 5-17, 5-31)

These share the layout: a left panel of pressure-altitude lines against OAT and a right panel of curves against the same vertical scale. The vertical scale is a *chart altitude* `H` that equals pressure altitude at ISA (the STD. TEMP. line) and moves with OAT by a slope that grows with altitude — it is not density altitude except on Fig. 5-15. Because the curves are read at `H`, the calculator converts PA + OAT to `H` first (`climbChartAlt`, `descentChartAlt`, `rocChartAlt`) and subtracts cumulative values, instead of applying a percentage per °C.

| PDF page | `ysl` (H = 0) | `px1000` | OAT 0 °C at | px/°C | right-panel 0 at | px/unit |
|---|---|---|---|---|---|---|
| 103 (Fig. 5-15) | 1246 | 64.9 | 843 | 7.25 | 1283 | 0.7295 px/fpm |
| 104 (Fig. 5-17) | 1364 | 74.1 | 845 | 7.25 | 1282 | 14.65 |
| 111 (Fig. 5-31) | 1304 | 73.2 | 655 | 7.19 | 947 | 14.63 |

- The pressure-altitude lines are too flat for `trace`; their slopes were read from ±100 px tiles and pinned with the worked examples: Fig. 5-17 ≈ 4 + 7·PA/1000 ft per °C (the lines rise with OAT), Fig. 5-31 ≈ 0 at sea level to −40 ft/°C at 12 000 ft (the lines fall with OAT), Fig. 5-15 ≈ 100 ft/°C (density altitude).
- Fig. 5-17 has one set of curves; the "mixture leaned / full rich" boundary is a procedure note. The chart's start, taxi and takeoff fuel allowance (≈0.6 gal, the sea-level intercept) cancels out in the cruise-minus-departure subtraction, so it is not included in the calculator's climb-fuel result.
- Fig. 5-31's three curves are straight lines: 2.38 min, 5.73 nm and 0.29 gal per 1000 ft of `H` (their sea-level intercepts cancel in cruise − destination).
- Fig. 5-15's rate-of-climb line is nearly straight, ≈743 − 0.0415·H ft/min.

| Example | POH | Model |
|---|---|---|
| Fig. 5-17: 2000 ft / 21 °C → 6000 ft / 13 °C | 8.5 min, 11.5 nm, 1.0 gal | 8.3 min, 11.2 nm, 1.05 gal |
| Fig. 5-31: 6000 ft / 13 °C → 2300 ft / 21 °C | 8.5 min, 20.5 nm, 1.0 gal | 8.6 min, 20.8 nm, 1.05 gal |
| Fig. 5-15: 3600 ft / −1 °C | 620 ft/min | 622 ft/min |
