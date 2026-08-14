# -*- coding: utf-8 -*-
"""
从生态环境部官网爬取标准列表，对比数据库找出缺失的标准并补充入库
覆盖分类: 水环境/大气/噪声/土壤 等
"""
import re
import time
import json
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

# 环境部标准分类URL
CATEGORY_URLS = [
    # 水环境保护
    ("水环境质量标准", "废水", "环保", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/shjbh/shjzlbz/"),
    ("水污染物排放标准", "废水", "环保", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/shjbh/swrwpfbz/"),
    ("水相关标准", "废水", "环保", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/shjbh/xgbzh/"),
    # 大气环境保护
    ("大气环境质量标准", "废气", "环保", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/dqhjbh/dqhjzlbz/"),
    ("大气固定源污染物排放标准", "废气", "环保", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/dqhjbh/dqgdwrywrwpfbz/"),
    ("大气移动源污染物排放标准", "废气", "环保", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/dqhjbh/dqydywrwpfbz/"),
    ("大气相关标准", "废气", "环保", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/dqhjbh/xgbz/"),
    # 环境噪声与振动
    ("环境噪声与振动排放标准", "噪声", "环保", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/wlhj/hjzspfbz/"),
    ("环境噪声与振动质量标准", "噪声", "环保", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/wlhj/shjzlbz/"),
    # 土壤环境保护
    ("土壤环境保护标准", "土壤", "环保", "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/trhj/"),
    # 固体废物
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


def parse_standard_list(html):
    """从环境部标准列表页提取标准信息
    页面格式: <a href="...shtml">标准名称 GB XXXX-YYYY代替...</a>日期 实施
    """
    items = []
    # 匹配标准链接: 标题中含 GB/HJ/DB 开头的编号
    pattern = re.compile(
        r'<a[^>]+href="([^"]+\.shtml)"[^>]*>\s*([^<]+?)\s*</a>[^<]*?(\d{4}-\d{2}-\d{2})?\s*(实施|实施)?',
        re.DOTALL
    )
    for m in pattern.finditer(html):
        url = m.group(1)
        title = m.group(2).strip()
        impl_date = m.group(3) or ""

        # 跳过导航类链接
        if len(title) < 5 or '查看更多' in title or '当前位置' in title:
            continue
        if not re.search(r'(GB|HJ|DB)[\s/]*[TZ]?\s*\d', title):
            continue

        # 提取标准编号
        num_match = re.search(r'((?:GB|HJ|DB)[\s/]*[TZ]?\s*\d+(?:\.\d+)?(?:\s*[-—]\s*\d{2,4})?)', title)
        std_num = num_match.group(1).replace('—', '-').replace('–', '-').strip() if num_match else ""
        # 规范化标准编号
        std_num = re.sub(r'\s+', ' ', std_num)
        std_num = std_num.replace(' /T', '/T').replace('/ T', '/T')

        # 提取标准名称（去掉编号部分）
        std_name = re.sub(r'^(GB|HJ|DB)[\s/]*[TZ]?\s*\d+(?:\.\d+)?(?:\s*[-—–]\s*\d{2,4})?\s*', '', title).strip()
        # 去掉"代替..."部分
        std_name = re.sub(r'代替.*$', '', std_name).strip()
        # 去掉末尾括号说明
        std_name = re.sub(r'（试行）$', '', std_name).strip()

        if not std_name or len(std_name) < 3:
            std_name = title  # 用原标题

        full_url = url if url.startswith('http') else BASE + url

        items.append({
            "standard_number": std_num,
            "title": std_name,
            "full_title": title,
            "impl_date": impl_date,
            "source_url": full_url,
        })
    return items


def infer_category(title):
    """从标题推断污染类别"""
    if any(k in title for k in ['大气', '废气', '烟', '尘', '锅炉', '炉窑', '油气']):
        return '废气'
    if any(k in title for k in ['水', '污水', '废水', '河流', '流域']):
        return '废水'
    if any(k in title for k in ['噪声', '振动', '声']):
        return '噪声'
    if any(k in title for k in ['土壤', '地下水', '建设用地']):
        return '土壤'
    if any(k in title for k in ['固废', '固体废物', '垃圾', '危废']):
        return '固废'
    if any(k in title for k in ['辐射', '电磁', '放射性']):
        return '辐射'
    return '综合'


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

    # 获取已有标准编号集合
    existing_nums = set()
    for row in c.execute("SELECT standard_number FROM standards"):
        # 规范化: 去空格，统一格式
        n = re.sub(r'\s+', '', row[0]) if row[0] else ""
        existing_nums.add(n)
    print(f"数据库已有标准: {len(existing_nums)} 个编号")

    all_new = []
    seen_urls = set()

    for cat_name, default_cat, default_ind, url in CATEGORY_URLS:
        print(f"\n=== 爬取: {cat_name} ===")
        print(f"  URL: {url}")
        html = fetch(url)
        if not html:
            print(f"  [跳过] 无法获取页面")
            continue

        items = parse_standard_list(html)
        print(f"  解析到 {len(items)} 条标准")

        new_count = 0
        for item in items:
            # 去重: URL
            if item["source_url"] in seen_urls:
                continue
            seen_urls.add(item["source_url"])

            # 规范化编号用于对比
            norm_num = re.sub(r'\s+', '', item["standard_number"])
            if norm_num in existing_nums:
                continue

            # 新标准
            item["category"] = infer_category(item["title"]) or default_cat
            item["industry"] = default_ind
            item["standard_type"] = infer_standard_type(item["standard_number"])
            all_new.append(item)
            existing_nums.add(norm_num)
            new_count += 1

        print(f"  新增: {new_count} 条")

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
                item["standard_number"],
                item["title"],
                item["category"],
                item["industry"],
                item["standard_type"],
                None,  # publish_date 未知
                item["impl_date"] or None,
                item["source_url"],
                item["source_url"],  # pdf_url暂用source_url
                item["full_title"],  # content用完整标题
                now,
            ))
            inserted += 1
            print(f"  + {item['standard_number']} | {item['title'][:40]}")
        except Exception as e:
            print(f"  [错误] {item['standard_number']}: {e}")

    conn.commit()

    # 统计
    total = c.execute("SELECT COUNT(*) FROM standards").fetchone()[0]
    print(f"\n{'='*60}")
    print(f"入库: {inserted} 条")
    print(f"数据库标准总数: {total}")

    conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("从生态环境部官网爬取缺失的标准")
    print(f"数据源: {BASE}/ywgz/fgbz/bz/bzwb/")
    print("=" * 60)
    crawl()
