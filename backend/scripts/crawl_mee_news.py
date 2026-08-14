# -*- coding: utf-8 -*-
"""
从生态环境部(MEE)官网爬取环保资讯
抓取真实新闻文章，包含正确的原文链接
"""
import re
import time
import sqlite3
import requests
from urllib.parse import urljoin
from datetime import datetime

DB_PATH = "env_agent.db"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
MEE = "https://www.mee.gov.cn"

# MEE新闻资讯栏目
NEWS_SECTIONS = [
    ("政策解读", "https://www.mee.gov.cn/zcwj/zcjd/", "政策解读"),
    ("政策文件", "https://www.mee.gov.cn/zcwj/zcfg/", "政策法规"),
    ("部务公告", "https://www.mee.gov.cn/xxgk2018/xxgk/xxgk03/", "政策法规"),
    ("新闻发布", "https://www.mee.gov.cn/ywdt/xwfb/", "环保新闻"),
    ("各地动态", "https://www.mee.gov.cn/ywdt/gddt/", "行业动态"),
    ("部领导活动", "https://www.mee.gov.cn/ywdt/hjyw/", "环保新闻"),
]

MAX_PAGES = 3

# 允许的域名白名单
ALLOWED_DOMAINS = [
    "mee.gov.cn",
    "gov.cn",
    "nhc.gov.cn",
    "ndrc.gov.cn",
    "miit.gov.cn",
    "mnr.gov.cn",
    "mee.gov.cn",
]


def is_safe_url(url):
    """检查URL是否安全（仅允许政府官网域名）"""
    if not url:
        return False
    url_lower = url.lower()
    # 检查是否包含可疑关键词
    suspicious = ["sex", "porn", "adult", "xxx", "gamble", "casino", "色情", "赌博"]
    if any(k in url_lower for k in suspicious):
        return False
    # 检查是否是允许的域名
    return any(d in url_lower for d in ALLOWED_DOMAINS)


def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.encoding = r.apparent_encoding or "utf-8"
        return r.text
    except:
        return None


def extract_news_items(html, base_url):
    """从新闻列表页提取新闻条目"""
    items = []

    # 匹配新闻链接
    for m in re.finditer(r'<a\s+href=["\']([^"\']+\.shtml)["\'][^>]*>([^<]{10,})</a>', html):
        href = m.group(1)
        title = m.group(2).strip()

        # 过滤导航/翻页
        skip = ["更多", "首页", "尾页", "上一页", "下一页", "跳转",
                "网站声明", "网站地图", "联系我们", "京ICP",
                "离开", "是否继续"]
        if any(k in title for k in skip):
            continue
        if len(title) < 10:
            continue

        abs_url = urljoin(base_url, href)
        items.append({"url": abs_url, "title": title})

    return items


def extract_date_from_url(url):
    """从URL中提取日期 /202507/t20250715_xxx.shtml"""
    m = re.search(r'/t(\d{8})_', url)
    if m:
        d = m.group(1)
        return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
    return None


def extract_pagination(html, base_url):
    """提取分页"""
    pages = []
    for m in re.finditer(r'\[(\d+)\]\s*\(([^)]+)\)', html):
        num = int(m.group(1))
        url = urljoin(base_url, m.group(2))
        pages.append((num, url))
    next_m = re.search(r'下一页.*?\(([^)]+\.shtml)\)', html)
    if next_m:
        next_url = urljoin(base_url, next_m.group(1))
        if not any(p[1] == next_url for p in pages):
            pages.append((len(pages) + 1, next_url))
    return pages


def parse_news_detail(html, url, list_title):
    """解析新闻详情页"""
    news = {
        "title": list_title,
        "summary": "",
        "source": "生态环境部",
        "url": url,
        "published_at": "",
        "category": "环保新闻",
        "content": "",
        "tags": [],
    }

    # H1标题
    h1 = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
    if h1:
        h1_text = h1.group(1).strip()
        if "即将离开" not in h1_text and "是否继续" not in h1_text:
            news["title"] = h1_text

    # 来源
    src_m = re.search(r'来源[：:]\s*([^\s<]{2,20})', html)
    if src_m:
        news["source"] = src_m.group(1).strip()

    # 发布日期
    pub = re.search(r'(\d{4}-\d{2}-\d{2})', html)
    if pub:
        news["published_at"] = pub.group(1)
    else:
        d = extract_date_from_url(url)
        if d:
            news["published_at"] = d

    # 内容摘要 - 取第一段有意义的文字
    # 先尝试找"为"开头的段落
    content_m = re.search(r'<p[^>]*>([为近日据根据本][^<]{30,500})</p>', html)
    if content_m:
        text = content_m.group(1).strip()
        news["content"] = text
        news["summary"] = text[:100] + "..." if len(text) > 100 else text
    else:
        # 取前几个p标签的内容
        ps = re.findall(r'<p[^>]*>([^<]{30,})</p>', html)
        if ps:
            text = ps[0].strip()
            news["content"] = text
            news["summary"] = text[:100] + "..." if len(text) > 100 else text

    return news


