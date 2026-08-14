"""
EIA Cloud 环境标准数据抓取脚本 - 最终版
从 https://www.eiacloud.com/hpyzs/lawsRegulations/searchContent 抓取环境标准数据
"""
import httpx
import json
import re
import time
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

# 数据库路径
DB_PATH = "e:/TRAE SOLO CN/agent/backend/env_agent.db"
BASE_URL = "https://www.eiacloud.com"

# 请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': BASE_URL + '/hpyzs/lawsRegulations/searchContent',
}

# 行业映射 - 将EIA Cloud的fileType映射到数据库的行业字段
FILE_TYPE_TO_INDUSTRY = {
    '标准导则': '通用行业',
    '法律法规': '通用行业',
    '1': '通用行业',
    '2': '通用行业',
    'general': '通用行业',
    '通用': '通用行业',
    'Total 100': '通用行业',
}

# 行业关键词映射
INDUSTRY_KEYWORDS = {
    '电力': ['发电', '火力', '锅炉', '热力'],
    '钢铁': ['钢铁', '炼焦', '铁合金'],
    '水泥': ['水泥'],
    '化工': ['化工', '化学原料', '化肥'],
    '石油': ['石油', '石化', '炼油'],
    '制药': ['制药', '医药', '生物药品'],
    '印染': ['印染', '纺织', '化纤'],
    '电镀': ['电镀', '表面工程'],
    '造纸': ['造纸', '纸制品'],
    '电解铝': ['电解铝', '铝工业'],
    '煤炭': ['煤炭', '洗选'],
    '有色金属': ['有色', '铜', '铝', '铅', '锌'],
    '建材': ['建材', '陶瓷', '玻璃'],
    '电镀': ['电镀'],
    '垃圾焚烧': ['垃圾焚烧', '固废焚烧'],
    '危废处理': ['危废', '危险废物'],
    '固废处理': ['固废', '固体废物'],
    '污水厂': ['污水', '废水处理', '污水处理厂'],
}

# 类别关键词映射
CATEGORY_KEYWORDS = {
    '废气': ['废气', '大气', '烟', '尘', '颗粒物', '二氧化硫', '氮氧化物', 'VOCs', '挥发性有机物', '烟气'],
    '废水': ['废水', '污水', '水污染', 'COD', '氨氮', '总磷', '总氮', '石油类'],
    '噪声': ['噪声', '噪音', '厂界'],
    '土壤': ['土壤', '耕地'],
    '地下水': ['地下水', '潜水'],
    '固废': ['固废', '危废', '固体废物', '危险废物', '一般固废'],
    '环境空气': ['环境空气', '空气质量', '环境空气质量'],
    '职业病危害': ['职业病', '职业卫生', '工作场所'],
}


def clean_industry(file_type: str, title: str) -> str:
    """清理行业字段"""
    if not file_type:
        file_type = ''
    file_type = file_type.strip()

    # 从fileType映射
    if file_type in FILE_TYPE_TO_INDUSTRY:
        return FILE_TYPE_TO_INDUSTRY[file_type]

    # 清理 Total X 模式
    match = re.match(r'Total\s*(\d+)', file_type, re.IGNORECASE)
    if match:
        return '通用行业'

    # 从标题提取行业
    title_lower = title.lower()
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in title_lower:
                return industry

    return '通用行业'


def clean_category(title: str) -> str:
    """从标题推断类别"""
    if not title:
        return '其他'

    title_lower = title.lower()

    # 检查类别关键词
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in title_lower:
                return category

    return '其他'


def search_standards(keyword: str, page: int = 1, page_size: int = 50) -> Dict:
    """搜索标准"""
    try:
        params = {'keyword': keyword, 'pageNo': page, 'pageSize': page_size}
        resp = httpx.get(
            f'{BASE_URL}/hpyzs/lawsRegulations/quickSearch',
            headers=HEADERS,
            params=params,
            timeout=15
        )
        if resp.status_code == 200:
            return resp.json()
        return {'code': resp.status_code, 'data': {'list': []}}
    except Exception as e:
        print(f"搜索错误: {e}")
        return {'code': 0, 'data': {'list': []}}


