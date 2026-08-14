# -*- coding: utf-8 -*-
"""
从生态环境部官网爬取标准列表（含分页），补充缺失标准并修复标题
"""
import re
import time
import sqlite3
import requests
from datetime import datetime

DB_PATH = "env_agent.db"
BASE = "https://www.mee.gov.cn"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# 分类URL（含子分类）
CATEGORY_URLS = [
    ("水环境质量标准", "废水", "环保", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/shjbh/shjzlbz/"),
    ("水污染物排放标准", "废水", "环保", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/shjbh/swrwpfbz/"),
    ("水相关标准", "废水", "环保", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/shjbh/xgbzh/"),
    ("大气环境质量标准", "废气", "环保", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/dqhjbh/dqhjzlbz/"),
    ("大气固定源污染物排放标准", "废气", "环保", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/dqhjbh/dqgdwrywrwpfbz/"),
    ("大气移动源污染物排放标准", "废气", "环保", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/dqhjbh/dqydywrwpfbz/"),
    ("大气相关标准", "废气", "环保", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/dqhjbh/xgbz/"),
    ("噪声排放标准", "噪声", "环保", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/wlhj/hjzspfbz/"),
    ("噪声质量标准", "噪声", "环保", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/wlhj/shjzlbz/"),
    ("土壤环境保护标准", "土壤", "环保", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/trhj/"),
    ("固体废物污染控制标准", "固废", "环保", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/gthw/gtfwwrkzbz/"),
]


def fetch(url, retries=3):
    for i in range(retries):
        try:
            r = SESSION.get(url, timeout=30)
            r.encoding = r.apparent_encoding or "utf-8"
            if r.status_code == 200 and r.text and len(r.text) > 500:
                return r.text
        except Exception as e:
            print(f"    [重试 {i+1}] {e}")
        time.sleep(2)
    return None


def extract_std_number(title):
    """从标题中提取标准编号，支持编号在前或在后"""
    # 编号在前: GB 16297-1996 / GB/T 22733-2026 / HJ 1234-2021
    m = re.search(r'((?:GB|HJ|DB)[\s/]*[TZ]?\s*\d+(?:\.\d+)?(?:\s*[-—–]\s*\d{2,4})?)', title)
    if m:
        num = m.group(1)
        num = num.replace('—', '-').replace('–', '-')
        num = re.sub(r'\s+', ' ', num).strip()
        num = num.replace(' /T', '/T').replace('/ T', '/T')
        return num
    return ""


def extract_std_name(title, std_num):
    """从标题中提取标准名称（去掉编号部分）"""
    name = title
    # 去掉编号
    if std_num:
        name = name.replace(std_num, '')
        # 也尝试去掉各种变体
        for variant in [std_num.replace(' ', ''), std_num.replace('-', '—'),
                        std_num.replace('-', '–'), std_num.replace('/T', '/ T')]:
            name = name.replace(variant, '')
    # 去掉"代替..."部分
    name = re.sub(r'代替.*$', '', name).strip()
    # 去掉"（试行）"
    name = re.sub(r'（试行）$', '', name).strip()
    # 去掉"（自XXXX起废止）"等
    name = re.sub(r'（自.*?废止）', '', name).strip()
    # 去掉多余空格
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def parse_standard_list(html):
    """从环境部标准列表页提取标准信息"""
    items = []
    # 匹配标准链接
    pattern = re.compile(
        r'<a[^>]+href="([^"]+\.shtml)"[^>]*>\s*([^<]+?)\s*</a>',
        re.DOTALL
    )
    for m in pattern.finditer(html):
        url = m.group(1)
        title = m.group(2).strip()

        # 跳过导航类链接
        if len(title) < 5:
            continue
        if '查看更多' in title or '当前位置' in title or '首页' in title:
            continue
        if '生态环境标准' in title and len(title) < 15:
            continue

        # 必须含标准编号
        if not re.search(r'(GB|HJ|DB)[\s/]*[TZ]?\s*\d', title):
            continue

        # 跳过公告类（非标准）
        if '公告' in title and '关于' in title:
            continue

        std_num = extract_std_number(title)
        std_name = extract_std_name(title, std_num)

        # 如果名称为空或太短，用原标题
        if not std_name or len(std_name) < 3:
            std_name = title

        # 提取实施日期（链接后面的文本）
        # 查找链接后的日期
        after_text = html[m.end():m.end()+200]
        date_m = re.search(r'(\d{4}-\d{2}-\d{2})\s*实施', after_text)
        impl_date = date_m.group(1) if date_m else ""

        full_url = url if url.startswith('http') else BASE + url

        items.append({
            "standard_number": std_num,
            "title": std_name,
            "full_title": title,
            "impl_date": impl_date,
            "source_url": full_url,
        })
    return items


def find_pagination(html, base_url):
    """查找分页链接"""
    pages = set()
    # 查找 index_1.shtml, index_2.shtml 等分页
    for m in re.finditer(r'href="([^"]*index_(\d+)\.shtml)"', html):
        pages.add(m.group(1))
    return sorted(pages)


def infer_category(title, default_cat):
    if any(k in title for k in ['大气', '废气', '烟', '尘', '锅炉', '炉窑', '油气', '挥发性']):
        return '废气'
    if any(k in title for k in ['水', '污水', '废水', '河流', '流域', '船舶水']):
        return '废水'
    if any(k in title for k in ['噪声', '振动', '声']):
        return '噪声'
    if any(k in title for k in ['土壤', '地下水', '建设用地', '污染地块']):
        return '土壤'
    if any(k in title for k in ['固废', '固体废物', '垃圾', '危废', '废盐', '废硫酸', '锰渣', '石膏']):
        return '固废'
    if any(k in title for k in ['辐射', '电磁', '放射性']):
        return '辐射'
    return default_cat


def infer_standard_type(std_num):
    if not std_num:
        return "国家标准"
    if std_num.startswith('GB/T'):
        return "推荐性国家标准"
    if std_num.startswith('GB'):
        return "强制性国家标准"
    if std_num.startswith('HJ'):
        return "行业标准"
    if std_num.startswith('DB'):
        return "地方标准"
    return "国家标准"


def crawl():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()

    # 获取已有标准编号集合（规范化）
    existing_nums = set()
    for row in c.execute("SELECT standard_number FROM standards"):
        n = re.sub(r'\s+', '', row[0]) if row[0] else ""
        existing_nums.add(n)
    print(f"数据库已有标准: {len(existing_nums)} 个编号")

    all_new = []
    seen_urls = set()

    for cat_name, default_cat, default_ind, url in CATEGORY_URLS:
        print(f"\n=== 爬取: {cat_name} ===")
        html = fetch(url)
        if not html:
            print(f"  [跳过] 无法获取页面")
            continue

        # 查找分页
        pages = find_pagination(html, url)
        all_pages = [url] + [BASE + p if not p.startswith('http') else p for p in pages]
        print(f"  发现 {len(all_pages)} 个分页")

        cat_new = 0
        for page_idx, page_url in enumerate(all_pages):
            if page_idx > 0:
                time.sleep(1)
                html = fetch(page_url)
                if not html:
                    continue

            items = parse_standard_list(html)
            for item in items:
                if item["source_url"] in seen_urls:
                    continue
                seen_urls.add(item["source_url"])

                norm_num = re.sub(r'\s+', '', item["standard_number"])
                if norm_num in existing_nums:
                    continue

                item["category"] = infer_category(item["title"], default_cat)
                item["industry"] = default_ind
                item["standard_type"] = infer_standard_type(item["standard_number"])
                all_new.append(item)
                existing_nums.add(norm_num)
                cat_new += 1

        print(f"  新增: {cat_new} 条")
        time.sleep(1)

    # 写入数据库
    print(f"\n{'='*60}")
    print(f"共发现 {len(all_new)} 条新标准")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    inserted = 0
    for item in all_new:
        try:
            c.execute("""
                INSERT INTO standards
                    (standard_number, title, category, industry, standard_type,
                     publish_date, implement_date, source_url, pdf_url, content, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item["standard_number"], item["title"], item["category"],
                item["industry"], item["standard_type"], None,
                item["impl_date"] or None, item["source_url"], item["source_url"],
                item["full_title"], now,
            ))
            inserted += 1
            print(f"  + {item['standard_number']} | {item['title'][:40]}")
        except Exception as e:
            print(f"  [错误] {item['standard_number']}: {e}")

    conn.commit()
    total = c.execute("SELECT COUNT(*) FROM standards").fetchone()[0]
    print(f"\n{'='*60}")
    print(f"入库: {inserted} 条")
    print(f"数据库标准总数: {total}")
    conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("从生态环境部官网爬取缺失标准（含分页）")
    print("=" * 60)
    crawl()
