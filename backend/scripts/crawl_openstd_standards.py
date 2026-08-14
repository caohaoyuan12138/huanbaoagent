# -*- coding: utf-8 -*-
"""
openstd.samr.gov.cn 国家标准爬虫
爬取强制GB + 推荐GB/T 标准，覆盖环保/化工/医药/新能源/新材料/日化等行业
输出 JSONL 格式，支持断点续爬
"""
import re
import json
import time
import os
import sys
import subprocess
from datetime import datetime
from urllib.parse import urljoin

# ============ 配置 ============
BASE_URL = "https://openstd.samr.gov.cn"
LIST_URL = BASE_URL + "/bzgk/std/std_list_type"
DETAIL_URL = BASE_URL + "/bzgk/std/newGbInfo"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "openstd_standards.jsonl")
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "openstd_progress.json")

HEADERS = [
    "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,*/*;q=0.8",
    "Accept-Language: zh-CN,zh;q=0.9",
]

# ICS 分类覆盖: 环保/化工/医药/新能源/新材料/日化/纺织/橡胶
ICS_CONFIGS = [
    # (ics_code, p1, label)
    ("13", "1", "环保-强制GB"),
    ("13", "2", "环保-推荐GB/T"),
    ("71", "1", "化工-强制GB"),
    ("71", "2", "化工-推荐GB/T"),
    ("71.100", "1", "日化-强制GB"),
    ("71.100", "2", "日化-推荐GB/T"),
    ("11", "1", "医药-强制GB"),
    ("11", "2", "医药-推荐GB/T"),
    ("27", "1", "新能源-强制GB"),
    ("27", "2", "新能源-推荐GB/T"),
    ("29", "1", "电气-强制GB"),
    ("29", "2", "电气-推荐GB/T"),
    ("59", "1", "纺织-强制GB"),
    ("59", "2", "纺织-推荐GB/T"),
    ("83", "1", "橡胶塑料-强制GB"),
    ("83", "2", "橡胶塑料-推荐GB/T"),
]

PAGE_SIZE = 200
SLEEP_LIST = 0.3
SLEEP_DETAIL = 0.15
REQUEST_TIMEOUT = 30


def fetch(url, max_retries=3):
    """Curl 封装 GET 请求"""
    cmd = ["curl", "-s", "-m", str(REQUEST_TIMEOUT), "-L", url]
    for h in HEADERS:
        cmd.extend(["-H", h])
    for attempt in range(max_retries):
        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=REQUEST_TIMEOUT + 5
            )
            if r.returncode == 0 and r.stdout:
                return r.stdout
            elif r.returncode != 0:
                print(f"  [WARN] curl exit code {r.returncode}, stderr: {r.stderr[:200]}", file=sys.stderr)
        except Exception as e:
            print(f"  [WARN] fetch attempt {attempt+1} failed: {e}", file=sys.stderr)
        if attempt < max_retries - 1:
            time.sleep(1)
    return None


def parse_list_page(html):
    """解析列表页，返回标准列表"""
    # 收集所有 showInfo 条目，按 hcno 合并（同一行有编号和名称两个列）
    raw = {}
    for m in re.finditer(r"showInfo\('([0-9A-F]{32})'[^>]*>\s*([^<]+)</a>", html, re.DOTALL):
        hcno = m.group(1)
        text = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        if hcno not in raw:
            raw[hcno] = {"hcno": hcno, "texts": []}
        raw[hcno]["texts"].append(text)

    items = []
    for hcno, data in raw.items():
        texts = data["texts"]
        item = {"hcno": hcno}
        # 尝试区分标准编号和名称
        # 标准编号通常匹配模式: GB 12345-2020, GB/T 12345-2020, HJ 1234-2020
        std_num = ""
        name = ""
        for t in texts:
            if re.match(r'^[A-Z]{1,6}[\s/]*\d+', t):
                if not std_num:
                    std_num = t
            else:
                if not name:
                    name = t
        item["standard_number_raw"] = std_num or (texts[0] if texts else "")
        item["title_raw"] = name or (texts[1] if len(texts) > 1 else texts[0] if texts else "")
        items.append(item)

    return items


