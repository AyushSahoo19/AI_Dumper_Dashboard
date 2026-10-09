"""
kim_combined.py
---------------
Generates ONE KML file per date (e.g. KIM_17_02_2026.kml), with three
top-level folders inside — one per shift:

  ▼ Shift 1
      ▼ Continuous Elevations
      ▼ Plan Paths (Roads)
      ▼ Detected Bumps (Hazards)
  ▼ Shift 2
      ▼ ...
  ▼ Shift 3
      ▼ ...

In Google Earth the user can tick/untick each Shift folder independently
to show/hide the paths for that shift.

Usage:
    python kim_combined.py
    python kim_combined.py --input "path/to/Positions Data KIM 17-18.csv"
"""

import csv
import math
import os
import simplekml
from datetime import datetime
from collections import defaultdict
from pyproj import Transformer

# ─────────────────────────────────────────────────────────────────────────────
# Configuration  (identical to kim_segmentation.py)
# ─────────────────────────────────────────────────────────────────────────────
MAX_DISTANCE_GAP_M      = 150.0
MAX_TIME_GAP_SECONDS    = 180
SMOOTHING_WINDOW_SIZE   = 3
CLIMB_GRADIENT_THRESHOLD= 0.02
BUMP_HEIGHT_THRESHOLD_M = 1.0
BUMP_MIN_LENGTH_M       = 1.0
RAISE_HEIGHT_M          = 3.0

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _dist(n1, e1, n2, e2):
    return math.hypot(n2 - n1, e2 - e1)

def _utm_to_latlon(n, e, zone=45, hemi='north'):
    utm = f'+proj=utm +zone={zone} +ellps=WGS84 +datum=WGS84 +units=m +no_defs'
    if hemi != 'north':
        utm += ' +south'
    wgs = '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs'
    lon, lat = Transformer.from_crs(utm, wgs, always_xy=True).transform(e, n)
    return lat, lon

