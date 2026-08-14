# -*- coding: utf-8 -*-
import requests
import sqlite3

# 检查服务
for url in ['http://localhost:8000/api/health', 'http://localhost:3000']:
    try:
        r = requests.get(url, timeout=3)
        print(url, '->', r.status_code)
    except:
        print(url, '-> ERR')

# 测试限值API
conn = sqlite3.connect("env_agent.db")
c = conn.cursor()

test_nums = ['GB 12348-2008', 'GB 3552-2018', 'GB/T 14848-2017', 'GB/T 18883-2022']
for std_num in test_nums:
    row = c.execute("SELECT id, title FROM standards WHERE standard_number = ?", (std_num,)).fetchone()
    if not row:
        print(f"{std_num}: 未找到")
        continue
    sid, title = row
    r = requests.get(f"http://localhost:8000/api/knowledge/standards/{sid}/limits")
    d = r.json()
    print(f"\n{std_num} | {title}")
    print(f"  限值数: {len(d['limits'])}")
    for l in d['limits'][:3]:
        print(f"  {l['factor_name']} = {l['limit_value']} {l['unit']} | {l['description']}")

# 总体统计
total = c.execute("SELECT COUNT(*) FROM standards").fetchone()[0]
limits = c.execute("SELECT COUNT(*) FROM pollution_limits").fetchone()[0]
std_with = c.execute("SELECT COUNT(DISTINCT standard_title) FROM pollution_limits").fetchone()[0]
mee_count = c.execute("SELECT COUNT(*) FROM standards WHERE source_url LIKE '%mee.gov.cn%'").fetchone()[0]
print(f"\n=== 总体统计 ===")
print(f"标准总数: {total} (其中环境部来源: {mee_count})")
print(f"污染限值总数: {limits}")
print(f"含限值标准数: {std_with}")
conn.close()
