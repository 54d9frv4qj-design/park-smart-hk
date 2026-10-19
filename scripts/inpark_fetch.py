# -*- coding: utf-8 -*-
"""從 inpark API 分瓦片抓取全部停車場收費，輸出 CSV。

適應式四分：瓦片超過 400 點就切四塊重抓，避免單瓦片被截。
"""
import csv
import json
import time
import urllib.request

API = "https://api-inpark.com/v1/parking/map/layer"
BOUNDS = dict(sw_lat=22.13, sw_lng=113.84, ne_lat=22.62, ne_lng=114.46)
OUT = "data/inpark_fees.csv"
KEYS = ["id", "name_zh_hant", "name_en", "lat", "lng",
        "min_avg_hourly_hkd", "headline_hourly_hkd", "total_cost_hkd"]


def fetch(sw_lat, sw_lng, ne_lat, ne_lng, retries=3):
    q = (f"{API}?sw_lat={sw_lat:.5f}&sw_lng={sw_lng:.5f}"
         f"&ne_lat={ne_lat:.5f}&ne_lng={ne_lng:.5f}&typical=true&lens=hourly")
    for i in range(retries):
        try:
            req = urllib.request.Request(q, headers={
                "User-Agent": "Mozilla/5.0", "Referer": "https://inpark.com.hk/"})
            return json.loads(urllib.request.urlopen(req, timeout=20).read())
        except Exception:
            time.sleep(1.0 + i)
    return None


def collect(sw_lat, sw_lng, ne_lat, ne_lng, acc, depth=0):
    d = fetch(sw_lat, sw_lng, ne_lat, ne_lng)
    if d is None:
        return
    if d["total_in_viewport"] <= 400 or depth >= 8:
        for row in d["data"]:
            acc[row["id"]] = row
        return
    mid_lat = (sw_lat + ne_lat) / 2
    mid_lng = (sw_lng + ne_lng) / 2
    collect(sw_lat, sw_lng, mid_lat, mid_lng, acc, depth + 1)
    collect(sw_lat, mid_lng, mid_lat, ne_lng, acc, depth + 1)
    collect(mid_lat, sw_lng, ne_lat, mid_lng, acc, depth + 1)
    collect(mid_lat, mid_lng, ne_lat, ne_lng, acc, depth + 1)


def main():
    acc = {}
    collect(BOUNDS["sw_lat"], BOUNDS["sw_lng"], BOUNDS["ne_lat"], BOUNDS["ne_lng"], acc)
    rows = list(acc.values())
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=KEYS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in KEYS})
    print(f"fetched {len(rows)} records -> {OUT}")


if __name__ == "__main__":
    main()
