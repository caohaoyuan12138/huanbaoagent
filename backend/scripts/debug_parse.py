# -*- coding: utf-8 -*-
"""调试openstd页面HTML结构"""
import re
import requests

url = 'https://openstd.samr.gov.cn/bzgk/std/std_list_type?r=0.1&page=1&pageSize=2&p.p1=1&p.p6=13&p.p90=circulation_date&p.p91=desc'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
r = requests.get(url, headers=headers, timeout=30)
r.encoding = r.apparent_encoding or 'utf-8'
html = r.text

# 找所有tr
trs = re.findall(r'<tr[^>]*>.*?</tr>', html, re.DOTALL)
print(f"共找到 {len(trs)} 个 <tr>")
for i, tr in enumerate(trs[:6]):
    print(f"\n=== TR {i} ===")
    tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL)
    for j, td in enumerate(tds):
        clean = re.sub(r'<[^>]+>', '', td).strip()
        print(f"  TD[{j}]: {clean[:80]}")
    # 检查showInfo
    shows = re.findall(r"showInfo\('([^']+)'\)", tr)
    if shows:
        print(f"  showInfo hcno: {shows[0]}")
    # 检查a标签
    links = re.findall(r'<a[^>]*>([^<]+)</a>', tr)
    if links:
        print(f"  links: {links}")
