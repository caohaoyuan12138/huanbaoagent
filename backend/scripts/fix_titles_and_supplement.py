# -*- coding: utf-8 -*-
"""
1. 修复标题中带编号的问题
2. 为新入库和已有但缺限值的排放标准补充污染因子限值
数据来源：生态环境部 https://www.mee.gov.cn/ywgz/fgbz/bz/
"""
import re
import json
import sqlite3
from datetime import datetime

DB_PATH = "env_agent.db"


def fix_titles():
    """修复标题中带编号的问题"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    rows = c.execute("SELECT id, standard_number, title FROM standards WHERE source_url LIKE '%mee.gov.cn%'").fetchall()
    fixed = 0
    for sid, std_num, title in rows:
        if not title:
            continue
        new_title = title
        # 去掉标题中的标准编号（各种变体）
        if std_num:
            for variant in [std_num, std_num.replace(' ', ''),
                            std_num.replace('-', '—'), std_num.replace('-', '–'),
                            std_num.replace('-', '－'),
                            std_num.replace('/T', '/ T'), std_num.replace('/T', '/T')]:
                new_title = new_title.replace(variant, '').strip()
        # 去掉"代替..."部分
        new_title = re.sub(r'代替.*$', '', new_title).strip()
        # 去掉"（试行）"
        new_title = re.sub(r'（试行）$', '', new_title).strip()
        # 去掉多余空格
        new_title = re.sub(r'\s+', ' ', new_title).strip()

        if new_title and new_title != title and len(new_title) >= 3:
            c.execute("UPDATE standards SET title = ? WHERE id = ?", (new_title, sid))
            fixed += 1
            print(f"  修复: {std_num} | {title[:30]} -> {new_title[:30]}")

    conn.commit()
    conn.close()
    print(f"\n标题修复完成: {fixed} 条")


# ==================== 新增限值数据 ====================
NEW_LIMITS = {
    "GB 12348-2008": {  # 工业企业厂界环境噪声排放标准
        "factors": [
            {"name": "厂界噪声", "symbol": "Noise", "limits": [
                {"level": "1类(昼间)", "value": 55, "unit": "dB(A)", "desc": "工业企业厂界"},
                {"level": "1类(夜间)", "value": 45, "unit": "dB(A)", "desc": "工业企业厂界"},
                {"level": "2类(昼间)", "value": 60, "unit": "dB(A)", "desc": "工业企业厂界"},
                {"level": "2类(夜间)", "value": 50, "unit": "dB(A)", "desc": "工业企业厂界"},
                {"level": "3类(昼间)", "value": 65, "unit": "dB(A)", "desc": "工业企业厂界"},
                {"level": "3类(夜间)", "value": 55, "unit": "dB(A)", "desc": "工业企业厂界"},
                {"level": "4类(昼间)", "value": 70, "unit": "dB(A)", "desc": "工业企业厂界"},
                {"level": "4类(夜间)", "value": 55, "unit": "dB(A)", "desc": "工业企业厂界"},
            ]},
        ]
    },
    "GB 22337-2008": {  # 社会生活环境噪声排放标准
        "factors": [
            {"name": "边界噪声", "symbol": "Noise", "limits": [
                {"level": "1类(昼间)", "value": 55, "unit": "dB(A)", "desc": "社会生活边界"},
                {"level": "1类(夜间)", "value": 45, "unit": "dB(A)", "desc": "社会生活边界"},
                {"level": "2类(昼间)", "value": 60, "unit": "dB(A)", "desc": "社会生活边界"},
                {"level": "2类(夜间)", "value": 50, "unit": "dB(A)", "desc": "社会生活边界"},
                {"level": "3类(昼间)", "value": 65, "unit": "dB(A)", "desc": "社会生活边界"},
                {"level": "3类(夜间)", "value": 55, "unit": "dB(A)", "desc": "社会生活边界"},
                {"level": "4类(昼间)", "value": 70, "unit": "dB(A)", "desc": "社会生活边界"},
                {"level": "4类(夜间)", "value": 55, "unit": "dB(A)", "desc": "社会生活边界"},
            ]},
        ]
    },
    "GB 3096": {  # 声环境质量标准
        "factors": [
            {"name": "环境噪声", "symbol": "Noise", "limits": [
                {"level": "0类(昼间)", "value": 50, "unit": "dB(A)", "desc": "康复疗养区"},
                {"level": "0类(夜间)", "value": 40, "unit": "dB(A)", "desc": "康复疗养区"},
                {"level": "1类(昼间)", "value": 55, "unit": "dB(A)", "desc": "居民文教区"},
                {"level": "1类(夜间)", "value": 45, "unit": "dB(A)", "desc": "居民文教区"},
                {"level": "2类(昼间)", "value": 60, "unit": "dB(A)", "desc": "混合区"},
                {"level": "2类(夜间)", "value": 50, "unit": "dB(A)", "desc": "混合区"},
                {"level": "3类(昼间)", "value": 65, "unit": "dB(A)", "desc": "工业区"},
                {"level": "3类(夜间)", "value": 55, "unit": "dB(A)", "desc": "工业区"},
                {"level": "4类(昼间)", "value": 70, "unit": "dB(A)", "desc": "交通干线两侧"},
                {"level": "4类(夜间)", "value": 55, "unit": "dB(A)", "desc": "交通干线两侧"},
            ]},
        ]
    },
    "GB 20950-2020": {  # 储油库大气污染物排放标准
        "factors": [
            {"name": "非甲烷总烃", "symbol": "NMHC", "limits": [
                {"level": "现有企业", "value": 25, "unit": "mg/m³", "desc": "储油库油气处理装置"},
                {"level": "新建企业", "value": 25, "unit": "mg/m³", "desc": "储油库油气处理装置"},
            ]},
            {"name": "液泄漏值", "symbol": "Leak", "limits": [
                {"level": "通用", "value": 500, "unit": "ppm", "desc": "储油库泄漏控制"},
            ]},
        ]
    },
    "GB 20951-2020": {  # 油品运输大气污染物排放标准
        "factors": [
            {"name": "非甲烷总烃", "symbol": "NMHC", "limits": [
                {"level": "现有企业", "value": 5, "unit": "g/m³", "desc": "油品运输"},
                {"level": "新建企业", "value": 5, "unit": "g/m³", "desc": "油品运输"},
            ]},
        ]
    },
    "GB 20952-2020": {  # 加油站大气污染物排放标准
        "factors": [
            {"name": "非甲烷总烃", "symbol": "NMHC", "limits": [
                {"level": "现有企业", "value": 20, "unit": "g/m³", "desc": "加油站油气处理装置"},
                {"level": "新建企业", "value": 20, "unit": "g/m³", "desc": "加油站油气处理装置"},
            ]},
            {"name": "液泄漏值", "symbol": "Leak", "limits": [
                {"level": "通用", "value": 500, "unit": "ppm", "desc": "加油站泄漏控制"},
            ]},
        ]
    },
    "GB 21522-2024": {  # 煤层气排放标准
        "factors": [
            {"name": "甲烷", "symbol": "CH4", "limits": [
                {"level": "煤矿瓦斯", "value": 30, "unit": "%", "desc": "甲烷浓度限值(高于此浓度不得排放)"},
            ]},
        ]
    },
    "GB 3552-2018": {  # 船舶水污染物排放控制标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "内河", "value": 60, "unit": "mg/L", "desc": "船舶污水"},
                {"level": "沿海", "value": 125, "unit": "mg/L", "desc": "船舶污水"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "内河", "value": 35, "unit": "mg/L", "desc": "船舶污水"},
                {"level": "沿海", "value": 35, "unit": "mg/L", "desc": "船舶污水"},
            ]},
            {"name": "石油类", "symbol": "Petroleum", "limits": [
                {"level": "内河", "value": 5, "unit": "mg/L", "desc": "船舶含油污水"},
                {"level": "沿海", "value": 5, "unit": "mg/L", "desc": "船舶含油污水"},
            ]},
            {"name": "总氮", "symbol": "TN", "limits": [
                {"level": "内河", "value": 20, "unit": "mg/L", "desc": "船舶污水"},
            ]},
            {"name": "总磷", "symbol": "TP", "limits": [
                {"level": "内河", "value": 1.0, "unit": "mg/L", "desc": "船舶污水"},
            ]},
        ]
    },
    "GB 16171.1-2024": {  # 炼焦化学工业大气污染物排放标准
        "factors": [
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 30, "unit": "mg/m³", "desc": "炼焦化学工业"},
                {"level": "新建", "value": 15, "unit": "mg/m³", "desc": "炼焦化学工业"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "现有", "value": 100, "unit": "mg/m³", "desc": "炼焦化学工业"},
                {"level": "新建", "value": 50, "unit": "mg/m³", "desc": "炼焦化学工业"},
            ]},
            {"name": "氮氧化物", "symbol": "NOx", "limits": [
                {"level": "现有", "value": 300, "unit": "mg/m³", "desc": "炼焦化学工业"},
                {"level": "新建", "value": 150, "unit": "mg/m³", "desc": "炼焦化学工业"},
            ]},
            {"name": "苯并[a]芘", "symbol": "BaP", "limits": [
                {"level": "通用", "value": 0.003, "unit": "mg/m³", "desc": "炼焦化学工业"},
            ]},
            {"name": "苯可溶物", "symbol": "BSE", "limits": [
                {"level": "通用", "value": 0.5, "unit": "mg/m³", "desc": "炼焦化学工业"},
            ]},
        ]
    },
    "GB 25466.1-2025": {  # 铅、锌工业大气污染物排放标准
        "factors": [
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 50, "unit": "mg/m³", "desc": "铅锌工业"},
                {"level": "新建", "value": 30, "unit": "mg/m³", "desc": "铅锌工业"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "现有", "value": 400, "unit": "mg/m³", "desc": "铅锌工业"},
                {"level": "新建", "value": 200, "unit": "mg/m³", "desc": "铅锌工业"},
            ]},
            {"name": "铅及其化合物", "symbol": "Pb", "limits": [
                {"level": "现有", "value": 1.0, "unit": "mg/m³", "desc": "铅锌工业"},
                {"level": "新建", "value": 0.7, "unit": "mg/m³", "desc": "铅锌工业"},
            ]},
            {"name": "汞及其化合物", "symbol": "Hg", "limits": [
                {"level": "通用", "value": 0.015, "unit": "mg/m³", "desc": "铅锌工业"},
            ]},
        ]
    },
    "GB 26453-2011": {  # 平板玻璃工业大气污染物排放标准
        "factors": [
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 50, "unit": "mg/m³", "desc": "平板玻璃工业"},
                {"level": "新建", "value": 30, "unit": "mg/m³", "desc": "平板玻璃工业"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "现有", "value": 400, "unit": "mg/m³", "desc": "平板玻璃工业"},
                {"level": "新建", "value": 200, "unit": "mg/m³", "desc": "平板玻璃工业"},
            ]},
            {"name": "氮氧化物", "symbol": "NOx", "limits": [
                {"level": "现有", "value": 700, "unit": "mg/m³", "desc": "平板玻璃工业"},
                {"level": "新建", "value": 500, "unit": "mg/m³", "desc": "平板玻璃工业"},
            ]},
            {"name": "氯化氢", "symbol": "HCl", "limits": [
                {"level": "通用", "value": 30, "unit": "mg/m³", "desc": "平板玻璃工业"},
            ]},
        ]
    },
    "GB 13457-2025": {  # 屠宰及肉类加工工业水污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 60, "unit": "mg/L", "desc": "屠宰及肉类加工"},
                {"level": "间接排放", "value": 200, "unit": "mg/L", "desc": "屠宰及肉类加工"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "直接排放", "value": 10, "unit": "mg/L", "desc": "屠宰及肉类加工"},
                {"level": "间接排放", "value": 25, "unit": "mg/L", "desc": "屠宰及肉类加工"},
            ]},
            {"name": "总氮", "symbol": "TN", "limits": [
                {"level": "直接排放", "value": 20, "unit": "mg/L", "desc": "屠宰及肉类加工"},
                {"level": "间接排放", "value": 40, "unit": "mg/L", "desc": "屠宰及肉类加工"},
            ]},
            {"name": "总磷", "symbol": "TP", "limits": [
                {"level": "直接排放", "value": 0.5, "unit": "mg/L", "desc": "屠宰及肉类加工"},
                {"level": "间接排放", "value": 1.5, "unit": "mg/L", "desc": "屠宰及肉类加工"},
            ]},
            {"name": "动植物油", "symbol": "Oil", "limits": [
                {"level": "直接排放", "value": 10, "unit": "mg/L", "desc": "屠宰及肉类加工"},
                {"level": "间接排放", "value": 30, "unit": "mg/L", "desc": "屠宰及肉类加工"},
            ]},
        ]
    },
    "GB 21523-2024": {  # 农药工业水污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 60, "unit": "mg/L", "desc": "农药工业"},
                {"level": "间接排放", "value": 150, "unit": "mg/L", "desc": "农药工业"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "直接排放", "value": 10, "unit": "mg/L", "desc": "农药工业"},
                {"level": "间接排放", "value": 25, "unit": "mg/L", "desc": "农药工业"},
            ]},
            {"name": "总氮", "symbol": "TN", "limits": [
                {"level": "直接排放", "value": 20, "unit": "mg/L", "desc": "农药工业"},
                {"level": "间接排放", "value": 40, "unit": "mg/L", "desc": "农药工业"},
            ]},
            {"name": "总磷", "symbol": "TP", "limits": [
                {"level": "直接排放", "value": 0.5, "unit": "mg/L", "desc": "农药工业"},
                {"level": "间接排放", "value": 1.0, "unit": "mg/L", "desc": "农药工业"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "直接排放", "value": 50, "unit": "mg/L", "desc": "农药工业"},
                {"level": "间接排放", "value": 100, "unit": "mg/L", "desc": "农药工业"},
            ]},
        ]
    },
    "GB 46790-2025": {  # 耐火材料工业大气污染物排放标准
        "factors": [
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 30, "unit": "mg/m³", "desc": "耐火材料工业"},
                {"level": "新建", "value": 20, "unit": "mg/m³", "desc": "耐火材料工业"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "现有", "value": 200, "unit": "mg/m³", "desc": "耐火材料工业"},
                {"level": "新建", "value": 100, "unit": "mg/m³", "desc": "耐火材料工业"},
            ]},
            {"name": "氮氧化物", "symbol": "NOx", "limits": [
                {"level": "现有", "value": 300, "unit": "mg/m³", "desc": "耐火材料工业"},
                {"level": "新建", "value": 200, "unit": "mg/m³", "desc": "耐火材料工业"},
            ]},
        ]
    },
    "GB 46817-2025": {  # 食品加工制造业水污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 80, "unit": "mg/L", "desc": "食品加工制造"},
                {"level": "间接排放", "value": 200, "unit": "mg/L", "desc": "食品加工制造"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "直接排放", "value": 10, "unit": "mg/L", "desc": "食品加工制造"},
                {"level": "间接排放", "value": 25, "unit": "mg/L", "desc": "食品加工制造"},
            ]},
            {"name": "总氮", "symbol": "TN", "limits": [
                {"level": "直接排放", "value": 20, "unit": "mg/L", "desc": "食品加工制造"},
                {"level": "间接排放", "value": 40, "unit": "mg/L", "desc": "食品加工制造"},
            ]},
            {"name": "总磷", "symbol": "TP", "limits": [
                {"level": "直接排放", "value": 0.5, "unit": "mg/L", "desc": "食品加工制造"},
                {"level": "间接排放", "value": 1.5, "unit": "mg/L", "desc": "食品加工制造"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "直接排放", "value": 50, "unit": "mg/L", "desc": "食品加工制造"},
                {"level": "间接排放", "value": 100, "unit": "mg/L", "desc": "食品加工制造"},
            ]},
        ]
    },
    "GB 47945-2026": {  # 赤水河流域水污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 50, "unit": "mg/L", "desc": "赤水河流域"},
                {"level": "间接排放", "value": 100, "unit": "mg/L", "desc": "赤水河流域"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "直接排放", "value": 5, "unit": "mg/L", "desc": "赤水河流域"},
                {"level": "间接排放", "value": 15, "unit": "mg/L", "desc": "赤水河流域"},
            ]},
            {"name": "总氮", "symbol": "TN", "limits": [
                {"level": "直接排放", "value": 15, "unit": "mg/L", "desc": "赤水河流域"},
                {"level": "间接排放", "value": 30, "unit": "mg/L", "desc": "赤水河流域"},
            ]},
            {"name": "总磷", "symbol": "TP", "limits": [
                {"level": "直接排放", "value": 0.2, "unit": "mg/L", "desc": "赤水河流域"},
                {"level": "间接排放", "value": 0.5, "unit": "mg/L", "desc": "赤水河流域"},
            ]},
        ]
    },
    "GB 19821-2025": {  # 酒类制造业水污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 80, "unit": "mg/L", "desc": "酒类制造"},
                {"level": "间接排放", "value": 200, "unit": "mg/L", "desc": "酒类制造"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "直接排放", "value": 10, "unit": "mg/L", "desc": "酒类制造"},
                {"level": "间接排放", "value": 25, "unit": "mg/L", "desc": "酒类制造"},
            ]},
            {"name": "总氮", "symbol": "TN", "limits": [
                {"level": "直接排放", "value": 20, "unit": "mg/L", "desc": "酒类制造"},
                {"level": "间接排放", "value": 40, "unit": "mg/L", "desc": "酒类制造"},
            ]},
            {"name": "总磷", "symbol": "TP", "limits": [
                {"level": "直接排放", "value": 0.5, "unit": "mg/L", "desc": "酒类制造"},
                {"level": "间接排放", "value": 1.5, "unit": "mg/L", "desc": "酒类制造"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "直接排放", "value": 50, "unit": "mg/L", "desc": "酒类制造"},
                {"level": "间接排放", "value": 100, "unit": "mg/L", "desc": "酒类制造"},
            ]},
        ]
    },
    "GB/T 14848-2017": {  # 地下水质量标准
        "factors": [
            {"name": "pH", "symbol": "pH", "limits": [
                {"level": "I类", "value": 7.0, "unit": "", "desc": "地下水天然背景"},
                {"level": "III类", "value": 8.5, "unit": "", "desc": "地下水集中式饮用水"},
                {"level": "V类", "value": 9.0, "unit": "", "desc": "地下水"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "III类", "value": 0.5, "unit": "mg/L", "desc": "地下水集中式饮用水"},
                {"level": "V类", "value": 1.5, "unit": "mg/L", "desc": "地下水"},
            ]},
            {"name": "硝酸盐", "symbol": "NO3-N", "limits": [
                {"level": "III类", "value": 20, "unit": "mg/L", "desc": "地下水集中式饮用水"},
                {"level": "V类", "value": 30, "unit": "mg/L", "desc": "地下水"},
            ]},
            {"name": "总硬度", "symbol": "TH", "limits": [
                {"level": "III类", "value": 450, "unit": "mg/L", "desc": "地下水集中式饮用水"},
                {"level": "V类", "value": 650, "unit": "mg/L", "desc": "地下水"},
            ]},
            {"name": "总大肠菌群", "symbol": "Coliform", "limits": [
                {"level": "III类", "value": 3.0, "unit": "MPN/L", "desc": "地下水集中式饮用水"},
            ]},
        ]
    },
    "GB/T 18883-2022": {  # 室内空气质量标准
        "factors": [
            {"name": "甲醛", "symbol": "HCHO", "limits": [
                {"level": "通用", "value": 0.08, "unit": "mg/m³", "desc": "室内空气(1小时均值)"},
            ]},
            {"name": "苯", "symbol": "C6H6", "limits": [
                {"level": "通用", "value": 0.03, "unit": "mg/m³", "desc": "室内空气(1小时均值)"},
            ]},
            {"name": "TVOC", "symbol": "TVOC", "limits": [
                {"level": "通用", "value": 0.5, "unit": "mg/m³", "desc": "室内空气(8小时均值)"},
            ]},
            {"name": "PM2.5", "symbol": "PM2.5", "limits": [
                {"level": "通用", "value": 50, "unit": "μg/m³", "desc": "室内空气(24小时均值)"},
            ]},
            {"name": "PM10", "symbol": "PM10", "limits": [
                {"level": "通用", "value": 100, "unit": "μg/m³", "desc": "室内空气(24小时均值)"},
            ]},
            {"name": "二氧化碳", "symbol": "CO2", "limits": [
                {"level": "通用", "value": 1000, "unit": "mg/m³", "desc": "室内空气(日均值)"},
            ]},
        ]
    },
}


def supplement_limits():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    factor_cache = {}
    for row in c.execute("SELECT id, symbol FROM pollution_factors"):
        factor_cache[row[1]] = row[0]

    supplemented = 0
    skipped = []

    for std_num, data in NEW_LIMITS.items():
        rows = c.execute("SELECT id, title, standard_type FROM standards WHERE standard_number = ?", (std_num,)).fetchall()
        if not rows:
            # 尝试模糊匹配
            norm = re.sub(r'\s+', '', std_num)
            rows = c.execute("SELECT id, title, standard_type FROM standards WHERE REPLACE(standard_number, ' ', '') = ?", (norm,)).fetchall()
        if not rows:
            skipped.append((std_num, "数据库中无此标准"))
            continue

        for std_id, std_title, std_type in rows:
            existing = c.execute("SELECT COUNT(*) FROM pollution_limits WHERE standard_title = ?", (std_title,)).fetchone()[0]
            if existing > 0:
                skipped.append((std_num, f"已有{existing}条限值，跳过"))
                continue

            pf_json = []
            for f in data["factors"]:
                symbol = f["symbol"]
                pf_json.append({"name": f["name"], "symbol": symbol, "limits": f["limits"]})

                if symbol not in factor_cache:
                    c.execute("INSERT INTO pollution_factors (name, symbol, unit, created_at) VALUES (?, ?, ?, ?)",
                              (f["name"], symbol, f["limits"][0]["unit"], now))
                    factor_cache[symbol] = c.lastrowid
                factor_id = factor_cache[symbol]

                for limit in f["limits"]:
                    c.execute("""INSERT INTO pollution_limits
                        (factor_id, standard_title, limit_value, unit, standard_type, description, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (factor_id, std_title, limit["value"], limit["unit"],
                         std_type or "国家标准", f"{limit['level']} - {limit['desc']}", now))

            c.execute("UPDATE standards SET pollution_factors = ? WHERE id = ?",
                      (json.dumps(pf_json, ensure_ascii=False), std_id))
            supplemented += 1
            print(f"  + {std_num} | {std_title[:30]} | {len(data['factors'])}个因子")

    conn.commit()
    total_factors = c.execute("SELECT COUNT(*) FROM pollution_factors").fetchone()[0]
    total_limits = c.execute("SELECT COUNT(*) FROM pollution_limits").fetchone()[0]
    standards_with_limits = c.execute("SELECT COUNT(DISTINCT standard_title) FROM pollution_limits").fetchone()[0]
    total_standards = c.execute("SELECT COUNT(*) FROM standards").fetchone()[0]

    print(f"\n{'='*60}")
    print(f"限值补充完成!")
    print(f"  本次补充: {supplemented} 个标准")
    print(f"  数据库标准总数: {total_standards}")
    print(f"  污染因子总数: {total_factors}")
    print(f"  污染限值总数: {total_limits}")
    print(f"  含限值的标准数: {standards_with_limits}")
    if skipped:
        print(f"\n  跳过 {len(skipped)} 项:")
        for s in skipped:
            print(f"    {s[0]}: {s[1]}")
    conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("第1步: 修复标题中带编号的问题")
    print("=" * 60)
    fix_titles()

    print("\n" + "=" * 60)
    print("第2步: 补充排放标准的污染因子限值")
    print("=" * 60)
    supplement_limits()
