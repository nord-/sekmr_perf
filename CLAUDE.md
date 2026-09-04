# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Flight planning and performance tools for a PA-28-181 Archer II aircraft (registration SE-KMR). Three standalone HTML files — no build system, no dependencies, no server required. Each file is a self-contained single-page application (HTML + CSS + inline JS) that runs directly in the browser.

## Files

- **OFP_PA28_SEKMR_fillable.html** — Operational Flight Plan (OFP). Navigation log with wind triangle solver, fuel planning (VFR/IFR reserves), mass & balance with CG envelope chart (canvas). Save/load via JSON, print-friendly A4 layout.
- **pa28_performance_calculator.html** — Climb/Cruise/Descent performance calculator. Tabbed UI with range sliders. Interpolates POH table data for time, distance, fuel, TAS, RPM, and fuel flow.
- **pa28_takeoff_landing.html** — Takeoff and landing distance calculator. Accounts for OAT, pressure altitude, weight, wind, flap setting, and surface conditions (grass, water/slush, wet snow, powder).

## Architecture

All computation is client-side JavaScript. No external JS libraries — only Google Fonts (IBM Plex Mono, DM Sans/IBM Plex Sans) loaded via CSS.

### Design patterns used across files

- **POH data as JS lookup tables** — Performance data is digitized from Pilot's Operating Handbook charts into nested objects keyed by altitude (ft), with arrays of `[temperature, value]` pairs or `{ power%: value }` objects.
- **Linear interpolation** — `lerp()` / `lerpNested()` / `it()` functions interpolate between data points for altitude, temperature, power setting, and weight. The climb/cruise/descent calculator uses a "cumulative from sea level" subtraction method: `result = lerp(cruiseAlt) - lerp(departureAlt)`, evaluated at the POH chart altitude `H` rather than pressure altitude — `climbChartAlt()` / `descentChartAlt()` / `rocChartAlt()` convert PA + OAT to H the way each chart's left panel does (Fig. 5-17, 5-31, 5-15).
- **Temperature correction** — ISA deviation (`OAT - ISA_temp`) is computed via `getISA(alt) = 15 - alt * 1.98/1000`. Climb, descent and ROC apply it through the chart altitude (see below); the takeoff/landing charts use OAT directly.
- **Density altitude** — `DA = PA + 120 * (OAT - ISA_temp)`, used in cruise TAS and RPM lookups. Cruise tables (`cruiseTAS.best_power` / `cruiseTAS.economy`, `cruiseRPM`, `fullThrottleTAS`) are digitized from POH Fig. 5-19/5-21/5-23 and keyed by DA in 1000 ft steps; `maxPowerAvailable(DA)` clamps requested power to the full-throttle limit (75% to ~7500 ft DA, 65% at 12 000 ft).
- **Event-driven recalculation** — Input events trigger cascading recalcs. In the OFP, changing a single field (e.g., wind direction) propagates through: wind triangle -> WCA/GS -> time_leg -> fuel_leg -> fuel table -> mass & balance -> CG chart.

### OFP-specific details

- Navigation log rows are generated dynamically via `createNavRow()`. Row types: `data`, `header` (alternate section), `totals`.
- Wind triangle: `WCA = arcsin(wspd * sin(wdir - TT) / TAS)`, `GS = TAS * cos(WCA) - wspd * cos(wdir - TT)`.
- Variation parsing accepts both `E4`/`W5` and `+/-` formats.
- Mass & balance constants: BEM 737 kg @ 223.7 cm, AVGAS density 0.719 kg/L, fuel arm 241.3 cm. CG envelope drawn on canvas with points for ZFM, TOM, LDG mass.
- Fuel reserves: VFR 30 min, IFR 45 min final reserve. Route reserve = 10% of destination fuel.
- Save/load serializes all non-readonly inputs to JSON.

### Takeoff/Landing-specific details

- Four takeoff configurations: flaps-up ground roll (TB1, Fig. 5-11), flaps-25 ground roll (TB2, Fig. 5-13), flaps-up over 50ft (TB3, Fig. 5-7), flaps-25 over 50ft (TB4, Fig. 5-9). Two landing: ground roll (LB1, Fig. 5-37), over 50ft (LB2, Fig. 5-35).
- All six charts live in one `CHARTS` object: straight pressure-altitude lines `dist = a + b*OAT` per 1000 ft (`lines`), a weight ratio per 100 lbs below 2550 (`wt`), linear head/tailwind fractions per knot (`hw`, `tw`) and the distance range the POH actually draws (`lo`, `hi`). `chartDist()` multiplies base × weight × wind × surface and flags cases outside the chart (OAT > 30 °C, tailwind > 5 kt, weight < 2000 lbs, base outside lo/hi) instead of clamping.
- Surface factor multipliers: grass +10%, water/slush +20%/cm, wet snow +10%/cm, powder +5%/cm.
- Results displayed in meters with feet shown as subtitle.

## UI Conventions

- OFP uses a light paper-like theme (print-optimized A4). The index page and the two performance calculators share one CSS variable set with a dark default and a light palette under `:root[data-theme="light"]`; the theme is chosen with a toggle in each page's header, stored in a `theme` cookie (no path, so it covers the folder) and applied to `<html data-theme>` by an inline head script on every page before first paint, falling back to `prefers-color-scheme` when no cookie is set. Keep colors as variables — no hardcoded hex/rgba except low-alpha accent tints.
- Fonts: IBM Plex Mono for data/values, DM Sans or IBM Plex Sans for labels.
- Range sliders with live value display above. Toggle buttons for binary choices.
- Computed/readonly fields use CSS class `computed` or `readonly-val`.
- Swedish labels for most UI text (Resultat, Bränsle, Startrull, etc.), English for aviation terms (TAS, GS, OAT, Pressure Altitude).

## Units

All aviation calculations use standard units: knots (speed), nautical miles (distance), feet (altitude), degrees (headings/wind). Fuel in liters (display) and US gallons (POH tables), converted via `GAL_TO_L = 3.7854`. Weight in kg (display) and lbs (POH tables), converted via `* 2.20462`. CG arm in cm, moments in kg*cm.