def parse_standard_number(raw):
    """标准化编号: GB 16297-1996, GB/T 12345-2020"""
    s = raw.strip()
    # 移除多余空格: "GB  16297-1996" → "GB 16297-1996"
    s = re.sub(r'\s+', ' ', s)
    return s


def parse_list_detail(html, items):
    """从列表页解析额外字段（发布日期、实施日期、状态等）"""
    for item in items:
        hcno = item["hcno"]
        # 找到包含此 hcno 的 <tr> 块
        i = html.find(hcno)
        if i < 0:
            continue
        row_start = html.rfind("<tr", 0, i)
        row_end = html.find("</tr>", i)
        if row_start < 0 or row_end < 0:
            continue
        row_html = html[row_start:row_end + 5]
        # 提取所有 td 内容
        tds = []
        for m in re.finditer(r'<t[dh][^>]*>(.*?)</t[dh]>', row_html, re.DOTALL):
            txt = m.group(1)
            txt = re.sub(r'<[^>]+>|\s+', ' ', txt).strip()
            tds.append(txt)

        # 根据列数映射: 常见结构: 序号, 编号, 名称, 状态, 发布日期, 实施日期, 操作
        # 或: 序号, 编号, 名称, 状态, 代替标准, 发布日期, 实施日期, 操作
        if len(tds) >= 7:
            # 找到状态列 (包含 现行/废止/即将实施)
            status = ""
            pub_date = ""
            impl_date = ""
            for td in tds[3:]:
                for kw in ["现行", "废止", "即将实施", "即将"]:
                    if kw in td:
                        status = td
                        break
                if re.match(r'\d{4}-\d{2}-\d{2}', td):
                    if not pub_date:
                        pub_date = td
                    elif not impl_date:
                        impl_date = td
            if not status:
                status = tds[3] if len(tds) > 3 else ""
            if not pub_date:
                pub_date = tds[4] if len(tds) > 4 else ""
            if not impl_date:
                impl_date = tds[5] if len(tds) > 5 else ""

            item["status"] = status
            item["publish_date"] = pub_date
            item["implement_date"] = impl_date
    return items


def parse_detail_page(html, hcno):
    """解析详情页，返回字段 dict"""
    data = {"hcno": hcno}

    # 标准号
    m = re.search(r'标准号[：:]\s*([^<]+)', html)
    if m:
        data["standard_number"] = m.group(1).strip()

    # 中文标准名称
    m = re.search(r'中文标准名称[：:]\s*<b>([^<]+)</b>', html)
    if m:
        data["title"] = m.group(1).strip()

    # 英文标准名称
    m = re.search(r'英文标准名称[：:]\s*([^<]+)', html)
    if m:
        data["english_title"] = m.group(1).strip()

    # 标准状态
    m = re.search(r'标准状态[：:]\s*<span[^>]*>([^<]+)</span>', html)
    if m:
        data["status"] = m.group(1).strip()

    # ICS
    m = re.search(r'国际标准分类号[（(]ICS[）)]\s*</div>\s*<div[^>]*class="[^"]*content[^"]*"[^>]*>\s*([^<]+)', html)
    if m:
        data["ics"] = m.group(1).strip()

    # CCS
    m = re.search(r'中国标准分类号[（(]CCS[）)]\s*</div>\s*<div[^>]*class="[^"]*content[^"]*"[^>]*>\s*([^<]+)', html)
    if m:
        data["ccs"] = m.group(1).strip()

    # 发布日期
    m = re.search(r'发布日期\s*</div>\s*<div[^>]*class="[^"]*content[^"]*"[^>]*>\s*(\d{4}-\d{2}-\d{2})', html)
    if m:
        data["publish_date"] = m.group(1).strip()

    # 实施日期
    m = re.search(r'实施日期\s*</div>\s*<div[^>]*class="[^"]*content[^"]*"[^>]*>\s*(\d{4}-\d{2}-\d{2})', html)
    if m:
        data["implement_date"] = m.group(1).strip()

    # 主管部门
    m = re.search(r'主管部门\s*</div>\s*<div[^>]*class="[^"]*content[^"]*"[^>]*>\s*([^<]+)', html)
    if m:
        data["competent_authority"] = m.group(1).strip()

    # 归口部门
    m = re.search(r'归口部门\s*</div>\s*<div[^>]*class="[^"]*content[^"]*"[^>]*>\s*([^<]+)', html)
    if m:
        data["technical_committee"] = m.group(1).strip()

    # 发布单位
    m = re.search(r'发布单位\s*</div>\s*<div[^>]*class="[^"]*content[^"]*"[^>]*>\s*([^<]+)', html)
    if m:
        data["issuing_authority"] = m.group(1).strip()

    # 备注
    m = re.search(r'备注\s*</div>\s*<div[^>]*class="[^"]*content[^"]*"[^>]*>\s*([^<]+)', html)
    if m:
        data["remark"] = m.group(1).strip()

    # 在线预览/下载链接的 hcno
    m = re.search(r'class="[^"]*xz_btn[^"]*"[^>]*data-value="([^"]+)"', html)
    if m:
        data["download_hcno"] = m.group(1).strip()

    return data


