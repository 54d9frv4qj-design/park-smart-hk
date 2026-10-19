# -*- coding: utf-8 -*-
"""把 inpark 收費併入 carparks_static（直接 ID 優先，最近≤50m 輔助）。

只寫 hourly_fee（min_avg_hourly_hkd），0/NaN 保留原樣不覆蓋。
"""
import gzip
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.haversine import haversine_m

STATIC = "data/csv_export/carparks_static.csv.gz"
INPARK = "data/inpark_fees.csv"
NEAR_M = 50.0


def main():
    static = pd.read_csv(STATIC)
    ip = pd.read_csv(INPARK)
    ip_by_id = ip.set_index("id")

    filled, kept, skipped = 0, 0, 0
    for idx, row in static.iterrows():
        pid = row["park_id"]
        fee = None
        if pid in ip_by_id.index:
            v = pd.to_numeric(ip_by_id.loc[pid, "min_avg_hourly_hkd"], errors="coerce")
            fee = float(v) if pd.notna(v) and v > 0 else None
        else:
            best = min(
                (haversine_m(row["lat"], row["lng"], a, b), i)
                for i, (a, b) in enumerate(zip(ip["lat"], ip["lng"]))
            )
            if best[0] <= NEAR_M:
                v = pd.to_numeric(ip.iloc[best[1]]["min_avg_hourly_hkd"], errors="coerce")
                fee = float(v) if pd.notna(v) and v > 0 else None

        if fee is not None:
            static.at[idx, "hourly_fee"] = fee
            static.at[idx, "fee_estimated"] = 0
            filled += 1
        elif pd.notna(row.get("hourly_fee")) and row["hourly_fee"] > 0:
            kept += 1
        else:
            skipped += 1

    with gzip.open(STATIC, "wt", encoding="utf-8", newline="") as f:
        static.to_csv(f, index=False, encoding="utf-8-sig")
    print(f"filled={filled} kept_old={kept} no_fee={skipped}")


if __name__ == "__main__":
    main()
