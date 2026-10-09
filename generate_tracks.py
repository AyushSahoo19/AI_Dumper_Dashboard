import pandas as pd
import json
from pyproj import Transformer

print("Reading raw excel...")
df = pd.read_excel('O2K048 Aug26 Readyline (1).xlsx')

df['time'] = pd.to_datetime(df['time'])
df = df.sort_values('time')
df['date_str'] = df['time'].dt.strftime('%Y-%m-%d')
dates = df['date_str'].unique().tolist()

dumper_id = 'DMP-48' # O2K048

# Setup transformer from UTM 45N (EPSG:32645) to Lat/Lon (EPSG:4326)
transformer = Transformer.from_crs("EPSG:32645", "EPSG:4326", always_xy=True)

tracks = {}

for date in dates:
    print(f"Processing tracks for {date}...")
    day_df = df[df['date_str'] == date].copy()
    
    # Sample data to keep JSON small: every 20th row (~ 600 points a day)
    day_df = day_df.iloc[::20]
    
    pts = []
    for _, row in day_df.iterrows():
        n = pd.to_numeric(row['VHMS_KOMHD785_1.Northing'], errors='coerce')
        e = pd.to_numeric(row['VHMS_KOMHD785_1.Easting'], errors='coerce')
        
        if pd.notna(n) and pd.notna(e) and n != 0 and e != 0:
            lon, lat = transformer.transform(e, n)
            
            speed = pd.to_numeric(row['VHMS_KOMHD785_1.Speed'], errors='coerce')
            fuel = pd.to_numeric(row['VHMS_KOMHD785_1.Fuel Rate'], errors='coerce')
            rpm = pd.to_numeric(row.get('VHMS_KOMHD785_1.Engine RPM', 0), errors='coerce')
            
            pts.append({
                'lat': lat,
                'lon': lon,
                'speed': round(speed, 1) if pd.notna(speed) else 0,
                'fuel': round(fuel, 1) if pd.notna(fuel) else 0,
                'rpm': round(rpm, 0) if pd.notna(rpm) else 0,
                'intensity': round(speed, 1) if pd.notna(speed) else 0 # mock intensity based on speed to show variations
            })
            
    tracks[dumper_id + '|' + date] = {'points': pts}

js_content = f"window.READYLINE_TRACKS = {json.dumps(tracks, indent=2)};\n"
with open('Fleet Dashboard/assets/js/readyline_tracks.js', 'w') as f:
    f.write(js_content)
    
print("Tracks generated at Fleet Dashboard/assets/js/readyline_tracks.js!")
