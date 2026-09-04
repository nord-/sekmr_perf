# PA-28-181 Archer II (SE-KMR) — Flight Planning Tools

> **WARNING: These tools are NOT approved for operational flight planning. All values are digitized approximations from POH diagrams and MUST be verified against the original Pilot's Operating Handbook before any real-world use. Do not rely on these calculators as your primary source — always cross-check every number with the actual POH.**

A set of browser-based flight planning tools for the PA-28-181 Archer II, tailored to SE-KMR. The calculators default to a dark theme; a light theme can be selected on the index page and is remembered in a cookie.

**Live version:** https://nord-.github.io/sekmr_perf/

## Tools

### Operational Flight Plan
Interactive navigation log with automatic wind triangle solving (WCA, GS), fuel planning with VFR/IFR reserves, and mass & balance with CG envelope visualization. Print-optimized A4 layout. Supports save/load to JSON.

### Climb / Cruise / Descent Calculator
Interpolates POH chart data to estimate time, distance, and fuel for climb and descent phases. Cruise tab provides TAS, RPM, fuel flow, and range for various altitude, temperature, and power settings. Supports leaned/rich mixture for climb and best power/economy for cruise.

### Takeoff & Landing Performance
Ground roll and 50 ft obstacle clearance distances for multiple flap configurations. Inputs for OAT, pressure altitude, weight, and wind. Surface condition adjustments (grass, water/slush, wet/powder snow) are rule-of-thumb estimates — not from the POH.

## Disclaimer

**These tools are provided for educational and reference purposes only.**

- Performance data has been digitized from POH charts (Figures 5-7, 5-9, 5-11, 5-13, 5-15, 5-17, 5-19, 5-21, 5-23, 5-31, 5-35, 5-37). Each chart panel was read separately (pressure-altitude lines, weight and wind guide lines, curves), so the tables reproduce the POH worked examples within about 2 % and individual readings are good to roughly ±3 %, but errors may exist.
- Surface condition corrections (anything other than dry paved runway) are rules of thumb, not POH data.
- Mass & balance constants are specific to SE-KMR and its equipment list. They do not apply to other PA-28-181 airframes.
- **The pilot in command is solely responsible for verifying all performance data against the approved POH before flight.**

How the charts were read, with the calibration values needed to check or extend the tables, is documented in [docs/DIGITIZING.md](docs/DIGITIZING.md).
