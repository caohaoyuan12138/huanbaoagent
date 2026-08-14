import requests
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

urls = [
    ("水污染物", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/shjbh/swrwpfbz/"),
    ("大气质量", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/dqhjbh/dqhjzlbz/"),
    ("环评", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/hp/pjjsdz/"),
    ("排污许可", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/pwxk/"),
]

for name, url in urls:
    print(f"\n{'='*60}")
    print(f"{name}: {url}")
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.encoding = r.apparent_encoding or "utf-8"
        html = r.text
        print(f"Status: {r.status_code}, Length: {len(html)}")

        # 所有链接
        links = re.findall(r'<a\s+href=["\']([^"\']+\.shtml)["\'][^>]*>([^<]{6,})</a>', html)
        print(f"All .shtml links: {len(links)}")

        # 看看有哪些链接
        skip = ["环境影响评价", "生态环境标准", "标准修改与解释", "标准征求意见",
                "地方标准备案", "大气环境质量标准", "大气固定源", "大气移动源",
                "水环境质量标准", "水污染物排放标准", "环境噪声排放标准",
                "声环境质量标准", "噪声环境质量标准", "空气质量",
                "石油炼制", "再生铜", "合成树脂", "外交部", "国防部"]
        for href, title in links[:30]:
            is_skip = any(k in title for k in skip)
            mark = " [SKIP]" if is_skip else ""
            print(f"  {title[:55]:55s}{mark} | {href}")

        # 检查分页
        pages = re.findall(r'\[(\d+)\]\s*\(([^)]+)\)', html)
        next_m = re.search(r'下一页.*?\(([^)]+\.shtml)\)', html)
        print(f"Pages: {pages}, Next: {next_m.group(1) if next_m else None}")
    except Exception as e:
        print(f"Error: {e}")
