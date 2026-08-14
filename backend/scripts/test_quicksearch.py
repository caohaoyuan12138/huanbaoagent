import httpx
import json
import re
from datetime import datetime

base = 'https://www.eiacloud.com'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': base + '/hpyzs/lawsRegulations/searchContent',
}

# 测试quickSearch API
print("Testing quickSearch API...")
keywords = ['标准', '排放', '大气', '废水', '噪声', '土壤', 'GB', 'HJ']

all_results = []
for kw in keywords:
    try:
        r = httpx.get(f'{base}/hpyzs/lawsRegulations/quickSearch',
                      headers=headers, params={'keyword': kw}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get('code') == 200 and data.get('data', {}).get('list'):
                results = data['data']['list']
                print(f"Keyword '{kw}': {len(results)} results")
                all_results.extend(results)
    except Exception as e:
        print(f"Keyword '{kw}': Error - {e}")

print(f"\nTotal results collected: {len(all_results)}")

# 去重
seen_ids = set()
unique_results = []
for item in all_results:
    fid = item.get('fileId', '')
    if fid not in seen_ids:
        seen_ids.add(fid)
        unique_results.append(item)

print(f"Unique results: {len(unique_results)}")

# 保存结果
with open('e:/TRAE SOLO CN/agent/backend/scripts/search_results.json', 'w', encoding='utf-8') as f:
    json.dump(unique_results, f, ensure_ascii=False, indent=2)

print("Results saved to search_results.json")
