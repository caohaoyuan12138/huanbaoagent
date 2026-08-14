"""验证MEE网站详情页是否都是跳转页"""
import requests
import re
import sys

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def fetch(url):
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = r.apparent_encoding or 'utf-8'
        return r.text
    except:
        return None

# 测试列表页
list_urls = [
    ('大气固定源', 'https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/dqhjbh/dqgdwrywrwpfbz/'),
    ('水污染物', 'https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/shjbh/swrwpfbz/'),
    ('噪声质量', 'https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/wlhj/shjzlbz/'),
    ('固废', 'https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/gthw/gtfwwrkzbz/'),
    ('核辐射', 'https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/hxxhj/fsxhjbz/'),
]

link_pattern = re.compile(r'<a\s+href=["\']([^"\']+\.(?:shtml|htm))["\'][^>]*>([^<]{10,})</a>')
skip_kw = ['更多', '查看', '首页', '尾页', '上一页', '下一页', '跳', '标准发布', '标准解读',
           '标准文本', '标准修改', '标准征求意见', '地方标准备案', '标准管理', '环境质量',
           '污染物排放', '相关标准', '噪声排放', '声环境', '固体废物污染控制',
           '危险废物鉴别', '其他相关', '离开生态环境部', '是否继续', '即将离开', '点击继续']

for name, url in list_urls:
    html = fetch(url)
    if not html:
        print(f'  [{name}] 获取失败')
        continue

    has_redirect = '即将离开' in html or '是否继续' in html
    items = link_pattern.findall(html)
    print(f'\n[{name}] has_redirect={has_redirect}, total_links={len(items)}')

    valid = 0
    for href, title in items:
        title = title.strip()
        if any(k in title for k in skip_kw):
            continue
        if len(title) < 5:
            continue
        abs_url = href if href.startswith('http') else urljoin(url, href)
        detail = fetch(abs_url)
        if not detail:
            print(f'  SKIP(fetch failed): {title[:40]}')
            continue
        if '即将离开' in detail or '是否继续' in detail:
            print(f'  SKIP(redirect): {title[:40]}')
            continue
        valid += 1
        num_m = re.search(r'标准号[：:]\s*([A-Z]{1,4}[\s/]*\d+(?:\.\d+)?[—\-‐-]\d{4})', detail)
        num = num_m.group(1) if num_m else '?'
        h1_m = re.search(r'<h1[^>]*>([^<]+)</h1>', detail)
        h1 = h1_m.group(1).strip() if h1_m else title
        print(f'  OK: {num} | {h1[:50]}')
        if valid >= 3:
            break

print('\nDone')