def extract_standard_info(item: Dict) -> Dict:
    """从搜索结果提取标准信息"""
    file_type = item.get('fileType', '')
    title = item.get('fileName', '')
    return {
        'title': title,
        'standard_number': item.get('fileNumber', ''),
        'file_type': file_type,
        'category': clean_category(title),
        'industry': clean_industry(file_type, title),
        'source_url': f'{BASE_URL}/hpyzs/lawsRegulations/searchDetail?id={item.get("fileId", "")}',
        'file_id': item.get('fileId', ''),
        'summary': item.get('summarize', ''),
    }


def scrape_all_standards() -> List[Dict]:
    """抓取所有标准"""
    # 关键词列表 - 覆盖更多环境标准
    keywords = [
        # 综合关键词
        '标准', '法规', '规范', '指南', '导则',
        # 污染物类型
        '排放', '污染物', '污染', '废气', '废水', '固废', '危废',
        # 环境要素
        '大气', '空气', '土壤', '噪声', '振动', '辐射', '地下水',
        # 具体污染物
        'COD', '氨氮', '二氧化硫', '氮氧化物', '颗粒物', 'VOCs',
        '汞', '铅', '铬', '砷', '镉', '苯系物',
        # 行业关键词
        '电力', '钢铁', '水泥', '化工', '石油', '制药', '印染',
        '电镀', '造纸', '电解铝', '煤炭', '建材', '垃圾焚烧',
        # 管理关键词
        '监测', '评价', '环评', '许可', '台账', '报告',
        # 更多环境标准关键词
        '环境质量', '污染物', '排放标准', '排放标准',
        '污水综合', '大气污染物', '噪声排放标准',
        '危险废物', '一般工业', '生活垃圾',
    ]

    all_standards = []
    seen_ids = set()

    for keyword in keywords:
        print(f"搜索关键词: {keyword}")
        page = 1
        page_count = 0
        while page <= 3:  # 最多抓取3页
            result = search_standards(keyword, page=page, page_size=50)
            if result.get('code') != 200:
                print(f"  搜索失败")
                break

            items = result.get('data', {}).get('list', [])
            if not items:
                break

            for item in items:
                file_id = item.get('fileId', '')
                if file_id not in seen_ids:
                    seen_ids.add(file_id)
                    std_info = extract_standard_info(item)
                    std_info['search_keyword'] = keyword
                    all_standards.append(std_info)
                    page_count += 1

            total = result.get('totalRows', 0)
            if page * 50 >= total or len(items) < 50:
                break
            page += 1
            time.sleep(0.3)

        print(f"  本页新增: {page_count} 条")
        time.sleep(0.2)

    print(f"\n共收集 {len(all_standards)} 条标准")
    return all_standards


def get_existing_standards(conn) -> Dict[str, int]:
    """获取已存在的标准"""
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM standards")
    return {row[1]: row[0] for row in cursor.fetchall()}


def fuzzy_match(title: str, existing_titles: List[str]) -> Optional[str]:
    """模糊匹配标题"""
    title_clean = title.strip().lower()
    for etitle in existing_titles:
        etitle_clean = etitle.strip().lower()
        # 完全匹配
        if title_clean == etitle_clean:
            return etitle
        # 包含匹配
        if title_clean in etitle_clean or etitle_clean in title_clean:
            return etitle
        # 去除编号后匹配
        title_no_num = re.sub(r'[\d\-/]+', '', title_clean)
        etitle_no_num = re.sub(r'[\d\-/]+', '', etitle_clean)
        if title_no_num and etitle_no_num and (title_no_num in etitle_no_num or etitle_no_num in title_no_num):
            return etitle
    return None