def crawl():
    all_news = []
    seen_urls = set()

    print("=" * 60)
    print("从 MEE 官网爬取环保资讯...")
    print("=" * 60)

    for section_name, section_url, category in NEWS_SECTIONS:
        print(f"\n[栏目] {section_name}")
        page_num = 0
        current_url = section_url

        while page_num < MAX_PAGES:
            page_num += 1
            html = fetch(current_url)
            if not html:
                print(f"  第{page_num}页: 请求失败")
                break

            items = extract_news_items(html, current_url)
            print(f"  第{page_num}页: 找到 {len(items)} 条新闻链接")

            if not items:
                break

            for item in items:
                if item["url"] in seen_urls:
                    continue
                seen_urls.add(item["url"])

                # URL安全检查
                if not is_safe_url(item["url"]):
                    print(f"  跳过不安全URL: {item['url']}")
                    continue

                detail_html = fetch(item["url"])
                if not detail_html:
                    continue

                news = parse_news_detail(detail_html, item["url"], item["title"])
                news["category"] = category

                if news["published_at"]:
                    all_news.append(news)

                time.sleep(0.15)

            # 分页
            pages = extract_pagination(html, current_url)
            if not pages:
                break
            next_page = sorted(pages, key=lambda x: x[0])
            if page_num + 1 <= max(p[0] for p in next_page):
                current_url = next_page[0][1]
            else:
                break

            time.sleep(0.3)

    print(f"\n{'=' * 60}")
    print(f"爬取完成: 共 {len(all_news)} 条资讯")
    print(f"{'=' * 60}")
    return all_news


def save(news_list):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()

    inserted = updated = 0

    for news in news_list:
        title = news.get("title", "").strip()
        if not title:
            continue

        c.execute("SELECT id FROM news_items WHERE title = ?", (title,))
        existing = c.fetchone()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pub_date = news.get("published_at", "")

        if existing:
            c.execute("""
                UPDATE news_items SET
                    summary = COALESCE(?, summary),
                    source = COALESCE(?, source),
                    url = COALESCE(?, url),
                    published_at = COALESCE(?, published_at),
                    category = COALESCE(?, category),
                    content = COALESCE(?, content),
                    tags = COALESCE(?, tags)
                WHERE id = ?
            """, (
                news.get("summary", ""),
                news.get("source", ""),
                news.get("url", ""),
                pub_date,
                news.get("category", ""),
                news.get("content", ""),
                "[]",
                existing[0],
            ))
            updated += 1
        else:
            c.execute("""
                INSERT INTO news_items
                    (title, summary, source, url, published_at, category, content, tags, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                title,
                news.get("summary", ""),
                news.get("source", ""),
                news.get("url", ""),
                pub_date,
                news.get("category", ""),
                news.get("content", ""),
                "[]",
                now,
            ))
            inserted += 1

    conn.commit()

    # 统计
    c.execute("SELECT COUNT(*) FROM news_items")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM news_items WHERE url IS NOT NULL AND url != '' AND url != 'https://www.mee.gov.cn/'")
    with_real_url = c.fetchone()[0]
    conn.close()

    return inserted, updated, total, with_real_url


def fix_existing_urls():
    """修复现有新闻的URL - 清除指向首页的无效URL"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()

    # 将指向首页的URL设为空
    c.execute("UPDATE news_items SET url = '' WHERE url = 'https://www.mee.gov.cn/' OR url = 'https://www.nhc.gov.cn/'")
    fixed = c.rowcount

    # 删除含可疑关键词的URL
    c.execute("DELETE FROM news_items WHERE lower(url) LIKE '%sex%' OR lower(url) LIKE '%porn%' OR lower(url) LIKE '%adult%' OR lower(url) LIKE '%xxx%' OR lower(url) LIKE '%gamble%'")
    deleted = c.rowcount

    conn.commit()
    conn.close()
    return fixed, deleted


if __name__ == "__main__":
    # 1. 修复现有数据
    fixed, deleted = fix_existing_urls()
    print(f"修复现有URL: {fixed} 条设为空, 删除 {deleted} 条可疑记录")

    # 2. 爬取新资讯
    news = crawl()

    # 3. 保存
    inserted, updated, total, with_url = save(news)

    print(f"\n数据库更新: 新增 {inserted}, 更新 {updated}")
    print(f"资讯总计: {total} 条")
    print(f"有真实链接: {with_url} 条")

    # 输出示例
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT title, source, url, published_at, category FROM news_items ORDER BY id DESC LIMIT 15")
    print(f"\n最新资讯:")
    for r in c.fetchall():
        url_short = r[2][:60] if r[2] else "(空)"
        print(f"  {r[3]} | {r[4]} | {r[1]} | {r[0][:40]} | {url_short}")
    conn.close()
