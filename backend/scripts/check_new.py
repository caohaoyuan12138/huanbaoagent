# -*- coding: utf-8 -*-
"""检查新入库的标准，找出需要补充限值的排放标准"""
import sqlite3
import re

conn = sqlite3.connect("env_agent.db")
c = conn.cursor()

# 查找新入库的排放/质量标准（source_url含mee.gov.cn）
print("=== 新入库的排放/质量标准（来自环境部官网）===")
rows = c.execute("""
    SELECT s.standard_number, s.title, s.category, s.industry, s.source_url,
           (SELECT COUNT(*) FROM pollution_limits pl WHERE pl.standard_title = s.title) AS limit_count
    FROM standards s
    WHERE s.source_url LIKE '%mee.gov.cn%'
      AND (s.title LIKE '%排放标准%' OR s.title LIKE '%质量标准%' OR s.title LIKE '%环境质量%'
           OR s.title LIKE '%污染控制%' OR s.title LIKE '%排放控制%')
    ORDER BY limit_count ASC, s.standard_number
""").fetchall()
print(f"共 {len(rows)} 条\n")
for r in rows:
    print(f"  [{r[5]}项] {r[0]} | {r[1][:40]} | {r[2]} | {r[3]}")

# 同时检查之前已有的排放标准中缺少限值的
print("\n\n=== 之前已有但缺限值的排放标准 ===")
rows2 = c.execute("""
    SELECT s.standard_number, s.title, s.category,
           (SELECT COUNT(*) FROM pollution_limits pl WHERE pl.standard_title = s.title) AS limit_count
    FROM standards s
    WHERE (s.title LIKE '%排放标准%' OR s.title LIKE '%质量标准%')
      AND (SELECT COUNT(*) FROM pollution_limits pl WHERE pl.standard_title = s.title) = 0
      AND s.source_url NOT LIKE '%mee.gov.cn%'
    ORDER BY s.standard_number
""").fetchall()
print(f"共 {len(rows2)} 条\n")
for r in rows2:
    print(f"  {r[0]} | {r[1][:40]} | {r[2]}")

conn.close()
