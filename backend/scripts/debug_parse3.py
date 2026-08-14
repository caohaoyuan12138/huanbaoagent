# -*- coding: utf-8 -*-
"""测试推荐GB/T页面解析"""
import re
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://openstd.samr.gov.cn/bzgk/std/index",
}

# 使用和爬虫完全相同的URL
url = 'https://openstd.samr.gov.cn/bzgk/std/std_list_type?r=0.1&page=1&pageSize=50&p.p1=2&p.p6=13&p.p90=circulation_date&p.p91=desc'
r = requests.get(url, headers=HEADERS, timeout=30)
r.encoding = r.apparent_encoding or 'utf-8'
html = r.text

print(f"HTML length: {len(html)}")

# 检查总条数
clean = html.replace('&nbsp;', ' ').replace('\xa0', ' ')
m = re.search(r'共\s*(\d+)\s*条', clean)
print(f"get_total_count: {m.group(1) if m else 'NOT FOUND'}")

# 检查页面文本
m2 = re.search(r'共\s*\d+\s*条标准\s*\d+\s*/\s*(\d+)', clean)
print(f"total_pages: {m2.group(1) if m2 else 'NOT FOUND'}")

# 运行parse_list_page
rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
print(f"Total <tr>: {len(rows)}")

data_rows = 0
for i, row in enumerate(rows):
    tds = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
    if len(tds) < 6:
        continue
    cells = []
    for td in tds:
        c = re.sub(r'<[^>]+>', '', td).strip()
        c = re.sub(r'\s+', ' ', c)
        cells.append(c)
    if not cells[0] or not cells[0].isdigit():
        continue
    data_rows += 1
    if data_rows <= 3:
        print(f"  Row {data_rows}: std_num={cells[1][:30]}, title={cells[3][:50]}")

print(f"\nTotal data rows: {data_rows}")
