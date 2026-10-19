# -*- coding: utf-8 -*-
"""
修正 vacancy=-1 → 0（政府 API 用 -1 表示滿座/數據暫停）
"""
import sys; sys.path.insert(0, '.')
from src.db.connection import get_engine
from sqlalchemy import text

e = get_engine()
with e.connect() as c:
    # 統計修正前
    before = c.execute(text("SELECT COUNT(*) FROM carparks_realtime WHERE vacancy < 0")).fetchone()[0]
    print(f"修正前：{before} 條負值記錄")

    # 將所有負值 vacancy 轉為 0
    c.execute(text("UPDATE carparks_realtime SET vacancy = 0 WHERE vacancy < 0"))
    c.commit()

    # 都檢查其他 vacancy 欄位
    for col in ["vacancy_ev", "vacancy_motorcycle", "vacancy_goods"]:
        try:
            n = c.execute(text(f"SELECT COUNT(*) FROM carparks_realtime WHERE {col} < 0")).fetchone()[0]
            if n > 0:
                c.execute(text(f"UPDATE carparks_realtime SET {col} = 0 WHERE {col} < 0"))
                c.commit()
                print(f"  {col}: 修正 {n} 條")
        except Exception:
            pass

    # 驗證
    after = c.execute(text("SELECT COUNT(*) FROM carparks_realtime WHERE vacancy < 0")).fetchone()[0]
    print(f"修正後：{after} 條負值記錄")

print("✅ 完成")
