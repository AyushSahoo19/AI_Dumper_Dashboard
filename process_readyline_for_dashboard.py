import pandas as pd
import json
import math
import os

print("Reading raw excel...")
df = pd.read_excel('O2K048 Aug26 Readyline (1).xlsx')

df['time'] = pd.to_datetime(df['time'])
df = df.sort_values('time')
df['date_str'] = df['time'].dt.strftime('%Y-%m-%d')
dates = df['date_str'].unique().tolist()

dumper_id = 'DMP-48' # O2K048

store = {}
meta = {dumper_id: []}
timeseries = {}

for date in dates:
    print(f"Processing {date}...")
    day_df = df[df['date_str'] == date]
    
    # Calculate metrics for the day
    fuel = pd.to_numeric(day_df['VHMS_KOMHD785_1.Fuel Rate'], errors='coerce')
    rpm = pd.to_numeric(day_df['VHMS_KOMHD785_1.Engine RPM'], errors='coerce')
    spd = pd.to_numeric(day_df['VHMS_KOMHD785_1.Speed'], errors='coerce')
    wt = pd.to_numeric(day_df['VHMS_KOMHD785_1.Live Weight'], errors='coerce')
    ret = pd.to_numeric(day_df['VHMS_KOMHD785_1.Retarder Position'], errors='coerce')
    
    # Basic aggs
    fuel_lph = fuel.mean() if not fuel.dropna().empty else 0
    wt_valid = wt[wt > 0]
    avg_payload = wt_valid.mean() if not wt_valid.empty else 0
    
    idle_mask = (spd < 1) & (rpm < 700)
    idle_pct = (idle_mask.sum() / len(day_df) * 100) if len(day_df) > 0 else 0
    
    ret_pct = ((ret > 10).sum() / len(day_df) * 100) if len(day_df) > 0 else 0
    
    trips = 15 # Mocking trips as we don't have hoist lever pos in this data
    
    metrics = {
        'fuel_lph': round(fuel_lph, 1),
        'idle_pct': round(idle_pct, 1),
        'avg_payload': round(avg_payload, 1),
        'overload_events': int((wt_valid > 110).sum() / 10), # rough estimate
        'trips': trips,
        'susp_imbalance': 8, # mock
        'susp_press_rr_avg': 110, # mock
        'brake_temp_max': 85, # mock
        'retarder_pct': round(ret_pct, 1),
        'coolant_max': 90, # mock
        'eng_oil_temp_max': 100, # mock
        'oil_press_min': 30, # mock
        'boost_avg': 50, # mock
        'blowby_avg': 100, # mock
        'exh_temp_max': 450, # mock
        'harsh_brake_events': 2, # mock
        'overspeed_events': int((spd > 35).sum() / 5),
        'rack_red_count': 5, # mock
        'bias_red_count': 5, # mock
        'undulation_p95': 12, # mock
        'fuel_per_ton': round((fuel_lph * 10) / (avg_payload * trips) if avg_payload * trips > 0 else 0, 2)
    }
    
    store[date] = {dumper_id: metrics}
    meta[dumper_id].append(date)

out_json = {
    'store': store,
    'meta': meta,
    'dates': sorted(dates),
    'today': sorted(dates)[-1] if dates else '2026-08-31'
}

js_content = f"const READYLINE_DATA = {json.dumps(out_json, indent=2)};\n"
with open('Fleet Dashboard/assets/js/readyline_data.js', 'w') as f:
    f.write(js_content)
    
print("Dashboard data generated at Fleet Dashboard/assets/js/readyline_data.js!")
