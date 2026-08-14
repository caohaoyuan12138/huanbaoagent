# -*- coding: utf-8 -*-
"""检查当前数据库中已有的排放标准/质量标准"""
import sqlite3

conn = sqlite3.connect("env_agent.db")
c = conn.cursor()

print("=== 数据库中所有含'排放/质量/环境'关键词的标准 ===")
rows = c.execute("""
    SELECT standard_number, title, category, industry
    FROM standards
    WHERE title LIKE '%排放标准%' OR title LIKE '%环境质量%' OR title LIKE '%质量标准%'
    ORDER BY standard_number
""").fetchall()
print(f"共 {len(rows)} 条")
for r in rows:
    print(f"  {r[0]} | {r[1]} | {r[2]} | {r[3]}")

print("\n=== 按关键词统计 ===")
keywords = ['大气', '噪声', '地下水', '废水', '污水', '雨水', '土壤', '废气', '地表水', '环境空气']
for kw in keywords:
    cnt = c.execute("SELECT COUNT(*) FROM standards WHERE title LIKE ?", (f'%{kw}%',)).fetchone()[0]
    print(f"  '{kw}': {cnt} 条")

conn.close()
