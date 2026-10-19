# -*- coding: utf-8 -*-
import sys, sqlite3, pandas as pd
from pathlib import Path
sys.path.insert(0, '.')

CSV_DIR = Path('data/csv_export')
tables = ['carparks_static', 'carparks_realtime', 'metered_parking', 
          'meter_occupancy', 'weather_data', 'carpark_meter_nearby']

conn = sqlite3.connect(':memory:')

with open('src/db/schema.sql', 'r', encoding='utf-8') as f:
    schema = f.read()
for stmt in schema.split(';'):
    stmt = stmt.strip()
    if not stmt or 'create_hypertable' in stmt.lower():
        continue
    try:
        conn.execute(stmt)
    except Exception as e:
        if 'already exists' not in str(e).lower():
            print(f"Schema warning: {e}")
conn.commit()

for table in tables:
    csv_path = CSV_DIR / f'{table}.csv.gz'
    if not csv_path.exists():
        print(f"SKIP {table}: not found")
        continue
    try:
        df = pd.read_csv(csv_path, compression='gzip', encoding='utf-8-sig')
        print(f"{table}: {len(df)} rows, cols={list(df.columns)[:5]}...")
        df.to_sql(table, conn, if_exists='append', index=False, chunksize=20000)
        conn.commit()
        print(f"  OK: {conn.execute(f'SELECT COUNT(*) FROM {table}').scalar()} rows")
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")

conn.close()
print("Done")