def update_database(standards: List[Dict]) -> Dict:
    """更新数据库"""
    conn = sqlite3.connect(DB_PATH)
    db = conn.cursor()

    # 获取现有标准
    existing_standards = get_existing_standards(conn)
    existing_titles = list(existing_standards.keys())

    new_count = 0
    update_count = 0
    error_count = 0

    for std in standards:
        try:
            title = std.get('title', '').strip()
            if not title:
                continue

            # 模糊匹配
            matched_title = fuzzy_match(title, existing_titles)
            existing_id = None
            if matched_title:
                existing_id = existing_standards.get(matched_title)

            # 提取字段
            industry = std.get('industry', '通用行业')
            category = std.get('category', '其他')
            source_url = std.get('source_url', '')
            summary = std.get('summary', '')

            if existing_id:
                # 更新现有标准
                db.execute("""
                    UPDATE standards SET
                        industry = COALESCE(?, industry),
                        category = COALESCE(?, category),
                        content = COALESCE(?, content),
                        source_url = COALESCE(?, source_url),
                        updated_at = ?
                    WHERE id = ?
                """, (
                    industry,
                    category,
                    summary if summary else None,
                    source_url if source_url else None,
                    datetime.now(),
                    existing_id,
                ))
                update_count += 1
            else:
                # 插入新标准
                db.execute("""
                    INSERT INTO standards
                    (title, standard_type, industry, category, sub_category,
                     content, source_url, status, publish_date, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    title,
                    '行业标准',
                    industry,
                    category,
                    '',
                    summary,
                    source_url,
                    'active',
                    datetime.now(),
                    datetime.now(),
                    datetime.now(),
                ))
                new_count += 1

        except Exception as e:
            print(f"处理标准错误: {title[:30]}... - {e}")
            error_count += 1

    conn.commit()
    conn.close()

    return {
        'new': new_count,
        'updated': update_count,
        'errors': error_count,
        'total': len(standards)
    }


def print_summary(conn):
    """打印数据库统计"""
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM standards')
    total = c.fetchone()[0]

    c.execute('SELECT industry, COUNT(*) FROM standards GROUP BY industry ORDER BY COUNT(*) DESC LIMIT 15')
    industries = c.fetchall()

    c.execute('SELECT category, COUNT(*) FROM standards GROUP BY category ORDER BY COUNT(*) DESC')
    categories = c.fetchall()

    c.execute('SELECT COUNT(*) FROM standards WHERE source_url IS NOT NULL AND source_url != ""')
    with_url = c.fetchone()[0]

    c.execute('SELECT COUNT(*) FROM standards WHERE content IS NOT NULL AND content != ""')
    with_content = c.fetchone()[0]

    print("\n" + "=" * 60)
    print("数据库统计:")
    print(f"  总标准数: {total}")
    print(f"  有来源URL: {with_url}")
    print(f"  有内容摘要: {with_content}")
    print(f"\n  按行业分布 (Top 15):")
    for ind, count in industries:
        print(f"    {ind}: {count}")
    print(f"\n  按类别分布:")
    for cat, count in categories:
        print(f"    {cat}: {count}")
    print("=" * 60)


def main():
    print("=" * 60)
    print("EIA Cloud 环境标准数据抓取 (最终版)")
    print("=" * 60)

    # 抓取数据
    standards = scrape_all_standards()

    # 去重
    seen_titles = set()
    unique_standards = []
    for std in standards:
        title = std.get('title', '').strip()
        if title and title not in seen_titles:
            seen_titles.add(title)
            unique_standards.append(std)

    print(f"\n去重后: {len(unique_standards)} 条标准")

    # 更新数据库
    if unique_standards:
        result = update_database(unique_standards)
        print("\n" + "=" * 60)
        print("更新结果:")
        print(f"  新增: {result['new']} 条")
        print(f"  更新: {result['updated']} 条")
        print(f"  错误: {result['errors']} 条")
        print(f"  总计: {result['total']} 条")
        print("=" * 60)

        # 打印统计
        conn = sqlite3.connect(DB_PATH)
        print_summary(conn)
        conn.close()
    else:
        print("没有需要更新的标准")


if __name__ == "__main__":
    main()
