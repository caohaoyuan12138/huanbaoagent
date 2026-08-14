import httpx
import re
import json

base = 'https://www.eiacloud.com'

# 获取主页面
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

print("Fetching main page...")
r = httpx.get(f'{base}/hpyzs/lawsRegulations/searchContent', headers=headers, timeout=15)
print(f"Status: {r.status_code}")

# 查找所有JS文件
js_files = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', r.text)
print(f"\nJS files found: {len(js_files)}")
for j in js_files[:20]:
    print(f"  {j}")

# 查找所有可能的API调用模式
api_patterns = re.findall(r'["\'](/[^"\']*api[^"\']*)["\']', r.text, re.IGNORECASE)
print(f"\nAPI patterns found: {len(api_patterns)}")
for a in api_patterns[:20]:
    print(f"  {a}")

# 查找所有URL模式
urls = re.findall(r'["\'](/[^"\']{5,}[^"\']*)["\']', r.text)
print(f"\nAll URLs found: {len(urls)}")
seen = set()
for u in urls:
    if u not in seen and not u.startswith('#') and 'js' not in u and 'css' not in u and 'icon' not in u:
        seen.add(u)
        print(f"  {u}")
