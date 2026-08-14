# -*- coding: utf-8 -*-
"""修复残留的日期和编号片段"""
import re
import sqlite3

conn = sqlite3.connect("env_agent.db")
c = conn.cursor()

# 查找标题中有残留日期/编号的
rows = c.execute("SELECT id, standard_number, title FROM standards WHERE source_url LIKE '%mee.gov.cn%'").fetchall()
fixed = 0
for sid, std_num, title in rows:
    if not title:
        continue
    new_title = title
    # 去掉末尾的 －YYYY / –YYYY / -YYYY
    new_title = re.sub(r'\s*[－–-]\s*\d{2,4}\s*$', '', new_title).strip()
    # 去掉末尾的 " 部分"
    new_title = re.sub(r'\s+部分\s*$', '', new_title).strip()
    # 去掉 "部分" 在中间的残留
    # 去掉多余空格
    new_title = re.sub(r'\s+', ' ', new_title).strip()

    if new_title and new_title != title and len(new_title) >= 3:
        c.execute("UPDATE standards SET title = ? WHERE id = ?", (new_title, sid))
        fixed += 1
        print(f"  {std_num} | '{title}' -> '{new_title}'")

# 修复 GB 12523 (无年份) 的标题
c.execute("UPDATE standards SET title = '建筑施工场界环境噪声排放标准' WHERE standard_number = 'GB 12523' AND title != '建筑施工场界环境噪声排放标准'")
if c.rowcount > 0:
    print(f"  修复 GB 12523 标题")
    fixed += c.rowcount

# 修复 GB 3096 (无年份) 的标题
c.execute("UPDATE standards SET title = '声环境质量标准' WHERE standard_number = 'GB 3096' AND title != '声环境质量标准'")
if c.rowcount > 0:
    print(f"  修复 GB 3096 标题")
    fixed += c.rowcount

# 修复 GB/T 15190 (无年份) 的标题
c.execute("UPDATE standards SET title = '声环境功能区划分技术规范' WHERE standard_number = 'GB/T 15190' AND title != '声环境功能区划分技术规范'")
if c.rowcount > 0:
    print(f"  修复 GB/T 15190 标题")
    fixed += c.rowcount

conn.commit()

# 最终统计
total = c.execute("SELECT COUNT(*) FROM standards").fetchone()[0]
limits_count = c.execute("SELECT COUNT(*) FROM pollution_limits").fetchone()[0]
std_with_limits = c.execute("SELECT COUNT(DISTINCT standard_title) FROM pollution_limits").fetchone()[0]
print(f"\n数据库标准总数: {total}")
print(f"污染限值总数: {limits_count}")
print(f"含限值标准数: {std_with_limits}")

conn.close()
print(f"\n修复完成: {fixed} 条")
