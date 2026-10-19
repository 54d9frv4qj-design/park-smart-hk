# -*- coding: utf-8 -*-
"""
修正佔用率：
1. 限制 0-1 範圍
2. 用每個停車場自己嘅歷史範圍計算「相對繁忙度」
3. 重新導出 CSV
"""
import sys; sys.path.insert(0, '.')
from src.db.connection import get_engine
from sqlalchemy import text
import pandas as pd

e = get_engine()

with e.connect() as c:
    # 1. 先修正異常值（限制 0-1）
    print("修正佔用率範圍 0-1...")
    c.execute(text("""
        UPDATE carparks_realtime
        SET occupancy_rate = CASE
            WHEN occupancy_rate < 0 THEN 0
            WHEN occupancy_rate > 1 THEN 1
            ELSE occupancy_rate
        END
    """))
    c.commit()

    # 2. 計算每個停車場嘅 min/max vacancy（用於標準化）
    print("計算每個停車場 vacancy 範圍...")
    ranges = c.execute(text("""
        SELECT park_id, MIN(vacancy) as min_vac, MAX(vacancy) as max_vac
        FROM carparks_realtime
        WHERE vacancy IS NOT NULL
        GROUP BY park_id
    """)).fetchall()

    # 3. 用標準化方法重新計算佔用率：
    # 每個停車場自己嘅 vacancy 範圍映射到 10%-95% 佔用率
    # vacancy=max（最空）→ 10% 佔用率
    # vacancy=min（最滿）→ 95% 佔用率
    print("用標準化方法重新計算...")
    updates = 0
    for pid, mn, mx in ranges:
        if mx is None or mn is None or mx <= mn:
            continue
        # 線性映射：vacancy → occupancy
        # occ = 0.95 - (vac - mn) / (mx - mn) * 0.85
        c.execute(text(f"""
            UPDATE carparks_realtime
            SET occupancy_rate = ROUND(0.95 - (CAST(vacancy AS REAL) - {mn}) / ({mx} - {mn}) * 0.85, 4)
            WHERE park_id = '{pid}' AND vacancy IS NOT NULL
        """))
        updates += 1
    c.commit()
    print(f"更新了 {updates} 個停車場")

    # 4. 更新 status
    print("更新 status...")
    c.execute(text("""
        UPDATE carparks_realtime
        SET status = CASE
            WHEN occupancy_rate >= 0.85 THEN 'red'
            WHEN occupancy_rate >= 0.65 THEN 'yellow'
            ELSE 'green'
        END
    """))
    c.commit()

    # 5. 驗證
    stats = c.execute(text("""
        SELECT MIN(occupancy_rate), MAX(occupancy_rate), AVG(occupancy_rate)
        FROM carparks_realtime
    """)).fetchone()
    print(f"\n佔用率範圍: {stats[0]:.2f} - {stats[1]:.2f}, 平均 {stats[2]:.2f}")

    df = pd.read_sql(text("""
        SELECT CAST(STRFTIME('%w', snapshot_time) AS INTEGER) as wd,
               CAST(STRFTIME('%H', snapshot_time) AS INTEGER) as hr,
               AVG(occupancy_rate) as occ
        FROM carparks_realtime GROUP BY wd, hr
    """), e)
    print(f"7x24 範圍: {df['occ'].min():.2f} - {df['occ'].max():.2f}")
    print("\n24小時平均:")
    for h in range(24):
        row = df[df['hr'] == h]
        if not row.empty:
            print(f"  {h:02d}點: {row['occ'].mean():.2f}")

print("\n✅ 完成！")
