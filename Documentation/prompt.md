# AI Dumper Dashboard & HRG Analysis - Project Context & Runbook

This document serves as the primary context file and runbook for AI agents and developers working on the Tata Steel HRG Analysis & Fleet Dashboard repository. Please read this entirely before beginning any new session or development process.

## 1. Project Overview
- **Objective:** Analyze Haul Road Gradients (HRG) for Tata Steel (Pit-1 to wet plant, KIM Mines) and visualize dumper telemetry data.
- **Components:**
  1. **Data Pipeline (Backend):** Python scripts to process raw GPS/telemetry CSV data into visual formats (KML for Google Earth and JS data for the Web Dashboard).
  2. **Web Dashboard (Frontend):** A premium, light-mode admin dashboard (inspired by modern enterprise UIs like Frest/Sneat) hosted on GitHub Pages to visualize telemetry, gradients, and fleet health.

## 2. Directory Structure & Key Files
- `Readyline_Data.csv` - The core telemetry dataset containing Timestamp, Northing, Easting, and Elevation.
- `kim_combined.py` - The ETL script that calculates haul road gradients and generates gradient-colored `.kml` files.
- `generate_tracks.py` - The ETL script that processes `Readyline_Data.csv` to extract paths and exports them as JSON data inside `Fleet Dashboard/assets/js/readyline_tracks.js`.
- `Output/` - Directory containing all the generated `.kml` files (e.g., `KIM_Combined_08_08_2026.kml`).
- `Fleet Dashboard/` - The frontend web application directory.
- `Fleet Dashboard/assets/css/styles.css` - Global stylesheet (Custom CSS variables, Boxicons, responsive grid, light-mode premium aesthetics).
- `Fleet Dashboard/assets/js/views.js` - Contains logic for UI navigation (`VIEWS.nav()`), Chart.js rendering, and Leaflet map initializations.
- `index.html` (Root) - A redirect file that points GitHub pages to `Fleet Dashboard/index.html`.

## 3. UI/UX Guidelines (Frontend Development)
If you are tasked with updating the frontend dashboard, strictly adhere to these design principles:
- **Aesthetic:** "Premium Light Mode" inspired by Frest/Sneat admin templates. Use soft diffused shadows (`rgba(34, 41, 47, 0.08)`), pure white cards (`#ffffff`), and a soft gray background (`#f8f9fa`).
- **Typography:** Inter font family. Use dark slate (`#475f7b`) for primary text, and gray (`#828d99`) for secondary text.
- **Icons:** We use **Boxicons** (`<i class='bx ...'></i>`). Do not use emojis for UI elements.
- **Components:**
  - Sidebar (`FleetSense` branding) should be compact, with tight padding and prominent active states.
  - Quick Links (Tabs) use the `.map-tabs` and `.link-card` classes, built for horizontal, ultra-compact map navigation buttons.
  - Charts (Chart.js) must use smooth curves (`tension: 0.4`), white tooltips, and soft gridlines.

## 4. Pipeline Execution (Backend Development)
To process new telemetry data, follow these steps in order:

### Step A: Prepare the Environment
Ensure Python dependencies are installed:
```bash
pip install pandas simplekml pyproj
```

### Step B: Generate KMLs for Google Earth / 3D Visualization
Run the KML generator on your dataset:
```bash
python kim_combined.py
```
*This parses `Readyline_Data.csv`, calculates the gradient between points, groups by shift/date, and outputs KMLs into the `Output/` directory.*

### Step C: Generate Web Dashboard Data
Run the track generator to update the web dashboard's map data:
```bash
python generate_tracks.py
```
*This reads the CSV, filters valid tracks, and outputs `Fleet Dashboard/assets/js/readyline_tracks.js` which is loaded directly by the Leaflet maps.*

## 5. Deployment Workflow
The project is deployed via GitHub Pages at `https://ayushsahoo19.github.io/AI_Dumper_Dashboard/`.
Whenever you make updates to the web dashboard UI or generate new KMLs/JS tracks:
1. Stage all files, including items in `Output/` (which are explicitly tracked).
2. Commit with descriptive messages.
3. Push to `main`.
4. GitHub Pages will automatically sync. Ask the user to do a hard refresh (`Ctrl + Shift + R`) to view changes.

## 6. Active Agent Instructions
- **Do not** overwrite `readyline_tracks.js` manually; always use `generate_tracks.py`.
- **Do not** change the color scales for the gradients (Green <= 6.25%, Yellow 6.25-10%, Red > 10%) without user consent.
- Keep the `styles.css` clean and modular. Avoid adding inline styles to `index.html`.
