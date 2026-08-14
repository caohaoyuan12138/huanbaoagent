# -*- coding: utf-8 -*-
"""调试推荐GB/T页面结构"""
import re
import requests

# 推荐GB/T 页面
url = 'https://openstd.samr.gov.cn/bzgk/std/std_list_type?r=0.1&page=1&pageSize=5&p.p1=2&p.p6=13&p.p90=circulation_date&p.p91=desc'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
r = requests.get(url, headers=headers, timeout=30)
r.encoding = r.apparent_encoding or 'utf-8'
html = r.text

# 找所有tr
trs = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
print(f"共找到 {len(trs)} 个 <tr>")
for i, tr in enumerate(trs[:8]):
    tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL)
    if not tds:
        continue
    cells = []
    for td in tds:
        clean = re.sub(r'<[^>]+>', '', td).strip()
        clean = re.sub(r'\s+', ' ', clean)
        cells.append(clean)
    print(f"\n=== TR {i} ({len(tds)} TDs) ===")
    for j, c in enumerate(cells):
        print(f"  TD[{j}]: {c[:80]}")
    # 检查第一个cell是否是数字
    print(f"  cells[0].isdigit(): {cells[0].isdigit() if cells else 'N/A'}")
