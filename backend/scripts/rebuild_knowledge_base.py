# -*- coding: utf-8 -*-
"""
重建知识库 - 从 openstd.samr.gov.cn 爬取大量国家标准
覆盖: 环保(13) / 化工(71) / 医药(11) / 能源(27) / 纺织(59) / 橡胶塑料(83) / 电气(29)
包含: 强制GB + 推荐GB/T
"""
import re
import time
import json
import sqlite3
import requests
from datetime import datetime
from urllib.parse import urljoin

DB_PATH = "env_agent.db"
BASE = "https://openstd.samr.gov.cn"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://openstd.samr.gov.cn/bzgk/std/index",
}

# 使用Session保持cookie
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# ICS分类: (ics_code, p1, category_label)
# p1=1 强制GB, p1=2 推荐GB/T
ICS_CATEGORIES = [
    ("13", "1", "环保"),        # 环保、保健和安全 - 强制
    ("13", "2", "环保"),        # 环保、保健和安全 - 推荐
    ("71", "1", "化工"),        # 化工技术 - 强制
    ("71", "2", "化工"),        # 化工技术 - 推荐
    ("11", "1", "医药"),        # 医药卫生技术 - 强制
    ("11", "2", "医药"),        # 医药卫生技术 - 推荐
    ("27", "1", "能源"),        # 能源和热传导工程 - 强制
    ("27", "2", "能源"),        # 能源和热传导工程 - 推荐
    ("59", "1", "纺织"),        # 纺织和皮革技术 - 强制
    ("59", "2", "纺织"),        # 纺织和皮革技术 - 推荐
    ("83", "1", "橡塑"),        # 橡胶和塑料工业 - 强制
    ("83", "2", "橡塑"),        # 橡胶和塑料工业 - 推荐
    ("29", "2", "电气"),        # 电气工程 - 推荐
]

PAGE_SIZE = 50
SLEEP_BETWEEN_PAGES = 0.5
SLEEP_BETWEEN_CATEGORIES = 3.0
MAX_PAGES_PER_CATEGORY = 0  # 0 = 不限制


def fetch(url, retries=3):
    for i in range(retries):
        try:
            r = SESSION.get(url, timeout=30)
            r.encoding = r.apparent_encoding or "utf-8"
            if r.status_code == 200 and r.text and len(r.text) > 1000:
                return r.text
            else:
                print(f"    [重试 {i+1}] 状态码={r.status_code}, 长度={len(r.text)}")
        except Exception as e:
            print(f"    [重试 {i+1}] {e}")
        time.sleep(2)
    return None


def parse_list_page(html):
    """解析列表页HTML表格，返回标准列表
    表格列: TD[0]=序号 TD[1]=标准号 TD[2]=采标 TD[3]=标准名称 TD[4]=状态 TD[5]=发布日期 TD[6]=实施日期 TD[7]=操作
    """
    items = []
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)

    for row in rows:
        tds = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        if len(tds) < 6:
            continue

        # 清理每个td的HTML标签和空白
        cells = []
        for td in tds:
            clean = re.sub(r'<[^>]+>', '', td).strip()
            clean = re.sub(r'\s+', ' ', clean)
            cells.append(clean)

        # 跳过表头和非数据行
        if not cells[0] or not cells[0].isdigit():
            continue

        std_num = cells[1].strip() if len(cells) > 1 else ""
        title = cells[3].strip() if len(cells) > 3 else ""
        status = cells[4].strip() if len(cells) > 4 else ""
        pub_date = cells[5].strip()[:10] if len(cells) > 5 and cells[5].strip() else ""
        impl_date = cells[6].strip()[:10] if len(cells) > 6 and cells[6].strip() else ""

        # 跳过无效行
        if not std_num or not title:
            continue
        # 确保标准号不是"序号"之类的
        # 支持 GB / GB/T / GBZ / HJ / DB 等格式
        if not re.match(r'^[A-Z]{1,6}(?:/[A-Z])?\s*[\d\.]+', std_num):
            continue

        # 提取 hcno
        hcno = ""
        hcno_m = re.search(r"showInfo\('([0-9A-F]{32})'\)", row)
        if hcno_m:
            hcno = hcno_m.group(1)

        items.append({
            "hcno": hcno,
            "standard_number": std_num,
            "title": title,
            "status": status,
            "publish_date": pub_date,
            "implement_date": impl_date,
        })

    # 后备: 如果表格行解析无结果，尝试 showInfo 方法
    if not items:
        raw = {}
        for m in re.finditer(r"showInfo\('([0-9A-F]{32})'[^>]*>\s*([^<]+)</a>", html, re.DOTALL):
            hcno = m.group(1)
            text = re.sub(r'<[^>]+>', '', m.group(2)).strip()
            if hcno not in raw:
                raw[hcno] = {"hcno": hcno, "texts": []}
            raw[hcno]["texts"].append(text)

        for hcno, data in raw.items():
            texts = data["texts"]
            std_num = ""
            title = ""
            for t in texts:
                if re.match(r'^[A-Z]{1,6}(?:/[A-Z])?\s*[\d\.]+', t):
                    if not std_num:
                        std_num = t
                elif len(t) > 3 and t != "查看详细":
                    if not title:
                        title = t
            if std_num and title:
                items.append({
                    "hcno": hcno,
                    "standard_number": std_num,
                    "title": title,
                    "status": "",
                    "publish_date": "",
                    "implement_date": "",
                })

    return items


def get_total_count(html):
    """从列表页提取总条数"""
    clean = html.replace('&nbsp;', ' ').replace('\xa0', ' ')
    m = re.search(r'共\s*(\d+)\s*条', clean)
    if m:
        return int(m.group(1))
    m = re.search(r'var\s+count\s*=\s*["\']?(\d+)', clean)
    if m:
        return int(m.group(1))
    return 0


def infer_category(title):
    """从标准名称推断环保类别"""
    title = title or ""
    if any(k in title for k in ["大气", "废气", "排放", "烟尘", "粉尘", "尾气", "尾气排放"]):
        if "水" not in title:
            return "废气"
    if any(k in title for k in ["水污染物", "废水", "污水", "排放标准"]):
        if "大气" not in title and "尾气" not in title:
            return "废水"
    if any(k in title for k in ["噪声", "声环境"]):
        return "噪声"
    if any(k in title for k in ["固废", "固体废物", "危险废物"]):
        return "固废"
    if any(k in title for k in ["土壤", "地下水"]):
        return "土壤"
    if any(k in title for k in ["辐射", "放射", "电磁"]):
        return "辐射"
    if any(k in title for k in ["环境空气", "空气质量"]):
        return "大气"
    if any(k in title for k in ["地表水", "地下水质量", "水质量", "水质"]):
        return "水"
    if any(k in title for k in ["生态环境", "环境质量"]):
        return "环境"
    if any(k in title for k in ["危险", "安全", "防护"]):
        return "安全"
    return "综合"


