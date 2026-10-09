import pandas as pd
from datetime import datetime, timedelta

def get_shift(dt):
    hour = dt.hour
    if 6 <= hour < 14:
        return '1', dt.strftime('%d-%m-%Y')
    elif 14 <= hour < 22:
        return '2', dt.strftime('%d-%m-%Y')
    else:
        # Shift 3: 22:00 to 06:00
        # If hour is < 6, it belongs to the previous day's shift 3
        shift_date = dt if hour >= 22 else dt - timedelta(days=1)
        return '3', shift_date.strftime('%d-%m-%Y')

print("Reading excel file...")
df = pd.read_excel('O2K048 Aug26 Readyline (1).xlsx')

print("Processing timestamps and shifts...")
# Parse time column
dt_series = pd.to_datetime(df['time'])

# Extract Timestamp string
df['Timestamp'] = dt_series.dt.strftime('%d-%m-%Y %H:%M:%S')

# Compute Shift Date and Shift
shifts_and_dates = dt_series.apply(get_shift)
df['Shift'] = shifts_and_dates.apply(lambda x: x[0])
df['Shift Date'] = shifts_and_dates.apply(lambda x: x[1])

# Rename columns
rename_map = {
    'VHMS_KOMHD785_1.Northing': 'Northing',
    'VHMS_KOMHD785_1.Easting': 'Easting',
    'VHMS_KOMHD785_1.Elevation': 'Elevation'
}
df.rename(columns=rename_map, inplace=True)

# Select required columns
final_df = df[['Timestamp', 'Shift Date', 'Shift', 'Northing', 'Easting', 'Elevation']]

# Save to CSV
print("Saving to CSV...")
final_df.to_csv('Readyline_Data.csv', index=False)
print("Data formatted and saved to Readyline_Data.csv!")