def write_jsonl(items, mode="a"):
    """追加写入 JSONL 文件"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, mode, encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def write_progress(progress):
    """写入进度文件"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def load_progress():
    """读取进度文件"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed_ics": [], "completed_detail": False}


def count_pages(html):
    """从列表页中提取总页数"""
    m = re.search(r'var\s+count\s*=\s*["\']?(\d+)["\']?', html)
    if m:
        return int(m.group(1))
    # 尝试从分页器中提取
    m = re.search(r'pages\s*:\s*["\"](\d+)["\"]', html)
    if m:
        return int(m.group(1))
    return 0


def crawl_ics(ics, p1, label):
    """爬取单个 ICS 分类的所有标准"""
    print(f"\n{'=' * 60}")
    print(f"[{label}] ICS={ics}, p1={p1}")
    print(f"{'=' * 60}")

    all_items = []
    total_pages = 0

    # 第1页: 获取总页数
    url = f"{LIST_URL}?r=0.1&page=1&pageSize={PAGE_SIZE}&p.p1={p1}&p.p6={ics}&p.p90=circulation_date&p.p91=desc"
    html = fetch(url)
    if not html:
        print(f"  [ERROR] 无法获取第1页")
        return []

    total_pages = count_pages(html)
    if total_pages == 0:
        # 尝试从 row count 推断
        items = parse_list_page(html)
        if items:
            # 估算: 每页 ~PAGE_SIZE，总条数 = count
            # 从统计文本中提取
            m = re.search(r'共[^<]*(\d+)<', html)
            if m:
                total_count = int(m.group(1))
                total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)
                print(f"  从统计文本解析: 共{total_count}条, {total_pages}页")
            else:
                total_pages = 1
        else:
            total_pages = 0

    print(f"  总页数: {total_pages}")

    if total_pages == 0:
        return []

    # 遍历所有页
    for page in range(1, total_pages + 1):
        if page == 1:
            page_html = html
        else:
            page_url = f"{LIST_URL}?r=0.1&page={page}&pageSize={PAGE_SIZE}&p.p1={p1}&p.p6={ics}&p.p90=circulation_date&p.p91=desc"
            page_html = fetch(page_url)
            if not page_html:
                print(f"  [WARN] 第{page}页获取失败，跳过")
                continue
            time.sleep(SLEEP_LIST)

        items = parse_list_page(page_html)
        if not items:
            continue

        # 解析行内额外字段
        row_items = parse_list_detail(page_html, items)

        # 标准化编号
        for item in row_items:
            item["standard_number"] = parse_standard_number(item.get("standard_number_raw", ""))
            item["ics_source"] = ics
            item["standard_type"] = "强制国标" if p1 == "1" else "推荐国标"

        all_items.extend(row_items)
        print(f"  第{page}/{total_pages}页: {len(row_items)}条, 累计{len(all_items)}条", flush=True)

    # 去重 (按 hcno)
    seen = set()
    deduped = []
    for item in all_items:
        if item["hcno"] not in seen:
            seen.add(item["hcno"])
            deduped.append(item)

    print(f"  去重后: {len(deduped)}条")
    return deduped


def crawl_detail(item):
    """爬取单个标准的详情页"""
    hcno = item["hcno"]
    url = f"{DETAIL_URL}?hcno={hcno}"
    html = fetch(url)
    if not html:
        return item

    detail = parse_detail_page(html, hcno)
    item.update(detail)
    return item


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    progress = load_progress()
    completed_ics = set(progress.get("completed_ics", []))

    all_standards = []

    # Phase 1: 爬取列表
    for ics, p1, label in ICS_CONFIGS:
        key = f"{ics}_{p1}"
        if key in completed_ics:
            print(f"\n[{label}] 已爬取，跳过")
            continue

        items = crawl_ics(ics, p1, label)
        if items:
            write_jsonl(items, "a")
            all_standards.extend(items)

        completed_ics.add(key)
        write_progress({
            "completed_ics": list(completed_ics),
            "completed_detail": False,
            "total_list": len(all_standards),
            "updated_at": datetime.now().isoformat(),
        })

    print(f"\n\n列表页爬取完成，共 {len(all_standards)} 条标准")

    # Phase 2: 爬取详情页
    print(f"\n{'=' * 60}")
    print("开始爬取详情页...")
    print(f"{'=' * 60}")

    # 从 JSONL 重新读取所有 hcno
    all_hcnos = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        item = json.loads(line)
                        if item.get("hcno"):
                            all_hcnos.add(item["hcno"])
                    except:
                        pass

    # 已爬取详情的 hcno
    detail_done = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        item = json.loads(line)
                        if item.get("title") or item.get("ics"):
                            item_hcno = item.get("hcno")
                            if item_hcno:
                                detail_done.add(item_hcno)
                    except:
                        pass

    pending = all_hcnos - detail_done
    print(f"  总计 {len(all_hcnos)} 条, 已爬详情 {len(detail_done)} 条, 待爬 {len(pending)} 条")

    # 按批次爬取详情
    batch_size = 50
    pending_list = list(pending)
    for i in range(0, len(pending_list), batch_size):
        batch = pending_list[i:i+batch_size]
        updated = []
        for hcno in batch:
            # 从 JSONL 读取原始行
            item = {"hcno": hcno}
            crawled = crawl_detail(item)
            if crawled.get("title"):
                detail_done.add(hcno)
            updated.append(crawled)
            time.sleep(SLEEP_DETAIL)

        # 写回 JSONL (追加)
        write_jsonl(updated, "a")

        progress_pct = min(100, (len(detail_done) / len(all_hcnos)) * 100) if all_hcnos else 0
        print(f"  详情进度: {len(detail_done)}/{len(all_hcnos)} ({progress_pct:.1f}%)", flush=True)

    write_progress({
        "completed_ics": list(completed_ics),
        "completed_detail": True,
        "total_list": len(all_hcnos),
        "detail_done": len(detail_done),
        "updated_at": datetime.now().isoformat(),
    })

    print(f"\n{'=' * 60}")
    print(f"爬取完成!")
    print(f"  列表: {len(all_hcnos)} 条")
    print(f"  详情: {len(detail_done)} 条")
    print(f"  输出: {OUTPUT_FILE}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()