def infer_industry(title):
    """从标准名称推断适用行业"""
    title = title or ""
    industries = [
        (["纺织", "印染", "丝绸", "化纤"], "纺织"),
        (["制药", "医药", "药品", "中药材"], "医药"),
        (["电池", "光伏", "风电", "新能源", "太阳能", "储能"], "新能源"),
        (["钢铁", "冶金", "有色金属", "铝", "铜", "锌", "镁"], "冶金"),
        (["造纸", "纸浆"], "造纸"),
        (["食品", "饮料", "发酵", "酒精", "味精"], "食品"),
        (["化工", "化学", "石油", "化肥", "农药", "涂料", "染料"], "化工"),
        (["水泥", "陶瓷", "玻璃", "建材"], "建材"),
        (["煤炭", "矿山", "采矿"], "矿山"),
        (["皮革", "毛皮"], "皮革"),
        (["电镀", "表面处理"], "电镀"),
        (["汽车", "船舶", "摩托车", "车辆"], "交通运输"),
        (["农业", "畜禽", "养殖", "种植"], "农业"),
        (["医院", "医疗机构"], "医疗"),
        (["城镇", "城市", "生活"], "市政"),
    ]
    for keywords, industry in industries:
        if any(k in title for k in keywords):
            return industry
    return "通用行业"


def infer_standard_type(std_num):
    """从标准编号推断标准类型"""
    if not std_num:
        return "国家标准"
    if "GB/T" in std_num:
        return "推荐性国家标准"
    if "GB" in std_num:
        return "强制性国家标准"
    return "国家标准"


def build_source_url(hcno, std_num):
    """构建标准来源URL"""
    if hcno:
        return f"{BASE}/bzgk/std/newGbInfo?hcno={hcno}"
    # 通过标准号搜索
    clean_num = re.sub(r'\s+', '', std_num or "")
    return f"{BASE}/bzgk/gbj/searchQueryByKey.do?searchKey={clean_num}"