# ─────────────────────────────────────────────────────────────────────────────
# 1. Load – group by (Shift Date, Shift)  →  {date: {shift: [points]}}
# ─────────────────────────────────────────────────────────────────────────────
def load_and_group(input_csv: str) -> dict:
    """
    Returns nested dict:
        { "17-02-2026": { "1": [pts], "2": [pts], "3": [pts] }, ... }
    """
    with open(input_csv, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    header_idx = None
    for i, line in enumerate(lines):
        if 'Northing' in line and 'Easting' in line and 'Elevation' in line:
            header_idx = i
            break
    if header_idx is None:
        raise RuntimeError("Header with Northing/Easting/Elevation not found")

    reader  = csv.DictReader(lines[header_idx:])
    # date → shift → list of points
    data: dict = defaultdict(lambda: defaultdict(list))
    skipped = 0

    for row in reader:
        try:
            ts_raw     = (row.get('Timestamp')  or '').strip()
            shift_date = (row.get('Shift Date') or 'UnknownDate').strip()
            shift_id   = (row.get('Shift')      or '1').strip()
            n = float(row['Northing'])
            e = float(row['Easting'])
            z = float(row['Elevation'])

            ts = None
            for fmt in ('%d-%m-%Y %H:%M:%S', '%d-%m-%Y %H:%M', '%d-%m-%Y'):
                try:
                    ts = datetime.strptime(ts_raw, fmt)
                    break
                except ValueError:
                    pass
            if ts is None:
                ts = datetime.min

            data[shift_date][shift_id].append({'ts': ts, 'n': n, 'e': e, 'z': z})

        except Exception:
            skipped += 1
            continue

    # Sort each shift chronologically
    for date in data:
        for sid in data[date]:
            data[date][sid].sort(key=lambda p: p['ts'])

    total = sum(len(v) for d in data.values() for v in d.values())
    print(f"Loaded {total} points across {len(data)} date(s). ({skipped} rows skipped)")
    return data


# ─────────────────────────────────────────────────────────────────────────────
# 2. Split contiguous paths  (gap filter)
# ─────────────────────────────────────────────────────────────────────────────
def split_paths(points: list) -> list:
    paths, current = [], []
    for p in points:
        if not current:
            current.append(p)
            continue
        prev = current[-1]
        d  = _dist(prev['n'], prev['e'], p['n'], p['e'])
        dt = (p['ts'] - prev['ts']).total_seconds()
        if d > MAX_DISTANCE_GAP_M or (0 < dt > MAX_TIME_GAP_SECONDS and dt < 86400):
            if len(current) > 1:
                paths.append(current)
            current = [p]
        else:
            current.append(p)
    if len(current) > 1:
        paths.append(current)
    return paths


# ─────────────────────────────────────────────────────────────────────────────
# 3. Smooth elevation
# ─────────────────────────────────────────────────────────────────────────────
def smooth_z(points: list) -> list:
    out, win = [], []
    for p in points:
        win.append(p['z'])
        if len(win) > SMOOTHING_WINDOW_SIZE:
            win.pop(0)
        q = p.copy()
        q['z_s'] = sum(win) / len(win)
        out.append(q)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 4. Segment path into Climb / Plan sections
# ─────────────────────────────────────────────────────────────────────────────
def segment_path(pts: list) -> list:
    if len(pts) < 2:
        return []
    segs, cur = [], {'type': 'UNKNOWN', 'points': [pts[0]]}
    for i in range(1, len(pts)):
        p1, p2 = pts[i-1], pts[i]
        d  = _dist(p1['n'], p1['e'], p2['n'], p2['e'])
        dz = abs(p2['z_s'] - p1['z_s'])
        g  = dz / d if d > 0 else 0
        st = 'ELEVATION' if g > CLIMB_GRADIENT_THRESHOLD else 'PLAN'
        if cur['type'] == 'UNKNOWN':
            cur['type'] = st
        if st != cur['type']:
            segs.append(cur)
            cur = {'type': st, 'points': [p1, p2]}
        else:
            cur['points'].append(p2)
    segs.append(cur)
    return segs


# ─────────────────────────────────────────────────────────────────────────────
# 5. Write one shift's segments into pre-created KML sub-folders
# ─────────────────────────────────────────────────────────────────────────────
def populate_shift_folder(shift_folder, paths: list, shift_label: str):
    """Fills the three sub-folders (Elevations / Flats / Bumps) inside a shift folder."""
    f_climbs = shift_folder.newfolder(name="Continuous Elevations")
    f_flats  = shift_folder.newfolder(name="Plan Paths (Roads)")
    f_bumps  = shift_folder.newfolder(name="Detected Bumps (Hazards)")

    idx = 0
    for pi, raw_path in enumerate(paths):
        smoothed = smooth_z(raw_path)
        for seg in segment_path(smoothed):
            pts = seg['points']
            if len(pts) < 2:
                continue

            total_dist = total_dz = 0.0
            coords = []
            for k, p in enumerate(pts):
                lat, lon = _utm_to_latlon(p['n'], p['e'])
                coord = (lon, lat, RAISE_HEIGHT_M)
                if not coords or coords[-1] != coord:
                    coords.append(coord)
                if k > 0:
                    total_dist += _dist(pts[k-1]['n'], pts[k-1]['e'], p['n'], p['e'])
                    total_dz   += abs(p['z_s'] - pts[k-1]['z_s'])
            
            if len(coords) < 2:
                continue

            avg_grad = total_dz / total_dist if total_dist > 0 else 0.0

            if seg['type'] == 'ELEVATION':
                ls = f_climbs.newlinestring(name=f"{shift_label}_P{pi}_Climb{idx}")
                ls.coords       = coords
                ls.altitudemode = simplekml.AltitudeMode.relativetoground
                ls.extrude      = 1
                if avg_grad > 0.10:
                    ls.style.linestyle.color = simplekml.Color.red
                elif avg_grad > 0.0625:
                    ls.style.linestyle.color = simplekml.Color.yellow
                else:
                    ls.style.linestyle.color = simplekml.Color.green
                ls.style.linestyle.width = 1.5
                ls.description  = (f"Shift: {shift_label}\n"
                                   f"Type: Continuous Climb\n"
                                   f"Length: {total_dist:.1f} m\n"
                                   f"Gradient: {avg_grad*100:.1f} %")
            else:
                ls = f_flats.newlinestring(name=f"{shift_label}_P{pi}_Flat{idx}")
                ls.coords       = coords
                ls.altitudemode = simplekml.AltitudeMode.relativetoground
                ls.style.linestyle.color = simplekml.Color.green
                ls.style.linestyle.width = 1.5
                ls.description  = f"Shift: {shift_label}\nType: Plan Path\nLength: {total_dist:.1f} m"

                # Bump detector
                b_dz = b_dist = 0.0
                b_start = 0
                for k in range(1, len(pts)):
                    d   = _dist(pts[k-1]['n'], pts[k-1]['e'], pts[k]['n'], pts[k]['e'])
                    z_u = pts[k]['z_s'] - pts[k-1]['z_s']
                    if z_u > 0:
                        b_dz   += z_u
                        b_dist += d
                    else:
                        b_dz = b_dist = 0.0
                        b_start = k
                    if b_dz > BUMP_HEIGHT_THRESHOLD_M and b_dist >= BUMP_MIN_LENGTH_M:
                        bcoords = []
                        for j in range(b_start, k+1):
                            la, lo = _utm_to_latlon(pts[j]['n'], pts[j]['e'])
                            bcoords.append((lo, la, RAISE_HEIGHT_M + 2))
                        bm = f_bumps.newlinestring(name=f"BUMP_{shift_label}_{pi}_{k}")
                        bm.coords       = bcoords
                        bm.style.linestyle.color = simplekml.Color.green
                        bm.style.linestyle.width = 1.5
                        bm.altitudemode = simplekml.AltitudeMode.relativetoground
                        bm.description  = (f"Shift: {shift_label}\nHAZARD: Bump > 1 m\n"
                                           f"Height: {b_dz:.2f} m\nSpan: {b_dist:.1f} m")
                        b_dz = b_dist = 0.0
                        b_start = k
            idx += 1


# ─────────────────────────────────────────────────────────────────────────────
# 6. Build one combined KML per date
# ─────────────────────────────────────────────────────────────────────────────
def build_combined_kml(date_str: str, shifts_dict: dict, out_path: str):
    """
    Creates a single KML with three top-level folders (Shift 1, Shift 2, Shift 3).
    Each folder can be toggled independently in Google Earth.
    """
    kml = simplekml.Kml(name=f"KIM Analysis – {date_str}",
                        description="Select a Shift folder in Google Earth to toggle visibility.")

    sorted_shifts = sorted(shifts_dict.keys(), key=lambda s: int(s) if s.isdigit() else 999)

    for shift_id in sorted_shifts:
        shift_label = f"Shift {shift_id}"
        points      = shifts_dict[shift_id]

        # Top-level shift folder — visible by default, user can uncheck in GE
        shift_folder = kml.newfolder(name=shift_label)
        shift_folder.visibility = 1   # 1 = visible, 0 = hidden

        paths = split_paths(points)
        print(f"  [{date_str} {shift_label}] {len(points)} pts -> {len(paths)} path(s)")

        if paths:
            populate_shift_folder(shift_folder, paths, shift_label)
        else:
            shift_folder.newpoint(name="No data", coords=[(0, 0, 0)]).visibility = 0

    kml.save(out_path)
    print(f"  [OK] Saved: {os.path.basename(out_path)}")


# ─────────────────────────────────────────────────────────────────────────────
# 7. Main
# ─────────────────────────────────────────────────────────────────────────────
def process(input_csv: str):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir    = os.path.join(script_dir, "Output")
    os.makedirs(out_dir, exist_ok=True)

    data = load_and_group(input_csv)   # { date: { shift_id: [pts] } }

    for date_str, shifts_dict in sorted(data.items()):
        print(f"\nBuilding combined KML for {date_str} ({len(shifts_dict)} shift(s))...")
        safe_date = date_str.replace('-', '_').replace('/', '_').replace(' ', '_')
        out_path  = os.path.join(out_dir, f"KIM_Combined_{safe_date}.kml")
        build_combined_kml(date_str, shifts_dict, out_path)

    print(f"\nAll combined KML files saved to: {out_dir}")


if __name__ == '__main__':
    import argparse
    # CSV sits in the same folder as this script (KIM_Combined/)
    DEFAULT = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'Positions Data KIM 17-18.csv'
    )
    p = argparse.ArgumentParser(description='KIM Combined Shift KML Generator')
    p.add_argument('--input', default=DEFAULT)
    args = p.parse_args()
    process(args.input)
