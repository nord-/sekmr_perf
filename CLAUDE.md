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
- **Linear interpolation** — `lerp()` / `lerpNested()` / `it()` functions interpolate between data points for altitude, temperature, power setting, and weight. The climb/cruise/descent calculator uses a "cumulative from sea level" subtraction method: `result = lerp(cruiseAlt) - lerp(departureAlt)`.
- **Temperature correction** — ISA deviation (`OAT - ISA_temp`) is computed via `getISA(alt) = 15 - alt * 1.98/1000`. Corrections are applied as multiplicative factors (e.g., `1 + dev * 0.01` for climb).
- **Density altitude** — `DA = PA + 120 * (OAT - ISA_temp)`, used in cruise TAS and RPM lookups.
- **Event-driven recalculation** — Input events trigger cascading recalcs. In the OFP, changing a single field (e.g., wind direction) propagates through: wind triangle -> WCA/GS -> time_leg -> fuel_leg -> fuel table -> mass & balance -> CG chart.

### OFP-specific details

- Navigation log rows are generated dynamically via `createNavRow()`. Row types: `data`, `header` (alternate section), `totals`.
- Wind triangle: `WCA = arcsin(wspd * sin(wdir - TT) / TAS)`, `GS = TAS * cos(WCA) - wspd * cos(wdir - TT)`.
- Variation parsing accepts both `E4`/`W5` and `+/-` formats.
- Mass & balance constants: BEM 737 kg @ 223.7 cm, AVGAS density 0.719 kg/L, fuel arm 241.3 cm. CG envelope drawn on canvas with points for ZFM, TOM, LDG mass.
- Fuel reserves: VFR 30 min, IFR 45 min final reserve. Route reserve = 10% of destination fuel.
- Save/load serializes all non-readonly inputs to JSON.

### Takeoff/Landing-specific details

- Four takeoff configurations: flaps-up ground roll (TB1), flaps-25 ground roll (TB2), flaps-up over 50ft (TB3), flaps-25 over 50ft (TB4). Two landing: ground roll (LB1), over 50ft (LB2).
- Weight correction via separate interpolation tables (TW1-TW4, LW1-LW2) indexed by weight in lbs.
- Wind correction functions (`twGR`, `tw50`, `lwGR`, `lw50`) use quadratic polynomials, different for headwind vs tailwind.
- Surface factor multipliers: grass +10%, water/slush +20%/cm, wet snow +10%/cm, powder +5%/cm.
- Results displayed in meters with feet shown as subtitle.

## UI Conventions

- OFP uses a light paper-like theme (print-optimized A4). Performance calculators use a dark theme.
- Fonts: IBM Plex Mono for data/values, DM Sans or IBM Plex Sans for labels.
- Range sliders with live value display above. Toggle buttons for binary choices.
- Computed/readonly fields use CSS class `computed` or `readonly-val`.
- Swedish labels for most UI text (Resultat, Bränsle, Startrull, etc.), English for aviation terms (TAS, GS, OAT, Pressure Altitude).

## Units

All aviation calculations use standard units: knots (speed), nautical miles (distance), feet (altitude), degrees (headings/wind). Fuel in liters (display) and US gallons (POH tables), converted via `GAL_TO_L = 3.7854`. Weight in kg (display) and lbs (POH tables), converted via `* 2.20462`. CG arm in cm, moments in kg*cm.