# ==================== 已知环保标准的污染因子限值 ====================
KNOWN_LIMITS = {
    "GB 16297-1996": {
        "factors": [
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "一级", "value": 550, "unit": "mg/m³", "desc": "最高允许排放浓度"},
                {"level": "二级", "value": 960, "unit": "mg/m³", "desc": "最高允许排放浓度"},
            ]},
            {"name": "氮氧化物", "symbol": "NOx", "limits": [
                {"level": "一级", "value": 240, "unit": "mg/m³", "desc": "最高允许排放浓度"},
                {"level": "二级", "value": 1100, "unit": "mg/m³", "desc": "最高允许排放浓度"},
            ]},
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "一级", "value": 120, "unit": "mg/m³", "desc": "最高允许排放浓度"},
                {"level": "二级", "value": 250, "unit": "mg/m³", "desc": "最高允许排放浓度"},
            ]},
            {"name": "氟化物", "symbol": "F", "limits": [
                {"level": "一级", "value": 9, "unit": "mg/m³", "desc": "最高允许排放浓度"},
                {"level": "二级", "value": 20, "unit": "mg/m³", "desc": "最高允许排放浓度"},
            ]},
            {"name": "氯化氢", "symbol": "HCl", "limits": [
                {"level": "一级", "value": 100, "unit": "mg/m³", "desc": "最高允许排放浓度"},
                {"level": "二级", "value": 250, "unit": "mg/m³", "desc": "最高允许排放浓度"},
            ]},
            {"name": "硫酸雾", "symbol": "H2SO4", "limits": [
                {"level": "一级", "value": 45, "unit": "mg/m³", "desc": "最高允许排放浓度"},
                {"level": "二级", "value": 160, "unit": "mg/m³", "desc": "最高允许排放浓度"},
            ]},
            {"name": "铅及其化合物", "symbol": "Pb", "limits": [
                {"level": "一级", "value": 0.9, "unit": "mg/m³", "desc": "最高允许排放浓度"},
                {"level": "二级", "value": 5.0, "unit": "mg/m³", "desc": "最高允许排放浓度"},
            ]},
            {"name": "汞及其化合物", "symbol": "Hg", "limits": [
                {"level": "一级", "value": 0.015, "unit": "mg/m³", "desc": "最高允许排放浓度"},
                {"level": "二级", "value": 0.030, "unit": "mg/m³", "desc": "最高允许排放浓度"},
            ]},
            {"name": "苯", "symbol": "C6H6", "limits": [
                {"level": "一级", "value": 12, "unit": "mg/m³", "desc": "最高允许排放浓度"},
                {"level": "二级", "value": 40, "unit": "mg/m³", "desc": "最高允许排放浓度"},
            ]},
            {"name": "甲醛", "symbol": "HCHO", "limits": [
                {"level": "一级", "value": 5.0, "unit": "mg/m³", "desc": "最高允许排放浓度"},
                {"level": "二级", "value": 25, "unit": "mg/m³", "desc": "最高允许排放浓度"},
            ]},
        ]
    },
    "GB 8978-1996": {
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "一级", "value": 100, "unit": "mg/L", "desc": "最高允许排放浓度"},
                {"level": "二级", "value": 150, "unit": "mg/L", "desc": "最高允许排放浓度"},
                {"level": "三级", "value": 500, "unit": "mg/L", "desc": "最高允许排放浓度"},
            ]},
            {"name": "生化需氧量", "symbol": "BOD5", "limits": [
                {"level": "一级", "value": 30, "unit": "mg/L", "desc": "最高允许排放浓度"},
                {"level": "二级", "value": 60, "unit": "mg/L", "desc": "最高允许排放浓度"},
                {"level": "三级", "value": 300, "unit": "mg/L", "desc": "最高允许排放浓度"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "一级", "value": 70, "unit": "mg/L", "desc": "最高允许排放浓度"},
                {"level": "二级", "value": 200, "unit": "mg/L", "desc": "最高允许排放浓度"},
                {"level": "三级", "value": 400, "unit": "mg/L", "desc": "最高允许排放浓度"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "一级", "value": 15, "unit": "mg/L", "desc": "最高允许排放浓度"},
                {"level": "二级", "value": 25, "unit": "mg/L", "desc": "最高允许排放浓度"},
            ]},
            {"name": "总磷", "symbol": "TP", "limits": [
                {"level": "一级", "value": 0.5, "unit": "mg/L", "desc": "最高允许排放浓度"},
                {"level": "二级", "value": 1.0, "unit": "mg/L", "desc": "最高允许排放浓度"},
            ]},
            {"name": "石油类", "symbol": "Petroleum", "limits": [
                {"level": "一级", "value": 5, "unit": "mg/L", "desc": "最高允许排放浓度"},
                {"level": "二级", "value": 10, "unit": "mg/L", "desc": "最高允许排放浓度"},
            ]},
            {"name": "总汞", "symbol": "Hg", "limits": [
                {"level": "一级", "value": 0.05, "unit": "mg/L", "desc": "最高允许排放浓度"},
                {"level": "二级", "value": 0.05, "unit": "mg/L", "desc": "最高允许排放浓度"},
            ]},
            {"name": "总镉", "symbol": "Cd", "limits": [
                {"level": "一级", "value": 0.1, "unit": "mg/L", "desc": "最高允许排放浓度"},
                {"level": "二级", "value": 0.1, "unit": "mg/L", "desc": "最高允许排放浓度"},
            ]},
            {"name": "总铬", "symbol": "Cr", "limits": [
                {"level": "一级", "value": 1.5, "unit": "mg/L", "desc": "最高允许排放浓度"},
                {"level": "二级", "value": 1.5, "unit": "mg/L", "desc": "最高允许排放浓度"},
            ]},
            {"name": "六价铬", "symbol": "Cr6+", "limits": [
                {"level": "一级", "value": 0.5, "unit": "mg/L", "desc": "最高允许排放浓度"},
                {"level": "二级", "value": 0.5, "unit": "mg/L", "desc": "最高允许排放浓度"},
            ]},
            {"name": "总铅", "symbol": "Pb", "limits": [
                {"level": "一级", "value": 1.0, "unit": "mg/L", "desc": "最高允许排放浓度"},
                {"level": "二级", "value": 1.0, "unit": "mg/L", "desc": "最高允许排放浓度"},
            ]},
            {"name": "挥发酚", "symbol": "VolatilePhenol", "limits": [
                {"level": "一级", "value": 0.5, "unit": "mg/L", "desc": "最高允许排放浓度"},
                {"level": "二级", "value": 0.5, "unit": "mg/L", "desc": "最高允许排放浓度"},
            ]},
        ]
    },
    "GB 3095-2026": {
        "factors": [
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "一级", "value": 0.05, "unit": "mg/m³", "desc": "年平均"},
                {"level": "二级", "value": 0.15, "unit": "mg/m³", "desc": "年平均"},
            ]},
            {"name": "PM2.5", "symbol": "PM2.5", "limits": [
                {"level": "一级", "value": 0.015, "unit": "mg/m³", "desc": "年平均"},
                {"level": "二级", "value": 0.035, "unit": "mg/m³", "desc": "年平均"},
            ]},
            {"name": "PM10", "symbol": "PM10", "limits": [
                {"level": "一级", "value": 0.04, "unit": "mg/m³", "desc": "年平均"},
                {"level": "二级", "value": 0.07, "unit": "mg/m³", "desc": "年平均"},
            ]},
            {"name": "氮氧化物", "symbol": "NOx", "limits": [
                {"level": "一级", "value": 0.05, "unit": "mg/m³", "desc": "年平均"},
                {"level": "二级", "value": 0.05, "unit": "mg/m³", "desc": "年平均"},
            ]},
            {"name": "臭氧", "symbol": "O3", "limits": [
                {"level": "一级", "value": 0.16, "unit": "mg/m³", "desc": "日最大8小时平均"},
                {"level": "二级", "value": 0.16, "unit": "mg/m³", "desc": "日最大8小时平均"},
            ]},
            {"name": "一氧化碳", "symbol": "CO", "limits": [
                {"level": "一级", "value": 4, "unit": "mg/m³", "desc": "24小时平均"},
                {"level": "二级", "value": 4, "unit": "mg/m³", "desc": "24小时平均"},
            ]},
        ]
    },
    "GB 3838-2002": {
        "factors": [
            {"name": "pH值", "symbol": "pH", "limits": [
                {"level": "I类", "value": 6, "unit": "-", "desc": "6-9"},
                {"level": "V类", "value": 9, "unit": "-", "desc": "6-9"},
            ]},
            {"name": "溶解氧", "symbol": "DO", "limits": [
                {"level": "I类", "value": 7.5, "unit": "mg/L", "desc": "饱和率≥90%"},
                {"level": "V类", "value": 2.0, "unit": "mg/L", "desc": "≥2.0"},
            ]},
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "I类", "value": 15, "unit": "mg/L", "desc": "≤15"},
                {"level": "V类", "value": 40, "unit": "mg/L", "desc": "≤40"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "I类", "value": 0.15, "unit": "mg/L", "desc": "≤0.15"},
                {"level": "V类", "value": 2.0, "unit": "mg/L", "desc": "≤2.0"},
            ]},
            {"name": "总磷", "symbol": "TP", "limits": [
                {"level": "I类", "value": 0.02, "unit": "mg/L", "desc": "≤0.02(湖库)"},
                {"level": "V类", "value": 0.4, "unit": "mg/L", "desc": "≤0.4(湖库)"},
            ]},
            {"name": "总氮", "symbol": "TN", "limits": [
                {"level": "I类", "value": 0.2, "unit": "mg/L", "desc": "≤0.2(湖库)"},
                {"level": "V类", "value": 2.0, "unit": "mg/L", "desc": "≤2.0(湖库)"},
            ]},
        ]
    },
    "GB 12348-2008": {
        "factors": [
            {"name": "厂界噪声", "symbol": "Noise", "limits": [
                {"level": "1类", "value": 55, "unit": "dB(A)", "desc": "昼间"},
                {"level": "1类", "value": 45, "unit": "dB(A)", "desc": "夜间"},
                {"level": "2类", "value": 60, "unit": "dB(A)", "desc": "昼间"},
                {"level": "2类", "value": 50, "unit": "dB(A)", "desc": "夜间"},
                {"level": "3类", "value": 65, "unit": "dB(A)", "desc": "昼间"},
                {"level": "3类", "value": 55, "unit": "dB(A)", "desc": "夜间"},
                {"level": "4类", "value": 70, "unit": "dB(A)", "desc": "昼间"},
                {"level": "4类", "value": 55, "unit": "dB(A)", "desc": "夜间"},
            ]},
        ]
    },
    "GB 12523-2011": {
        "factors": [
            {"name": "施工噪声", "symbol": "Noise", "limits": [
                {"level": "昼间", "value": 70, "unit": "dB(A)", "desc": "建筑施工场界"},
                {"level": "夜间", "value": 55, "unit": "dB(A)", "desc": "建筑施工场界"},
            ]},
        ]
    },
    "GB 31570-2015": {
        "factors": [
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "特别排放限值", "value": 50, "unit": "mg/m³", "desc": "石油炼制"},
                {"level": "现有", "value": 100, "unit": "mg/m³", "desc": "石油炼制"},
                {"level": "新建", "value": 50, "unit": "mg/m³", "desc": "石油炼制"},
            ]},
            {"name": "氮氧化物", "symbol": "NOx", "limits": [
                {"level": "特别排放限值", "value": 100, "unit": "mg/m³", "desc": "石油炼制"},
                {"level": "现有", "value": 200, "unit": "mg/m³", "desc": "石油炼制"},
                {"level": "新建", "value": 100, "unit": "mg/m³", "desc": "石油炼制"},
            ]},
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "特别排放限值", "value": 10, "unit": "mg/m³", "desc": "石油炼制"},
                {"level": "现有", "value": 30, "unit": "mg/m³", "desc": "石油炼制"},
                {"level": "新建", "value": 20, "unit": "mg/m³", "desc": "石油炼制"},
            ]},
            {"name": "VOCs", "symbol": "VOCs", "limits": [
                {"level": "特别排放限值", "value": 50, "unit": "mg/m³", "desc": "石油炼制"},
                {"level": "现有", "value": 120, "unit": "mg/m³", "desc": "石油炼制"},
                {"level": "新建", "value": 70, "unit": "mg/m³", "desc": "石油炼制"},
            ]},
        ]
    },
    "GB 31571-2015": {
        "factors": [
            {"name": "VOCs", "symbol": "VOCs", "limits": [
                {"level": "特别排放限值", "value": 50, "unit": "mg/m³", "desc": "石油化学工业"},
                {"level": "现有", "value": 120, "unit": "mg/m³", "desc": "石油化学工业"},
                {"level": "新建", "value": 60, "unit": "mg/m³", "desc": "石油化学工业"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "特别排放限值", "value": 50, "unit": "mg/m³", "desc": "石油化学工业"},
                {"level": "新建", "value": 50, "unit": "mg/m³", "desc": "石油化学工业"},
            ]},
            {"name": "氮氧化物", "symbol": "NOx", "limits": [
                {"level": "特别排放限值", "value": 100, "unit": "mg/m³", "desc": "石油化学工业"},
                {"level": "新建", "value": 100, "unit": "mg/m³", "desc": "石油化学工业"},
            ]},
        ]
    },
    "GB 31572-2015": {
        "factors": [
            {"name": "VOCs", "symbol": "VOCs", "limits": [
                {"level": "特别排放限值", "value": 40, "unit": "mg/m³", "desc": "合成树脂工业"},
                {"level": "现有", "value": 100, "unit": "mg/m³", "desc": "合成树脂工业"},
                {"level": "新建", "value": 60, "unit": "mg/m³", "desc": "合成树脂工业"},
            ]},
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "特别排放限值", "value": 10, "unit": "mg/m³", "desc": "合成树脂工业"},
                {"level": "新建", "value": 20, "unit": "mg/m³", "desc": "合成树脂工业"},
            ]},
        ]
    },
    "GB 4287-2026": {
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 80, "unit": "mg/L", "desc": "纺织工业"},
                {"level": "间接排放", "value": 200, "unit": "mg/L", "desc": "纺织工业"},
            ]},
            {"name": "生化需氧量", "symbol": "BOD5", "limits": [
                {"level": "直接排放", "value": 20, "unit": "mg/L", "desc": "纺织工业"},
                {"level": "间接排放", "value": 50, "unit": "mg/L", "desc": "纺织工业"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "直接排放", "value": 50, "unit": "mg/L", "desc": "纺织工业"},
                {"level": "间接排放", "value": 100, "unit": "mg/L", "desc": "纺织工业"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "直接排放", "value": 10, "unit": "mg/L", "desc": "纺织工业"},
                {"level": "间接排放", "value": 20, "unit": "mg/L", "desc": "纺织工业"},
            ]},
        ]
    },
    "GB 13223-2011": {
        "factors": [
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "现有", "value": 200, "unit": "mg/m³", "desc": "火电厂"},
                {"level": "新建", "value": 100, "unit": "mg/m³", "desc": "火电厂"},
                {"level": "特别排放限值", "value": 50, "unit": "mg/m³", "desc": "火电厂"},
            ]},
            {"name": "氮氧化物", "symbol": "NOx", "limits": [
                {"level": "现有", "value": 100, "unit": "mg/m³", "desc": "火电厂"},
                {"level": "新建", "value": 100, "unit": "mg/m³", "desc": "火电厂"},
                {"level": "特别排放限值", "value": 50, "unit": "mg/m³", "desc": "火电厂"},
            ]},
            {"name": "烟尘", "symbol": "PM", "limits": [
                {"level": "现有", "value": 30, "unit": "mg/m³", "desc": "火电厂"},
                {"level": "新建", "value": 30, "unit": "mg/m³", "desc": "火电厂"},
                {"level": "特别排放限值", "value": 20, "unit": "mg/m³", "desc": "火电厂"},
            ]},
            {"name": "汞及其化合物", "symbol": "Hg", "limits": [
                {"level": "通用", "value": 0.03, "unit": "mg/m³", "desc": "火电厂"},
            ]},
        ]
    },
    "GB 4915-2013": {
        "factors": [
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 30, "unit": "mg/m³", "desc": "水泥工业"},
                {"level": "新建", "value": 20, "unit": "mg/m³", "desc": "水泥工业"},
                {"level": "特别排放限值", "value": 10, "unit": "mg/m³", "desc": "水泥工业"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "现有", "value": 200, "unit": "mg/m³", "desc": "水泥工业"},
                {"level": "新建", "value": 100, "unit": "mg/m³", "desc": "水泥工业"},
                {"level": "特别排放限值", "value": 50, "unit": "mg/m³", "desc": "水泥工业"},
            ]},
            {"name": "氮氧化物", "symbol": "NOx", "limits": [
                {"level": "现有", "value": 400, "unit": "mg/m³", "desc": "水泥工业"},
                {"level": "新建", "value": 320, "unit": "mg/m³", "desc": "水泥工业"},
                {"level": "特别排放限值", "value": 150, "unit": "mg/m³", "desc": "水泥工业"},
            ]},
        ]
    },
    "GB 16171-2012": {
        "factors": [
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 50, "unit": "mg/m³", "desc": "炼焦化学工业"},
                {"level": "新建", "value": 30, "unit": "mg/m³", "desc": "炼焦化学工业"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "现有", "value": 100, "unit": "mg/m³", "desc": "炼焦化学工业"},
                {"level": "新建", "value": 50, "unit": "mg/m³", "desc": "炼焦化学工业"},
            ]},
            {"name": "氮氧化物", "symbol": "NOx", "limits": [
                {"level": "现有", "value": 500, "unit": "mg/m³", "desc": "炼焦化学工业"},
                {"level": "新建", "value": 500, "unit": "mg/m³", "desc": "炼焦化学工业"},
            ]},
            {"name": "苯并[a]芘", "symbol": "BaP", "limits": [
                {"level": "通用", "value": 0.3, "unit": "μg/m³", "desc": "炼焦化学工业"},
            ]},
        ]
    },
    "GB 18484-2001": {
        "factors": [
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "现有", "value": 400, "unit": "mg/m³", "desc": "危险废物焚烧"},
                {"level": "新建", "value": 300, "unit": "mg/m³", "desc": "危险废物焚烧"},
            ]},
            {"name": "氮氧化物", "symbol": "NOx", "limits": [
                {"level": "现有", "value": 500, "unit": "mg/m³", "desc": "危险废物焚烧"},
                {"level": "新建", "value": 500, "unit": "mg/m³", "desc": "危险废物焚烧"},
            ]},
            {"name": "一氧化碳", "symbol": "CO", "limits": [
                {"level": "现有", "value": 100, "unit": "mg/m³", "desc": "危险废物焚烧"},
                {"level": "新建", "value": 80, "unit": "mg/m³", "desc": "危险废物焚烧"},
            ]},
            {"name": "氯化氢", "symbol": "HCl", "limits": [
                {"level": "现有", "value": 100, "unit": "mg/m³", "desc": "危险废物焚烧"},
                {"level": "新建", "value": 60, "unit": "mg/m³", "desc": "危险废物焚烧"},
            ]},
        ]
    },
    "GB 18485-2014": {
        "factors": [
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "1小时均值", "value": 100, "unit": "mg/m³", "desc": "生活垃圾焚烧"},
                {"level": "24小时均值", "value": 80, "unit": "mg/m³", "desc": "生活垃圾焚烧"},
            ]},
            {"name": "氮氧化物", "symbol": "NOx", "limits": [
                {"level": "1小时均值", "value": 300, "unit": "mg/m³", "desc": "生活垃圾焚烧"},
                {"level": "24小时均值", "value": 250, "unit": "mg/m³", "desc": "生活垃圾焚烧"},
            ]},
            {"name": "氯化氢", "symbol": "HCl", "limits": [
                {"level": "1小时均值", "value": 60, "unit": "mg/m³", "desc": "生活垃圾焚烧"},
                {"level": "24小时均值", "value": 50, "unit": "mg/m³", "desc": "生活垃圾焚烧"},
            ]},
            {"name": "汞及其化合物", "symbol": "Hg", "limits": [
                {"level": "测定均值", "value": 0.05, "unit": "mg/m³", "desc": "生活垃圾焚烧"},
            ]},
            {"name": "二噁英类", "symbol": "PCDDs", "limits": [
                {"level": "测定均值", "value": 0.1, "unit": "ng-TEQ/m³", "desc": "生活垃圾焚烧"},
            ]},
        ]
    },
    "GB 14554-1993": {
        "factors": [
            {"name": "氨", "symbol": "NH3", "limits": [
                {"level": "排气筒", "value": 4.9, "unit": "kg/h", "desc": "恶臭污染物"},
            ]},
            {"name": "硫化氢", "symbol": "H2S", "limits": [
                {"level": "排气筒", "value": 0.33, "unit": "kg/h", "desc": "恶臭污染物"},
            ]},
            {"name": "甲硫醇", "symbol": "CH3SH", "limits": [
                {"level": "排气筒", "value": 0.04, "unit": "kg/h", "desc": "恶臭污染物"},
            ]},
            {"name": "臭气浓度", "symbol": "Odor", "limits": [
                {"level": "排气筒", "value": 2000, "unit": "无量纲", "desc": "恶臭污染物"},
            ]},
        ]
    },
    "GB 21900-2008": {
        "factors": [
            {"name": "总铬", "symbol": "Cr", "limits": [
                {"level": "现有", "value": 1.0, "unit": "mg/L", "desc": "电镀工业"},
                {"level": "新建", "value": 0.5, "unit": "mg/L", "desc": "电镀工业"},
            ]},
            {"name": "六价铬", "symbol": "Cr6+", "limits": [
                {"level": "现有", "value": 0.5, "unit": "mg/L", "desc": "电镀工业"},
                {"level": "新建", "value": 0.2, "unit": "mg/L", "desc": "电镀工业"},
            ]},
            {"name": "总镍", "symbol": "Ni", "limits": [
                {"level": "现有", "value": 0.5, "unit": "mg/L", "desc": "电镀工业"},
                {"level": "新建", "value": 0.1, "unit": "mg/L", "desc": "电镀工业"},
            ]},
            {"name": "总镉", "symbol": "Cd", "limits": [
                {"level": "现有", "value": 0.05, "unit": "mg/L", "desc": "电镀工业"},
                {"level": "新建", "value": 0.01, "unit": "mg/L", "desc": "电镀工业"},
            ]},
            {"name": "总银", "symbol": "Ag", "limits": [
                {"level": "现有", "value": 0.3, "unit": "mg/L", "desc": "电镀工业"},
                {"level": "新建", "value": 0.1, "unit": "mg/L", "desc": "电镀工业"},
            ]},
        ]
    },
    "GB 21902-2008": {
        "factors": [
            {"name": "VOCs", "symbol": "VOCs", "limits": [
                {"level": "现有", "value": 200, "unit": "mg/m³", "desc": "合成革与人造革工业"},
                {"level": "新建", "value": 100, "unit": "mg/m³", "desc": "合成革与人造革工业"},
            ]},
            {"name": "甲苯", "symbol": "C7H8", "limits": [
                {"level": "现有", "value": 40, "unit": "mg/m³", "desc": "合成革与人造革工业"},
                {"level": "新建", "value": 30, "unit": "mg/m³", "desc": "合成革与人造革工业"},
            ]},
            {"name": "二甲苯", "symbol": "C8H10", "limits": [
                {"level": "现有", "value": 40, "unit": "mg/m³", "desc": "合成革与人造革工业"},
                {"level": "新建", "value": 30, "unit": "mg/m³", "desc": "合成革与人造革工业"},
            ]},
        ]
    },
    "GB 21903-2008": {
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "现有", "value": 120, "unit": "mg/L", "desc": "发酵类制药工业"},
                {"level": "新建", "value": 80, "unit": "mg/L", "desc": "发酵类制药工业"},
            ]},
            {"name": "生化需氧量", "symbol": "BOD5", "limits": [
                {"level": "现有", "value": 40, "unit": "mg/L", "desc": "发酵类制药工业"},
                {"level": "新建", "value": 20, "unit": "mg/L", "desc": "发酵类制药工业"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "现有", "value": 35, "unit": "mg/L", "desc": "发酵类制药工业"},
                {"level": "新建", "value": 15, "unit": "mg/L", "desc": "发酵类制药工业"},
            ]},
            {"name": "总氮", "symbol": "TN", "limits": [
                {"level": "现有", "value": 70, "unit": "mg/L", "desc": "发酵类制药工业"},
                {"level": "新建", "value": 30, "unit": "mg/L", "desc": "发酵类制药工业"},
            ]},
        ]
    },
    "GB 21904-2008": {
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "现有", "value": 120, "unit": "mg/L", "desc": "化学合成类制药工业"},
                {"level": "新建", "value": 80, "unit": "mg/L", "desc": "化学合成类制药工业"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "现有", "value": 30, "unit": "mg/L", "desc": "化学合成类制药工业"},
                {"level": "新建", "value": 15, "unit": "mg/L", "desc": "化学合成类制药工业"},
            ]},
            {"name": "总氮", "symbol": "TN", "limits": [
                {"level": "现有", "value": 50, "unit": "mg/L", "desc": "化学合成类制药工业"},
                {"level": "新建", "value": 25, "unit": "mg/L", "desc": "化学合成类制药工业"},
            ]},
            {"name": "总磷", "symbol": "TP", "limits": [
                {"level": "现有", "value": 1.0, "unit": "mg/L", "desc": "化学合成类制药工业"},
                {"level": "新建", "value": 0.5, "unit": "mg/L", "desc": "化学合成类制药工业"},
            ]},
        ]
    },
    "GB 13456-2012": {
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 50, "unit": "mg/L", "desc": "钢铁工业"},
                {"level": "间接排放", "value": 200, "unit": "mg/L", "desc": "钢铁工业"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "直接排放", "value": 20, "unit": "mg/L", "desc": "钢铁工业"},
                {"level": "间接排放", "value": 100, "unit": "mg/L", "desc": "钢铁工业"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "直接排放", "value": 5, "unit": "mg/L", "desc": "钢铁工业"},
                {"level": "间接排放", "value": 15, "unit": "mg/L", "desc": "钢铁工业"},
            ]},
            {"name": "总氮", "symbol": "TN", "limits": [
                {"level": "直接排放", "value": 15, "unit": "mg/L", "desc": "钢铁工业"},
                {"level": "间接排放", "value": 40, "unit": "mg/L", "desc": "钢铁工业"},
            ]},
            {"name": "石油类", "symbol": "Petroleum", "limits": [
                {"level": "直接排放", "value": 3, "unit": "mg/L", "desc": "钢铁工业"},
                {"level": "间接排放", "value": 10, "unit": "mg/L", "desc": "钢铁工业"},
            ]},
        ]
    },
    "GB 3544-2008": {
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "现有", "value": 100, "unit": "mg/L", "desc": "制浆造纸工业"},
                {"level": "新建", "value": 80, "unit": "mg/L", "desc": "制浆造纸工业"},
            ]},
            {"name": "生化需氧量", "symbol": "BOD5", "limits": [
                {"level": "现有", "value": 30, "unit": "mg/L", "desc": "制浆造纸工业"},
                {"level": "新建", "value": 20, "unit": "mg/L", "desc": "制浆造纸工业"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "现有", "value": 50, "unit": "mg/L", "desc": "制浆造纸工业"},
                {"level": "新建", "value": 30, "unit": "mg/L", "desc": "制浆造纸工业"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "现有", "value": 10, "unit": "mg/L", "desc": "制浆造纸工业"},
                {"level": "新建", "value": 5, "unit": "mg/L", "desc": "制浆造纸工业"},
            ]},
            {"name": "总氮", "symbol": "TN", "limits": [
                {"level": "现有", "value": 15, "unit": "mg/L", "desc": "制浆造纸工业"},
                {"level": "新建", "value": 10, "unit": "mg/L", "desc": "制浆造纸工业"},
            ]},
        ]
    },
    "GB 25467-2010": {
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "现有", "value": 80, "unit": "mg/L", "desc": "铜镍钴工业"},
                {"level": "新建", "value": 50, "unit": "mg/L", "desc": "铜镍钴工业"},
            ]},
            {"name": "总铜", "symbol": "Cu", "limits": [
                {"level": "现有", "value": 1.0, "unit": "mg/L", "desc": "铜镍钴工业"},
                {"level": "新建", "value": 0.5, "unit": "mg/L", "desc": "铜镍钴工业"},
            ]},
            {"name": "总镍", "symbol": "Ni", "limits": [
                {"level": "现有", "value": 1.0, "unit": "mg/L", "desc": "铜镍钴工业"},
                {"level": "新建", "value": 0.5, "unit": "mg/L", "desc": "铜镍钴工业"},
            ]},
            {"name": "总钴", "symbol": "Co", "limits": [
                {"level": "现有", "value": 1.0, "unit": "mg/L", "desc": "铜镍钴工业"},
                {"level": "新建", "value": 1.0, "unit": "mg/L", "desc": "铜镍钴工业"},
            ]},
        ]
    },
    "GB 25466-2010": {
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "现有", "value": 80, "unit": "mg/L", "desc": "铅锌工业"},
                {"level": "新建", "value": 50, "unit": "mg/L", "desc": "铅锌工业"},
            ]},
            {"name": "总铅", "symbol": "Pb", "limits": [
                {"level": "现有", "value": 1.0, "unit": "mg/L", "desc": "铅锌工业"},
                {"level": "新建", "value": 0.5, "unit": "mg/L", "desc": "铅锌工业"},
            ]},
            {"name": "总锌", "symbol": "Zn", "limits": [
                {"level": "现有", "value": 2.0, "unit": "mg/L", "desc": "铅锌工业"},
                {"level": "新建", "value": 1.0, "unit": "mg/L", "desc": "铅锌工业"},
            ]},
            {"name": "总镉", "symbol": "Cd", "limits": [
                {"level": "现有", "value": 0.1, "unit": "mg/L", "desc": "铅锌工业"},
                {"level": "新建", "value": 0.05, "unit": "mg/L", "desc": "铅锌工业"},
            ]},
        ]
    },
    "GB 26451-2011": {
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "现有", "value": 80, "unit": "mg/L", "desc": "稀土工业"},
                {"level": "新建", "value": 60, "unit": "mg/L", "desc": "稀土工业"},
            ]},
            {"name": "总氮", "symbol": "TN", "limits": [
                {"level": "现有", "value": 20, "unit": "mg/L", "desc": "稀土工业"},
                {"level": "新建", "value": 15, "unit": "mg/L", "desc": "稀土工业"},
            ]},
            {"name": "总磷", "symbol": "TP", "limits": [
                {"level": "现有", "value": 5, "unit": "mg/L", "desc": "稀土工业"},
                {"level": "新建", "value": 3, "unit": "mg/L", "desc": "稀土工业"},
            ]},
            {"name": "总稀土", "symbol": "RE", "limits": [
                {"level": "现有", "value": 5, "unit": "mg/L", "desc": "稀土工业"},
                {"level": "新建", "value": 2, "unit": "mg/L", "desc": "稀土工业"},
            ]},
        ]
    },
    "GB 4274-2008": {
        "factors": [
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "现有", "value": 860, "unit": "mg/m³", "desc": "硫酸工业"},
                {"level": "新建", "value": 400, "unit": "mg/m³", "desc": "硫酸工业"},
            ]},
            {"name": "硫酸雾", "symbol": "H2SO4", "limits": [
                {"level": "现有", "value": 45, "unit": "mg/m³", "desc": "硫酸工业"},
                {"level": "新建", "value": 30, "unit": "mg/m³", "desc": "硫酸工业"},
            ]},
        ]
    },
    "GB 4277-2008": {
        "factors": [
            {"name": "氮氧化物", "symbol": "NOx", "limits": [
                {"level": "现有", "value": 800, "unit": "mg/m³", "desc": "硝酸工业"},
                {"level": "新建", "value": 300, "unit": "mg/m³", "desc": "硝酸工业"},
            ]},
            {"name": "硝酸雾", "symbol": "HNO3", "limits": [
                {"level": "现有", "value": 80, "unit": "mg/m³", "desc": "硝酸工业"},
                {"level": "新建", "value": 50, "unit": "mg/m³", "desc": "硝酸工业"},
            ]},
        ]
    },
    "GB 36600-2018": {
        "factors": [
            {"name": "铅", "symbol": "Pb", "limits": [
                {"level": "第一类用地", "value": 400, "unit": "mg/kg", "desc": "土壤污染风险筛选值"},
                {"level": "第二类用地", "value": 800, "unit": "mg/kg", "desc": "土壤污染风险筛选值"},
            ]},
            {"name": "镉", "symbol": "Cd", "limits": [
                {"level": "第一类用地", "value": 20, "unit": "mg/kg", "desc": "土壤污染风险筛选值"},
                {"level": "第二类用地", "value": 65, "unit": "mg/kg", "desc": "土壤污染风险筛选值"},
            ]},
            {"name": "砷", "symbol": "As", "limits": [
                {"level": "第一类用地", "value": 20, "unit": "mg/kg", "desc": "土壤污染风险筛选值"},
                {"level": "第二类用地", "value": 60, "unit": "mg/kg", "desc": "土壤污染风险筛选值"},
            ]},
            {"name": "汞", "symbol": "Hg", "limits": [
                {"level": "第一类用地", "value": 8, "unit": "mg/kg", "desc": "土壤污染风险筛选值"},
                {"level": "第二类用地", "value": 38, "unit": "mg/kg", "desc": "土壤污染风险筛选值"},
            ]},
            {"name": "苯", "symbol": "C6H6", "limits": [
                {"level": "第一类用地", "value": 1, "unit": "mg/kg", "desc": "土壤污染风险筛选值"},
                {"level": "第二类用地", "value": 4, "unit": "mg/kg", "desc": "土壤污染风险筛选值"},
            ]},
        ]
    },
    "GB 3096-2008": {
        "factors": [
            {"name": "环境噪声", "symbol": "Noise", "limits": [
                {"level": "0类", "value": 50, "unit": "dB(A)", "desc": "昼间"},
                {"level": "0类", "value": 40, "unit": "dB(A)", "desc": "夜间"},
                {"level": "1类", "value": 55, "unit": "dB(A)", "desc": "昼间"},
                {"level": "1类", "value": 45, "unit": "dB(A)", "desc": "夜间"},
                {"level": "2类", "value": 60, "unit": "dB(A)", "desc": "昼间"},
                {"level": "2类", "value": 50, "unit": "dB(A)", "desc": "夜间"},
                {"level": "3类", "value": 65, "unit": "dB(A)", "desc": "昼间"},
                {"level": "3类", "value": 55, "unit": "dB(A)", "desc": "夜间"},
                {"level": "4类", "value": 70, "unit": "dB(A)", "desc": "昼间"},
                {"level": "4类", "value": 55, "unit": "dB(A)", "desc": "夜间"},
            ]},
        ]
    },
    "GB 18599-2020": {
        "factors": [
            {"name": "浸出液化学需氧量", "symbol": "COD", "limits": [
                {"level": "I类", "value": 70, "unit": "mg/L", "desc": "一般工业固废浸出液"},
                {"level": "II类", "value": 200, "unit": "mg/L", "desc": "一般工业固废浸出液"},
            ]},
            {"name": "浸出液总磷", "symbol": "TP", "limits": [
                {"level": "I类", "value": 0.5, "unit": "mg/L", "desc": "一般工业固废浸出液"},
                {"level": "II类", "value": 3, "unit": "mg/L", "desc": "一般工业固废浸出液"},
            ]},
        ]
    },
}


def clean_database():
    """清空标准相关表"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    # 清空标准、污染因子、污染限值表
    c.execute("DELETE FROM standards")
    c.execute("DELETE FROM pollution_factors")
    c.execute("DELETE FROM pollution_limits")
    # 重置自增ID (如果表存在)
    try:
        c.execute("DELETE FROM sqlite_sequence WHERE name IN ('standards', 'pollution_factors', 'pollution_limits')")
    except:
        pass
    conn.commit()
    conn.close()
    print("已清空 standards, pollution_factors, pollution_limits 表")


def save_to_db(all_standards):
    """保存标准到数据库"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()

    inserted = 0
    factor_cache = {}  # symbol -> factor_id

    for std in all_standards:
        title = std.get("title", "").strip()
        std_num = std.get("standard_number", "").strip()
        if not title or not std_num:
            continue

        category = std.get("category", infer_category(title))
        industry = std.get("industry", infer_industry(title))
        std_type = std.get("standard_type", infer_standard_type(std_num))
        status = "active" if std.get("status", "") != "废止" else "obsolete"
        pub_date = std.get("publish_date", "")
        impl_date = std.get("implement_date", "")
        hcno = std.get("hcno", "")
        source_url = build_source_url(hcno, std_num)

        # 检查已知限值
        pollution_factors = []
        known = KNOWN_LIMITS.get(std_num)
        if known:
            for f in known["factors"]:
                pollution_factors.append({
                    "name": f["name"],
                    "symbol": f["symbol"],
                    "limits": f["limits"],
                })

        # 插入标准
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""
            INSERT INTO standards
                (title, standard_number, standard_type, industry, category, sub_category,
                 pollution_factors, publish_date, implement_date, content, source_url, pdf_url, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title, std_num, std_type, industry, category, "",
            json.dumps(pollution_factors, ensure_ascii=False),
            pub_date or None, impl_date or None,
            f"标准编号: {std_num}\n标准名称: {title}\n标准类型: {std_type}\n类别: {category}\n适用行业: {industry}\n状态: {std.get('status', '现行')}\n发布日期: {pub_date}\n实施日期: {impl_date}",
            source_url, source_url, status, now, now,
        ))
        std_id = c.lastrowid
        inserted += 1

        # 插入污染因子和限值
        if known:
            for f in known["factors"]:
                symbol = f["symbol"]
                if symbol not in factor_cache:
                    c.execute("INSERT INTO pollution_factors (name, symbol, unit, created_at) VALUES (?, ?, ?, ?)",
                              (f["name"], symbol, f["limits"][0]["unit"], now))
                    factor_cache[symbol] = c.lastrowid
                factor_id = factor_cache[symbol]

                for limit in f["limits"]:
                    c.execute("""
                        INSERT INTO pollution_limits
                            (factor_id, standard_title, limit_value, unit, standard_type, description, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        factor_id, title, limit["value"], limit["unit"],
                        std_type, f"{limit['level']} - {limit['desc']}", now,
                    ))

    conn.commit()

    # 统计
    c.execute("SELECT COUNT(*) FROM standards")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM pollution_factors")
    factors = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM pollution_limits")
    limits = c.fetchone()[0]
    c.execute("SELECT category, COUNT(*) FROM standards GROUP BY category ORDER BY COUNT(*) DESC")
    cat_stats = c.fetchall()
    c.execute("SELECT industry, COUNT(*) FROM standards GROUP BY industry ORDER BY COUNT(*) DESC LIMIT 10")
    ind_stats = c.fetchall()
    conn.close()

    return inserted, total, factors, limits, cat_stats, ind_stats


def crawl():
    """主爬取函数"""
    all_standards = []
    seen_numbers = set()

    print("=" * 70)
    print("从 openstd.samr.gov.cn 爬取国家标准")
    print(f"覆盖行业: 环保/化工/医药/能源/纺织/橡塑/电气")
    print("=" * 70)

    for ics, p1, label in ICS_CATEGORIES:
        std_type_label = "强制GB" if p1 == "1" else "推荐GB/T"
        print(f"\n[{label}-{std_type_label}] ICS={ics}")

        page = 1
        category_count = 0

        while True:
            url = (
                f"{BASE}/bzgk/std/std_list_type?"
                f"r=0.1&page={page}&pageSize={PAGE_SIZE}"
                f"&p.p1={p1}&p.p6={ics}"
                f"&p.p90=circulation_date&p.p91=desc"
            )
            html = fetch(url)
            if not html:
                print(f"  第{page}页: 请求失败")
                break

            if page == 1:
                total = get_total_count(html)
                print(f"  总条数: {total}")

            items = parse_list_page(html)
            if not items:
                print(f"  第{page}页: 无数据")
                break

            for item in items:
                std_num = item.get("standard_number", "").strip()
                if std_num and std_num not in seen_numbers:
                    seen_numbers.add(std_num)
                    # category: 环保类先用标题推断具体类别(废水/废气等)，推断为"综合"时用ICS标签
                    inferred_cat = infer_category(item.get("title", ""))
                    if inferred_cat == "综合":
                        item["category"] = label
                    else:
                        item["category"] = inferred_cat
                    # industry: 先用标题推断，推断为"通用行业"时用ICS标签
                    inferred_ind = infer_industry(item.get("title", ""))
                    if inferred_ind == "通用行业":
                        item["industry"] = label
                    else:
                        item["industry"] = inferred_ind
                    item["standard_type"] = infer_standard_type(std_num)
                    all_standards.append(item)
                    category_count += 1

            print(f"  第{page}页: {len(items)}条, 本分类累计{category_count}条, 总计{len(all_standards)}条", flush=True)

            # 检查是否还有下一页
            clean_html = html.replace('&nbsp;', ' ').replace('\xa0', ' ')
            total_pages_match = re.search(r'共\s*\d+\s*条标准\s*\d+\s*/\s*(\d+)', clean_html)
            if total_pages_match:
                total_pages = int(total_pages_match.group(1))
                if page >= total_pages:
                    break
            else:
                # 如果本页少于PAGE_SIZE条，可能是最后一页
                if len(items) < PAGE_SIZE:
                    break

            page += 1
            if MAX_PAGES_PER_CATEGORY > 0 and page > MAX_PAGES_PER_CATEGORY:
                break
            time.sleep(SLEEP_BETWEEN_PAGES)

        time.sleep(SLEEP_BETWEEN_CATEGORIES)

    print(f"\n{'=' * 70}")
    print(f"爬取完成: 共 {len(all_standards)} 条标准 (去重后)")
    print(f"{'=' * 70}")
    return all_standards


if __name__ == "__main__":
    # 1. 清空旧数据
    clean_database()

    # 2. 爬取新数据
    standards = crawl()

    # 3. 保存到数据库
    inserted, total, factors, limits, cat_stats, ind_stats = save_to_db(standards)

    print(f"\n{'=' * 70}")
    print(f"数据库重建完成!")
    print(f"  标准总数: {total}")
    print(f"  污染因子: {factors}")
    print(f"  污染限值: {limits}")
    print(f"\n按类别统计:")
    for cat, cnt in cat_stats:
        print(f"  {cat}: {cnt}条")
    print(f"\n按行业统计 (前10):")
    for ind, cnt in ind_stats:
        print(f"  {ind}: {cnt}条")
    print(f"{'=' * 70}")
