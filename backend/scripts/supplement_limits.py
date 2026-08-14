# -*- coding: utf-8 -*-
"""
补充排放标准的污染因子限值数据
数据来源：生态环境部 https://www.mee.gov.cn/ywgz/fgbz/bz/ 公开标准文本
覆盖数据库中所有"排放标准"但缺少限值的标准
"""
import sqlite3
import json
from datetime import datetime

DB_PATH = "env_agent.db"

# ==================== 排放标准污染因子限值补充数据 ====================
# 基于生态环境部公开标准文本整理
SUPPLEMENT_LIMITS = {
    # ===== 废水类 =====
    "GB 13457-1992": {  # 肉类加工工业水污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "一级", "value": 80, "unit": "mg/L", "desc": "肉类加工"},
                {"level": "二级", "value": 120, "unit": "mg/L", "desc": "肉类加工"},
                {"level": "三级", "value": 500, "unit": "mg/L", "desc": "肉类加工"},
            ]},
            {"name": "生化需氧量", "symbol": "BOD5", "limits": [
                {"level": "一级", "value": 30, "unit": "mg/L", "desc": "肉类加工"},
                {"level": "二级", "value": 60, "unit": "mg/L", "desc": "肉类加工"},
                {"level": "三级", "value": 300, "unit": "mg/L", "desc": "肉类加工"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "一级", "value": 70, "unit": "mg/L", "desc": "肉类加工"},
                {"level": "二级", "value": 150, "unit": "mg/L", "desc": "肉类加工"},
                {"level": "三级", "value": 400, "unit": "mg/L", "desc": "肉类加工"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "一级", "value": 15, "unit": "mg/L", "desc": "肉类加工"},
                {"level": "二级", "value": 25, "unit": "mg/L", "desc": "肉类加工"},
            ]},
            {"name": "动植物油", "symbol": "Oil", "limits": [
                {"level": "一级", "value": 15, "unit": "mg/L", "desc": "肉类加工"},
                {"level": "二级", "value": 30, "unit": "mg/L", "desc": "肉类加工"},
            ]},
        ]
    },
    "GB 13458-2013": {  # 合成氨工业水污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 60, "unit": "mg/L", "desc": "合成氨工业"},
                {"level": "间接排放", "value": 200, "unit": "mg/L", "desc": "合成氨工业"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "直接排放", "value": 10, "unit": "mg/L", "desc": "合成氨工业"},
                {"level": "间接排放", "value": 30, "unit": "mg/L", "desc": "合成氨工业"},
            ]},
            {"name": "总氮", "symbol": "TN", "limits": [
                {"level": "直接排放", "value": 30, "unit": "mg/L", "desc": "合成氨工业"},
                {"level": "间接排放", "value": 50, "unit": "mg/L", "desc": "合成氨工业"},
            ]},
            {"name": "总磷", "symbol": "TP", "limits": [
                {"level": "直接排放", "value": 0.5, "unit": "mg/L", "desc": "合成氨工业"},
                {"level": "间接排放", "value": 1.0, "unit": "mg/L", "desc": "合成氨工业"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "直接排放", "value": 50, "unit": "mg/L", "desc": "合成氨工业"},
                {"level": "间接排放", "value": 100, "unit": "mg/L", "desc": "合成氨工业"},
            ]},
        ]
    },
    "GB 15580-2011": {  # 磷肥工业水污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 80, "unit": "mg/L", "desc": "磷肥工业"},
                {"level": "间接排放", "value": 150, "unit": "mg/L", "desc": "磷肥工业"},
            ]},
            {"name": "总磷", "symbol": "TP", "limits": [
                {"level": "直接排放", "value": 10, "unit": "mg/L", "desc": "磷肥工业"},
                {"level": "间接排放", "value": 20, "unit": "mg/L", "desc": "磷肥工业"},
            ]},
            {"name": "氟化物", "symbol": "F", "limits": [
                {"level": "直接排放", "value": 15, "unit": "mg/L", "desc": "磷肥工业"},
                {"level": "间接排放", "value": 30, "unit": "mg/L", "desc": "磷肥工业"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "直接排放", "value": 50, "unit": "mg/L", "desc": "磷肥工业"},
                {"level": "间接排放", "value": 100, "unit": "mg/L", "desc": "磷肥工业"},
            ]},
        ]
    },
    "GB 15581-2016": {  # 烧碱、聚氯乙烯工业污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 60, "unit": "mg/L", "desc": "烧碱聚氯乙烯工业"},
                {"level": "间接排放", "value": 150, "unit": "mg/L", "desc": "烧碱聚氯乙烯工业"},
            ]},
            {"name": "总汞", "symbol": "Hg", "limits": [
                {"level": "直接排放", "value": 0.005, "unit": "mg/L", "desc": "聚氯乙烯"},
                {"level": "间接排放", "value": 0.005, "unit": "mg/L", "desc": "聚氯乙烯"},
            ]},
            {"name": "总氯乙烯", "symbol": "C2H3Cl", "limits": [
                {"level": "直接排放", "value": 0.5, "unit": "mg/L", "desc": "聚氯乙烯"},
                {"level": "间接排放", "value": 1.0, "unit": "mg/L", "desc": "聚氯乙烯"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "直接排放", "value": 50, "unit": "mg/L", "desc": "烧碱聚氯乙烯工业"},
                {"level": "间接排放", "value": 100, "unit": "mg/L", "desc": "烧碱聚氯乙烯工业"},
            ]},
        ]
    },
    "GB 18466-2005": {  # 医疗机构水污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "传染病", "value": 60, "unit": "mg/L", "desc": "传染病医疗机构"},
                {"level": "综合", "value": 60, "unit": "mg/L", "desc": "综合医疗机构"},
            ]},
            {"name": "生化需氧量", "symbol": "BOD5", "limits": [
                {"level": "传染病", "value": 20, "unit": "mg/L", "desc": "传染病医疗机构"},
                {"level": "综合", "value": 20, "unit": "mg/L", "desc": "综合医疗机构"},
            ]},
            {"name": "总余氯", "symbol": "Cl", "limits": [
                {"level": "传染病", "value": 0.5, "unit": "mg/L", "desc": "传染病医疗机构"},
                {"level": "综合", "value": 0.5, "unit": "mg/L", "desc": "综合医疗机构"},
            ]},
            {"name": "粪大肠菌群", "symbol": "Coliform", "limits": [
                {"level": "通用", "value": 500, "unit": "MPN/L", "desc": "医疗机构"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "传染病", "value": 20, "unit": "mg/L", "desc": "传染病医疗机构"},
                {"level": "综合", "value": 20, "unit": "mg/L", "desc": "综合医疗机构"},
            ]},
        ]
    },
    "GB 18918-2002": {  # 城镇污水处理厂污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "一级A", "value": 50, "unit": "mg/L", "desc": "城镇污水处理厂"},
                {"level": "一级B", "value": 60, "unit": "mg/L", "desc": "城镇污水处理厂"},
                {"level": "二级", "value": 100, "unit": "mg/L", "desc": "城镇污水处理厂"},
            ]},
            {"name": "生化需氧量", "symbol": "BOD5", "limits": [
                {"level": "一级A", "value": 10, "unit": "mg/L", "desc": "城镇污水处理厂"},
                {"level": "一级B", "value": 20, "unit": "mg/L", "desc": "城镇污水处理厂"},
                {"level": "二级", "value": 30, "unit": "mg/L", "desc": "城镇污水处理厂"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "一级A", "value": 10, "unit": "mg/L", "desc": "城镇污水处理厂"},
                {"level": "一级B", "value": 20, "unit": "mg/L", "desc": "城镇污水处理厂"},
                {"level": "二级", "value": 30, "unit": "mg/L", "desc": "城镇污水处理厂"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "一级A", "value": 5, "unit": "mg/L", "desc": "城镇污水处理厂"},
                {"level": "一级B", "value": 8, "unit": "mg/L", "desc": "城镇污水处理厂"},
                {"level": "二级", "value": 25, "unit": "mg/L", "desc": "城镇污水处理厂"},
            ]},
            {"name": "总磷", "symbol": "TP", "limits": [
                {"level": "一级A", "value": 0.5, "unit": "mg/L", "desc": "城镇污水处理厂"},
                {"level": "一级B", "value": 1.0, "unit": "mg/L", "desc": "城镇污水处理厂"},
                {"level": "二级", "value": 3.0, "unit": "mg/L", "desc": "城镇污水处理厂"},
            ]},
            {"name": "总氮", "symbol": "TN", "limits": [
                {"level": "一级A", "value": 15, "unit": "mg/L", "desc": "城镇污水处理厂"},
                {"level": "一级B", "value": 20, "unit": "mg/L", "desc": "城镇污水处理厂"},
            ]},
        ]
    },
    "GB 19430-2013": {  # 柠檬酸工业水污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 80, "unit": "mg/L", "desc": "柠檬酸工业"},
                {"level": "间接排放", "value": 200, "unit": "mg/L", "desc": "柠檬酸工业"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "直接排放", "value": 10, "unit": "mg/L", "desc": "柠檬酸工业"},
                {"level": "间接排放", "value": 25, "unit": "mg/L", "desc": "柠檬酸工业"},
            ]},
            {"name": "总氮", "symbol": "TN", "limits": [
                {"level": "直接排放", "value": 25, "unit": "mg/L", "desc": "柠檬酸工业"},
                {"level": "间接排放", "value": 40, "unit": "mg/L", "desc": "柠檬酸工业"},
            ]},
            {"name": "总磷", "symbol": "TP", "limits": [
                {"level": "直接排放", "value": 1.0, "unit": "mg/L", "desc": "柠檬酸工业"},
                {"level": "间接排放", "value": 2.0, "unit": "mg/L", "desc": "柠檬酸工业"},
            ]},
        ]
    },
    "GB 19821-2005": {  # 啤酒工业污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 80, "unit": "mg/L", "desc": "啤酒工业"},
                {"level": "间接排放", "value": 200, "unit": "mg/L", "desc": "啤酒工业"},
            ]},
            {"name": "生化需氧量", "symbol": "BOD5", "limits": [
                {"level": "直接排放", "value": 20, "unit": "mg/L", "desc": "啤酒工业"},
                {"level": "间接排放", "value": 60, "unit": "mg/L", "desc": "啤酒工业"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "直接排放", "value": 50, "unit": "mg/L", "desc": "啤酒工业"},
                {"level": "间接排放", "value": 120, "unit": "mg/L", "desc": "啤酒工业"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "直接排放", "value": 10, "unit": "mg/L", "desc": "啤酒工业"},
                {"level": "间接排放", "value": 20, "unit": "mg/L", "desc": "啤酒工业"},
            ]},
            {"name": "总磷", "symbol": "TP", "limits": [
                {"level": "直接排放", "value": 1.0, "unit": "mg/L", "desc": "啤酒工业"},
                {"level": "间接排放", "value": 3.0, "unit": "mg/L", "desc": "啤酒工业"},
            ]},
        ]
    },
    "GB 20426-2006": {  # 煤炭工业污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 50, "unit": "mg/L", "desc": "煤炭工业"},
                {"level": "间接排放", "value": 150, "unit": "mg/L", "desc": "煤炭工业"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "直接排放", "value": 50, "unit": "mg/L", "desc": "煤炭工业"},
                {"level": "间接排放", "value": 100, "unit": "mg/L", "desc": "煤炭工业"},
            ]},
            {"name": "石油类", "symbol": "Petroleum", "limits": [
                {"level": "直接排放", "value": 3, "unit": "mg/L", "desc": "煤炭工业"},
                {"level": "间接排放", "value": 10, "unit": "mg/L", "desc": "煤炭工业"},
            ]},
            {"name": "总铁", "symbol": "Fe", "limits": [
                {"level": "直接排放", "value": 2, "unit": "mg/L", "desc": "煤炭工业"},
                {"level": "间接排放", "value": 5, "unit": "mg/L", "desc": "煤炭工业"},
            ]},
            {"name": "总锰", "symbol": "Mn", "limits": [
                {"level": "直接排放", "value": 2, "unit": "mg/L", "desc": "煤炭工业"},
                {"level": "间接排放", "value": 4, "unit": "mg/L", "desc": "煤炭工业"},
            ]},
        ]
    },
    "GB 21908-2008": {  # 混装制剂类制药工业水污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 80, "unit": "mg/L", "desc": "混装制剂类制药"},
                {"level": "间接排放", "value": 150, "unit": "mg/L", "desc": "混装制剂类制药"},
            ]},
            {"name": "生化需氧量", "symbol": "BOD5", "limits": [
                {"level": "直接排放", "value": 20, "unit": "mg/L", "desc": "混装制剂类制药"},
                {"level": "间接排放", "value": 40, "unit": "mg/L", "desc": "混装制剂类制药"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "直接排放", "value": 30, "unit": "mg/L", "desc": "混装制剂类制药"},
                {"level": "间接排放", "value": 60, "unit": "mg/L", "desc": "混装制剂类制药"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "直接排放", "value": 10, "unit": "mg/L", "desc": "混装制剂类制药"},
                {"level": "间接排放", "value": 25, "unit": "mg/L", "desc": "混装制剂类制药"},
            ]},
            {"name": "总磷", "symbol": "TP", "limits": [
                {"level": "直接排放", "value": 0.5, "unit": "mg/L", "desc": "混装制剂类制药"},
                {"level": "间接排放", "value": 1.0, "unit": "mg/L", "desc": "混装制剂类制药"},
            ]},
        ]
    },
    "GB 21909-2008": {  # 制糖工业水污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 100, "unit": "mg/L", "desc": "制糖工业"},
                {"level": "间接排放", "value": 300, "unit": "mg/L", "desc": "制糖工业"},
            ]},
            {"name": "生化需氧量", "symbol": "BOD5", "limits": [
                {"level": "直接排放", "value": 30, "unit": "mg/L", "desc": "制糖工业"},
                {"level": "间接排放", "value": 80, "unit": "mg/L", "desc": "制糖工业"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "直接排放", "value": 50, "unit": "mg/L", "desc": "制糖工业"},
                {"level": "间接排放", "value": 100, "unit": "mg/L", "desc": "制糖工业"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "直接排放", "value": 10, "unit": "mg/L", "desc": "制糖工业"},
                {"level": "间接排放", "value": 20, "unit": "mg/L", "desc": "制糖工业"},
            ]},
            {"name": "总磷", "symbol": "TP", "limits": [
                {"level": "直接排放", "value": 0.5, "unit": "mg/L", "desc": "制糖工业"},
                {"level": "间接排放", "value": 1.5, "unit": "mg/L", "desc": "制糖工业"},
            ]},
        ]
    },
    "GB 25461-2010": {  # 淀粉工业水污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 100, "unit": "mg/L", "desc": "淀粉工业"},
                {"level": "间接排放", "value": 300, "unit": "mg/L", "desc": "淀粉工业"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "直接排放", "value": 15, "unit": "mg/L", "desc": "淀粉工业"},
                {"level": "间接排放", "value": 30, "unit": "mg/L", "desc": "淀粉工业"},
            ]},
            {"name": "总氮", "symbol": "TN", "limits": [
                {"level": "直接排放", "value": 30, "unit": "mg/L", "desc": "淀粉工业"},
                {"level": "间接排放", "value": 50, "unit": "mg/L", "desc": "淀粉工业"},
            ]},
            {"name": "总磷", "symbol": "TP", "limits": [
                {"level": "直接排放", "value": 1.0, "unit": "mg/L", "desc": "淀粉工业"},
                {"level": "间接排放", "value": 2.0, "unit": "mg/L", "desc": "淀粉工业"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "直接排放", "value": 50, "unit": "mg/L", "desc": "淀粉工业"},
                {"level": "间接排放", "value": 100, "unit": "mg/L", "desc": "淀粉工业"},
            ]},
        ]
    },
    "GB 25463-2010": {  # 油墨工业水污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 80, "unit": "mg/L", "desc": "油墨工业"},
                {"level": "间接排放", "value": 200, "unit": "mg/L", "desc": "油墨工业"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "直接排放", "value": 50, "unit": "mg/L", "desc": "油墨工业"},
                {"level": "间接排放", "value": 100, "unit": "mg/L", "desc": "油墨工业"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "直接排放", "value": 10, "unit": "mg/L", "desc": "油墨工业"},
                {"level": "间接排放", "value": 25, "unit": "mg/L", "desc": "油墨工业"},
            ]},
            {"name": "总磷", "symbol": "TP", "limits": [
                {"level": "直接排放", "value": 0.5, "unit": "mg/L", "desc": "油墨工业"},
                {"level": "间接排放", "value": 1.0, "unit": "mg/L", "desc": "油墨工业"},
            ]},
        ]
    },
    "GB 27631-2011": {  # 发酵酒精和白酒工业水污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 100, "unit": "mg/L", "desc": "发酵酒精白酒工业"},
                {"level": "间接排放", "value": 300, "unit": "mg/L", "desc": "发酵酒精白酒工业"},
            ]},
            {"name": "生化需氧量", "symbol": "BOD5", "limits": [
                {"level": "直接排放", "value": 30, "unit": "mg/L", "desc": "发酵酒精白酒工业"},
                {"level": "间接排放", "value": 80, "unit": "mg/L", "desc": "发酵酒精白酒工业"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "直接排放", "value": 50, "unit": "mg/L", "desc": "发酵酒精白酒工业"},
                {"level": "间接排放", "value": 150, "unit": "mg/L", "desc": "发酵酒精白酒工业"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "直接排放", "value": 10, "unit": "mg/L", "desc": "发酵酒精白酒工业"},
                {"level": "间接排放", "value": 25, "unit": "mg/L", "desc": "发酵酒精白酒工业"},
            ]},
            {"name": "总氮", "symbol": "TN", "limits": [
                {"level": "直接排放", "value": 20, "unit": "mg/L", "desc": "发酵酒精白酒工业"},
                {"level": "间接排放", "value": 40, "unit": "mg/L", "desc": "发酵酒精白酒工业"},
            ]},
        ]
    },
    "GB 28937-2012": {  # 毛纺工业水污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 80, "unit": "mg/L", "desc": "毛纺工业"},
                {"level": "间接排放", "value": 200, "unit": "mg/L", "desc": "毛纺工业"},
            ]},
            {"name": "生化需氧量", "symbol": "BOD5", "limits": [
                {"level": "直接排放", "value": 20, "unit": "mg/L", "desc": "毛纺工业"},
                {"level": "间接排放", "value": 50, "unit": "mg/L", "desc": "毛纺工业"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "直接排放", "value": 50, "unit": "mg/L", "desc": "毛纺工业"},
                {"level": "间接排放", "value": 100, "unit": "mg/L", "desc": "毛纺工业"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "直接排放", "value": 10, "unit": "mg/L", "desc": "毛纺工业"},
                {"level": "间接排放", "value": 20, "unit": "mg/L", "desc": "毛纺工业"},
            ]},
        ]
    },
    "GB 30486-2013": {  # 制革及毛皮加工工业水污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 80, "unit": "mg/L", "desc": "制革毛皮工业"},
                {"level": "间接排放", "value": 200, "unit": "mg/L", "desc": "制革毛皮工业"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "直接排放", "value": 10, "unit": "mg/L", "desc": "制革毛皮工业"},
                {"level": "间接排放", "value": 30, "unit": "mg/L", "desc": "制革毛皮工业"},
            ]},
            {"name": "总氮", "symbol": "TN", "limits": [
                {"level": "直接排放", "value": 25, "unit": "mg/L", "desc": "制革毛皮工业"},
                {"level": "间接排放", "value": 50, "unit": "mg/L", "desc": "制革毛皮工业"},
            ]},
            {"name": "总铬", "symbol": "Cr", "limits": [
                {"level": "直接排放", "value": 1.5, "unit": "mg/L", "desc": "制革毛皮工业"},
                {"level": "间接排放", "value": 1.5, "unit": "mg/L", "desc": "制革毛皮工业"},
            ]},
            {"name": "六价铬", "symbol": "Cr6+", "limits": [
                {"level": "直接排放", "value": 0.1, "unit": "mg/L", "desc": "制革毛皮工业"},
                {"level": "间接排放", "value": 0.1, "unit": "mg/L", "desc": "制革毛皮工业"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "直接排放", "value": 50, "unit": "mg/L", "desc": "制革毛皮工业"},
                {"level": "间接排放", "value": 100, "unit": "mg/L", "desc": "制革毛皮工业"},
            ]},
        ]
    },
    "GB 39731-2020": {  # 电子工业水污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 60, "unit": "mg/L", "desc": "电子工业"},
                {"level": "间接排放", "value": 150, "unit": "mg/L", "desc": "电子工业"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "直接排放", "value": 10, "unit": "mg/L", "desc": "电子工业"},
                {"level": "间接排放", "value": 25, "unit": "mg/L", "desc": "电子工业"},
            ]},
            {"name": "总氮", "symbol": "TN", "limits": [
                {"level": "直接排放", "value": 20, "unit": "mg/L", "desc": "电子工业"},
                {"level": "间接排放", "value": 40, "unit": "mg/L", "desc": "电子工业"},
            ]},
            {"name": "总磷", "symbol": "TP", "limits": [
                {"level": "直接排放", "value": 1.0, "unit": "mg/L", "desc": "电子工业"},
                {"level": "间接排放", "value": 2.0, "unit": "mg/L", "desc": "电子工业"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "直接排放", "value": 30, "unit": "mg/L", "desc": "电子工业"},
                {"level": "间接排放", "value": 80, "unit": "mg/L", "desc": "电子工业"},
            ]},
        ]
    },
    "GB 4287-2012": {  # 纺织染整工业水污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 80, "unit": "mg/L", "desc": "纺织染整"},
                {"level": "间接排放", "value": 200, "unit": "mg/L", "desc": "纺织染整"},
            ]},
            {"name": "生化需氧量", "symbol": "BOD5", "limits": [
                {"level": "直接排放", "value": 20, "unit": "mg/L", "desc": "纺织染整"},
                {"level": "间接排放", "value": 50, "unit": "mg/L", "desc": "纺织染整"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "直接排放", "value": 50, "unit": "mg/L", "desc": "纺织染整"},
                {"level": "间接排放", "value": 100, "unit": "mg/L", "desc": "纺织染整"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "直接排放", "value": 10, "unit": "mg/L", "desc": "纺织染整"},
                {"level": "间接排放", "value": 20, "unit": "mg/L", "desc": "纺织染整"},
            ]},
            {"name": "总氮", "symbol": "TN", "limits": [
                {"level": "直接排放", "value": 15, "unit": "mg/L", "desc": "纺织染整"},
                {"level": "间接排放", "value": 30, "unit": "mg/L", "desc": "纺织染整"},
            ]},
        ]
    },
    # ===== 废气类 =====
    "GB 13271-2014": {  # 锅炉大气污染物排放标准
        "factors": [
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "燃煤现有", "value": 50, "unit": "mg/m³", "desc": "锅炉"},
                {"level": "燃煤新建", "value": 30, "unit": "mg/m³", "desc": "锅炉"},
                {"level": "燃气", "value": 20, "unit": "mg/m³", "desc": "锅炉"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "燃煤现有", "value": 200, "unit": "mg/m³", "desc": "锅炉"},
                {"level": "燃煤新建", "value": 200, "unit": "mg/m³", "desc": "锅炉"},
                {"level": "燃气", "value": 50, "unit": "mg/m³", "desc": "锅炉"},
            ]},
            {"name": "氮氧化物", "symbol": "NOx", "limits": [
                {"level": "燃煤现有", "value": 300, "unit": "mg/m³", "desc": "锅炉"},
                {"level": "燃煤新建", "value": 200, "unit": "mg/m³", "desc": "锅炉"},
                {"level": "燃气", "value": 200, "unit": "mg/m³", "desc": "锅炉"},
            ]},
            {"name": "汞及其化合物", "symbol": "Hg", "limits": [
                {"level": "燃煤", "value": 0.05, "unit": "mg/m³", "desc": "锅炉"},
            ]},
        ]
    },
    "GB 13801-2015": {  # 火葬场大气污染物排放标准
        "factors": [
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 80, "unit": "mg/m³", "desc": "火葬场"},
                {"level": "新建", "value": 30, "unit": "mg/m³", "desc": "火葬场"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "现有", "value": 100, "unit": "mg/m³", "desc": "火葬场"},
                {"level": "新建", "value": 60, "unit": "mg/m³", "desc": "火葬场"},
            ]},
            {"name": "氮氧化物", "symbol": "NOx", "limits": [
                {"level": "现有", "value": 300, "unit": "mg/m³", "desc": "火葬场"},
                {"level": "新建", "value": 200, "unit": "mg/m³", "desc": "火葬场"},
            ]},
            {"name": "一氧化碳", "symbol": "CO", "limits": [
                {"level": "现有", "value": 200, "unit": "mg/m³", "desc": "火葬场"},
                {"level": "新建", "value": 80, "unit": "mg/m³", "desc": "火葬场"},
            ]},
        ]
    },
    "GB 18483-2001": {  # 饮食业油烟排放标准
        "factors": [
            {"name": "油烟", "symbol": "OilFume", "limits": [
                {"level": "小型", "value": 2.0, "unit": "mg/m³", "desc": "饮食业小型"},
                {"level": "中型", "value": 1.5, "unit": "mg/m³", "desc": "饮食业中型"},
                {"level": "大型", "value": 1.0, "unit": "mg/m³", "desc": "饮食业大型"},
            ]},
        ]
    },
    "GB 20950-2007": {  # 储油库大气污染物排放标准
        "factors": [
            {"name": "非甲烷总烃", "symbol": "NMHC", "limits": [
                {"level": "现有", "value": 80, "unit": "mg/m³", "desc": "储油库油气处理装置"},
                {"level": "新建", "value": 25, "unit": "mg/m³", "desc": "储油库油气处理装置"},
            ]},
        ]
    },
    "GB 20951-2007": {  # 汽油运输大气污染物排放标准
        "factors": [
            {"name": "非甲烷总烃", "symbol": "NMHC", "limits": [
                {"level": "现有", "value": 10, "unit": "g/m³", "desc": "汽油运输"},
                {"level": "新建", "value": 5, "unit": "g/m³", "desc": "汽油运输"},
            ]},
        ]
    },
    "GB 20952-2007": {  # 加油站大气污染物排放标准
        "factors": [
            {"name": "非甲烷总烃", "symbol": "NMHC", "limits": [
                {"level": "现有", "value": 25, "unit": "g/m³", "desc": "加油站油气处理装置"},
                {"level": "新建", "value": 20, "unit": "g/m³", "desc": "加油站油气处理装置"},
            ]},
        ]
    },
    "GB 26131-2010": {  # 硝酸工业污染物排放标准
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
    "GB 26132-2010": {  # 硫酸工业污染物排放标准
        "factors": [
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "现有", "value": 860, "unit": "mg/m³", "desc": "硫酸工业"},
                {"level": "新建", "value": 400, "unit": "mg/m³", "desc": "硫酸工业"},
            ]},
            {"name": "硫酸雾", "symbol": "H2SO4", "limits": [
                {"level": "现有", "value": 45, "unit": "mg/m³", "desc": "硫酸工业"},
                {"level": "新建", "value": 30, "unit": "mg/m³", "desc": "硫酸工业"},
            ]},
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 80, "unit": "mg/m³", "desc": "硫酸工业"},
                {"level": "新建", "value": 50, "unit": "mg/m³", "desc": "硫酸工业"},
            ]},
        ]
    },
    "GB 26452-2011": {  # 钒工业污染物排放标准
        "factors": [
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "现有", "value": 600, "unit": "mg/m³", "desc": "钒工业"},
                {"level": "新建", "value": 400, "unit": "mg/m³", "desc": "钒工业"},
            ]},
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 80, "unit": "mg/m³", "desc": "钒工业"},
                {"level": "新建", "value": 50, "unit": "mg/m³", "desc": "钒工业"},
            ]},
            {"name": "硫酸雾", "symbol": "H2SO4", "limits": [
                {"level": "现有", "value": 80, "unit": "mg/m³", "desc": "钒工业"},
                {"level": "新建", "value": 45, "unit": "mg/m³", "desc": "钒工业"},
            ]},
            {"name": "总钒", "symbol": "V", "limits": [
                {"level": "现有", "value": 0.7, "unit": "mg/m³", "desc": "钒工业"},
                {"level": "新建", "value": 0.5, "unit": "mg/m³", "desc": "钒工业"},
            ]},
        ]
    },
    "GB 26453-2022": {  # 玻璃工业大气污染物排放标准
        "factors": [
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 30, "unit": "mg/m³", "desc": "玻璃工业"},
                {"level": "新建", "value": 20, "unit": "mg/m³", "desc": "玻璃工业"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "现有", "value": 200, "unit": "mg/m³", "desc": "玻璃工业"},
                {"level": "新建", "value": 100, "unit": "mg/m³", "desc": "玻璃工业"},
            ]},
            {"name": "氮氧化物", "symbol": "NOx", "limits": [
                {"level": "现有", "value": 400, "unit": "mg/m³", "desc": "玻璃工业"},
                {"level": "新建", "value": 350, "unit": "mg/m³", "desc": "玻璃工业"},
            ]},
            {"name": "氯化氢", "symbol": "HCl", "limits": [
                {"level": "通用", "value": 30, "unit": "mg/m³", "desc": "玻璃工业"},
            ]},
        ]
    },
    "GB 27632-2011": {  # 橡胶制品工业污染物排放标准
        "factors": [
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 50, "unit": "mg/m³", "desc": "橡胶制品工业"},
                {"level": "新建", "value": 30, "unit": "mg/m³", "desc": "橡胶制品工业"},
            ]},
            {"name": "非甲烷总烃", "symbol": "NMHC", "limits": [
                {"level": "现有", "value": 80, "unit": "mg/m³", "desc": "橡胶制品工业"},
                {"level": "新建", "value": 50, "unit": "mg/m³", "desc": "橡胶制品工业"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "现有", "value": 200, "unit": "mg/m³", "desc": "橡胶制品工业"},
                {"level": "新建", "value": 100, "unit": "mg/m³", "desc": "橡胶制品工业"},
            ]},
        ]
    },
    "GB 28661-2012": {  # 铁矿采选工业污染物排放标准
        "factors": [
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 50, "unit": "mg/m³", "desc": "铁矿采选工业"},
                {"level": "新建", "value": 30, "unit": "mg/m³", "desc": "铁矿采选工业"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "现有", "value": 400, "unit": "mg/m³", "desc": "铁矿采选工业"},
                {"level": "新建", "value": 200, "unit": "mg/m³", "desc": "铁矿采选工业"},
            ]},
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 60, "unit": "mg/L", "desc": "铁矿采选工业"},
                {"level": "间接排放", "value": 200, "unit": "mg/L", "desc": "铁矿采选工业"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "直接排放", "value": 50, "unit": "mg/L", "desc": "铁矿采选工业"},
                {"level": "间接排放", "value": 100, "unit": "mg/L", "desc": "铁矿采选工业"},
            ]},
        ]
    },
    "GB 28666-2012": {  # 铁合金工业污染物排放标准
        "factors": [
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 80, "unit": "mg/m³", "desc": "铁合金工业"},
                {"level": "新建", "value": 50, "unit": "mg/m³", "desc": "铁合金工业"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "现有", "value": 400, "unit": "mg/m³", "desc": "铁合金工业"},
                {"level": "新建", "value": 200, "unit": "mg/m³", "desc": "铁合金工业"},
            ]},
            {"name": "铬酸雾", "symbol": "CrO3", "limits": [
                {"level": "现有", "value": 0.07, "unit": "mg/m³", "desc": "铁合金工业"},
                {"level": "新建", "value": 0.05, "unit": "mg/m³", "desc": "铁合金工业"},
            ]},
        ]
    },
    "GB 30484-2013": {  # 电池工业污染物排放标准
        "factors": [
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 50, "unit": "mg/m³", "desc": "电池工业"},
                {"level": "新建", "value": 30, "unit": "mg/m³", "desc": "电池工业"},
            ]},
            {"name": "硫酸雾", "symbol": "H2SO4", "limits": [
                {"level": "现有", "value": 30, "unit": "mg/m³", "desc": "电池工业"},
                {"level": "新建", "value": 15, "unit": "mg/m³", "desc": "电池工业"},
            ]},
            {"name": "铅及其化合物", "symbol": "Pb", "limits": [
                {"level": "现有", "value": 0.7, "unit": "mg/m³", "desc": "电池工业"},
                {"level": "新建", "value": 0.5, "unit": "mg/m³", "desc": "电池工业"},
            ]},
            {"name": "汞及其化合物", "symbol": "Hg", "limits": [
                {"level": "通用", "value": 0.01, "unit": "mg/m³", "desc": "电池工业"},
            ]},
        ]
    },
    "GB 30770-2014": {  # 锡、锑、汞工业污染物排放标准
        "factors": [
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 60, "unit": "mg/m³", "desc": "锡锑汞工业"},
                {"level": "新建", "value": 30, "unit": "mg/m³", "desc": "锡锑汞工业"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "现有", "value": 400, "unit": "mg/m³", "desc": "锡锑汞工业"},
                {"level": "新建", "value": 200, "unit": "mg/m³", "desc": "锡锑汞工业"},
            ]},
            {"name": "汞及其化合物", "symbol": "Hg", "limits": [
                {"level": "现有", "value": 0.015, "unit": "mg/m³", "desc": "锡锑汞工业"},
                {"level": "新建", "value": 0.012, "unit": "mg/m³", "desc": "锡锑汞工业"},
            ]},
            {"name": "铅及其化合物", "symbol": "Pb", "limits": [
                {"level": "现有", "value": 1.0, "unit": "mg/m³", "desc": "锡锑汞工业"},
                {"level": "新建", "value": 0.7, "unit": "mg/m³", "desc": "锡锑汞工业"},
            ]},
        ]
    },
    "GB 31573-2015": {  # 无机化学工业污染物排放标准
        "factors": [
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 50, "unit": "mg/m³", "desc": "无机化学工业"},
                {"level": "新建", "value": 30, "unit": "mg/m³", "desc": "无机化学工业"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "现有", "value": 200, "unit": "mg/m³", "desc": "无机化学工业"},
                {"level": "新建", "value": 100, "unit": "mg/m³", "desc": "无机化学工业"},
            ]},
            {"name": "氮氧化物", "symbol": "NOx", "limits": [
                {"level": "现有", "value": 300, "unit": "mg/m³", "desc": "无机化学工业"},
                {"level": "新建", "value": 200, "unit": "mg/m³", "desc": "无机化学工业"},
            ]},
            {"name": "氯气", "symbol": "Cl2", "limits": [
                {"level": "通用", "value": 5.0, "unit": "mg/m³", "desc": "无机化学工业"},
            ]},
            {"name": "氯化氢", "symbol": "HCl", "limits": [
                {"level": "通用", "value": 30, "unit": "mg/m³", "desc": "无机化学工业"},
            ]},
        ]
    },
    "GB 31574-2015": {  # 再生铜、铝、铅、锌工业污染物排放标准
        "factors": [
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 50, "unit": "mg/m³", "desc": "再生有色金属工业"},
                {"level": "新建", "value": 30, "unit": "mg/m³", "desc": "再生有色金属工业"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "现有", "value": 200, "unit": "mg/m³", "desc": "再生有色金属工业"},
                {"level": "新建", "value": 100, "unit": "mg/m³", "desc": "再生有色金属工业"},
            ]},
            {"name": "氮氧化物", "symbol": "NOx", "limits": [
                {"level": "现有", "value": 300, "unit": "mg/m³", "desc": "再生有色金属工业"},
                {"level": "新建", "value": 200, "unit": "mg/m³", "desc": "再生有色金属工业"},
            ]},
            {"name": "铅及其化合物", "symbol": "Pb", "limits": [
                {"level": "现有", "value": 1.0, "unit": "mg/m³", "desc": "再生有色金属工业"},
                {"level": "新建", "value": 0.7, "unit": "mg/m³", "desc": "再生有色金属工业"},
            ]},
        ]
    },
    "GB 37823-2019": {  # 制药工业大气污染物排放标准
        "factors": [
            {"name": "非甲烷总烃", "symbol": "NMHC", "limits": [
                {"level": "现有", "value": 120, "unit": "mg/m³", "desc": "制药工业"},
                {"level": "新建", "value": 60, "unit": "mg/m³", "desc": "制药工业"},
            ]},
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 50, "unit": "mg/m³", "desc": "制药工业"},
                {"level": "新建", "value": 30, "unit": "mg/m³", "desc": "制药工业"},
            ]},
            {"name": "苯", "symbol": "C6H6", "limits": [
                {"level": "通用", "value": 1.0, "unit": "mg/m³", "desc": "制药工业"},
            ]},
            {"name": "甲苯", "symbol": "C7H8", "limits": [
                {"level": "通用", "value": 15, "unit": "mg/m³", "desc": "制药工业"},
            ]},
            {"name": "甲醛", "symbol": "HCHO", "limits": [
                {"level": "通用", "value": 5.0, "unit": "mg/m³", "desc": "制药工业"},
            ]},
        ]
    },
    "GB 37824-2019": {  # 涂料、油墨及胶粘剂工业大气污染物排放标准
        "factors": [
            {"name": "非甲烷总烃", "symbol": "NMHC", "limits": [
                {"level": "现有", "value": 120, "unit": "mg/m³", "desc": "涂料油墨胶粘剂工业"},
                {"level": "新建", "value": 60, "unit": "mg/m³", "desc": "涂料油墨胶粘剂工业"},
            ]},
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 50, "unit": "mg/m³", "desc": "涂料油墨胶粘剂工业"},
                {"level": "新建", "value": 30, "unit": "mg/m³", "desc": "涂料油墨胶粘剂工业"},
            ]},
            {"name": "甲苯", "symbol": "C7H8", "limits": [
                {"level": "通用", "value": 15, "unit": "mg/m³", "desc": "涂料油墨胶粘剂工业"},
            ]},
            {"name": "二甲苯", "symbol": "C8H10", "limits": [
                {"level": "通用", "value": 20, "unit": "mg/m³", "desc": "涂料油墨胶粘剂工业"},
            ]},
        ]
    },
    "GB 39726-2020": {  # 铸造工业大气污染物排放标准
        "factors": [
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 30, "unit": "mg/m³", "desc": "铸造工业"},
                {"level": "新建", "value": 20, "unit": "mg/m³", "desc": "铸造工业"},
            ]},
            {"name": "非甲烷总烃", "symbol": "NMHC", "limits": [
                {"level": "现有", "value": 80, "unit": "mg/m³", "desc": "铸造工业"},
                {"level": "新建", "value": 60, "unit": "mg/m³", "desc": "铸造工业"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "通用", "value": 100, "unit": "mg/m³", "desc": "铸造工业"},
            ]},
        ]
    },
    "GB 39727-2020": {  # 农药制造工业大气污染物排放标准
        "factors": [
            {"name": "非甲烷总烃", "symbol": "NMHC", "limits": [
                {"level": "现有", "value": 120, "unit": "mg/m³", "desc": "农药制造工业"},
                {"level": "新建", "value": 60, "unit": "mg/m³", "desc": "农药制造工业"},
            ]},
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 50, "unit": "mg/m³", "desc": "农药制造工业"},
                {"level": "新建", "value": 30, "unit": "mg/m³", "desc": "农药制造工业"},
            ]},
            {"name": "甲苯", "symbol": "C7H8", "limits": [
                {"level": "通用", "value": 15, "unit": "mg/m³", "desc": "农药制造工业"},
            ]},
            {"name": "氯化氢", "symbol": "HCl", "limits": [
                {"level": "通用", "value": 30, "unit": "mg/m³", "desc": "农药制造工业"},
            ]},
        ]
    },
    "GB 39728-2020": {  # 陆上石油天然气开采工业大气污染物排放标准
        "factors": [
            {"name": "非甲烷总烃", "symbol": "NMHC", "limits": [
                {"level": "现有", "value": 120, "unit": "mg/m³", "desc": "石油天然气开采"},
                {"level": "新建", "value": 60, "unit": "mg/m³", "desc": "石油天然气开采"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "通用", "value": 200, "unit": "mg/m³", "desc": "石油天然气开采"},
            ]},
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "通用", "value": 30, "unit": "mg/m³", "desc": "石油天然气开采"},
            ]},
        ]
    },
    "GB 41616-2022": {  # 印刷工业大气污染物排放标准
        "factors": [
            {"name": "非甲烷总烃", "symbol": "NMHC", "limits": [
                {"level": "现有", "value": 80, "unit": "mg/m³", "desc": "印刷工业"},
                {"level": "新建", "value": 50, "unit": "mg/m³", "desc": "印刷工业"},
            ]},
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "通用", "value": 30, "unit": "mg/m³", "desc": "印刷工业"},
            ]},
            {"name": "甲苯", "symbol": "C7H8", "limits": [
                {"level": "通用", "value": 15, "unit": "mg/m³", "desc": "印刷工业"},
            ]},
            {"name": "二甲苯", "symbol": "C8H10", "limits": [
                {"level": "通用", "value": 20, "unit": "mg/m³", "desc": "印刷工业"},
            ]},
        ]
    },
    "GB 41617-2022": {  # 矿物棉工业大气污染物排放标准
        "factors": [
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 30, "unit": "mg/m³", "desc": "矿物棉工业"},
                {"level": "新建", "value": 20, "unit": "mg/m³", "desc": "矿物棉工业"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "现有", "value": 200, "unit": "mg/m³", "desc": "矿物棉工业"},
                {"level": "新建", "value": 100, "unit": "mg/m³", "desc": "矿物棉工业"},
            ]},
            {"name": "氮氧化物", "symbol": "NOx", "limits": [
                {"level": "现有", "value": 400, "unit": "mg/m³", "desc": "矿物棉工业"},
                {"level": "新建", "value": 300, "unit": "mg/m³", "desc": "矿物棉工业"},
            ]},
            {"name": "甲醛", "symbol": "HCHO", "limits": [
                {"level": "通用", "value": 5.0, "unit": "mg/m³", "desc": "矿物棉工业"},
            ]},
        ]
    },
    "GB 41618-2022": {  # 石灰、电石工业大气污染物排放标准
        "factors": [
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 30, "unit": "mg/m³", "desc": "石灰电石工业"},
                {"level": "新建", "value": 20, "unit": "mg/m³", "desc": "石灰电石工业"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "现有", "value": 200, "unit": "mg/m³", "desc": "石灰电石工业"},
                {"level": "新建", "value": 100, "unit": "mg/m³", "desc": "石灰电石工业"},
            ]},
            {"name": "氮氧化物", "symbol": "NOx", "limits": [
                {"level": "现有", "value": 400, "unit": "mg/m³", "desc": "石灰电石工业"},
                {"level": "新建", "value": 300, "unit": "mg/m³", "desc": "石灰电石工业"},
            ]},
        ]
    },
    "GB 9078-1996": {  # 工业炉窑大气污染物排放标准
        "factors": [
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "一级", "value": 100, "unit": "mg/m³", "desc": "工业炉窑"},
                {"level": "二级", "value": 150, "unit": "mg/m³", "desc": "工业炉窑"},
                {"level": "三级", "value": 200, "unit": "mg/m³", "desc": "工业炉窑"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "一级", "value": 100, "unit": "mg/m³", "desc": "工业炉窑"},
                {"level": "二级", "value": 300, "unit": "mg/m³", "desc": "工业炉窑"},
                {"level": "三级", "value": 850, "unit": "mg/m³", "desc": "工业炉窑"},
            ]},
            {"name": "氟及其化合物", "symbol": "F", "limits": [
                {"level": "一级", "value": 6, "unit": "mg/m³", "desc": "工业炉窑"},
                {"level": "二级", "value": 15, "unit": "mg/m³", "desc": "工业炉窑"},
            ]},
            {"name": "铅及其化合物", "symbol": "Pb", "limits": [
                {"level": "一级", "value": 0.9, "unit": "mg/m³", "desc": "工业炉窑"},
                {"level": "二级", "value": 5.0, "unit": "mg/m³", "desc": "工业炉窑"},
            ]},
        ]
    },
    "GB 16171-1996": {  # 炼焦炉大气污染物排放标准
        "factors": [
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "一级", "value": 50, "unit": "mg/m³", "desc": "炼焦炉"},
                {"level": "二级", "value": 100, "unit": "mg/m³", "desc": "炼焦炉"},
                {"level": "三级", "value": 150, "unit": "mg/m³", "desc": "炼焦炉"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "一级", "value": 100, "unit": "mg/m³", "desc": "炼焦炉"},
                {"level": "二级", "value": 200, "unit": "mg/m³", "desc": "炼焦炉"},
                {"level": "三级", "value": 300, "unit": "mg/m³", "desc": "炼焦炉"},
            ]},
            {"name": "苯并[a]芘", "symbol": "BaP", "limits": [
                {"level": "一级", "value": 0.0025, "unit": "mg/m³", "desc": "炼焦炉"},
                {"level": "二级", "value": 0.0040, "unit": "mg/m³", "desc": "炼焦炉"},
            ]},
            {"name": "苯可溶物", "symbol": "BSE", "limits": [
                {"level": "一级", "value": 0.6, "unit": "mg/m³", "desc": "炼焦炉"},
                {"level": "二级", "value": 1.0, "unit": "mg/m³", "desc": "炼焦炉"},
            ]},
        ]
    },
    "GB 14374-1993": {  # 航天推进剂水污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "一级", "value": 100, "unit": "mg/L", "desc": "航天推进剂"},
                {"level": "二级", "value": 150, "unit": "mg/L", "desc": "航天推进剂"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "一级", "value": 70, "unit": "mg/L", "desc": "航天推进剂"},
                {"level": "二级", "value": 200, "unit": "mg/L", "desc": "航天推进剂"},
            ]},
            {"name": "偏二甲肼", "symbol": "UDMH", "limits": [
                {"level": "一级", "value": 0.5, "unit": "mg/L", "desc": "航天推进剂"},
                {"level": "二级", "value": 1.0, "unit": "mg/L", "desc": "航天推进剂"},
            ]},
        ]
    },
    "GB 18596-2001": {  # 畜禽养殖业污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "通用", "value": 400, "unit": "mg/L", "desc": "畜禽养殖"},
            ]},
            {"name": "生化需氧量", "symbol": "BOD5", "limits": [
                {"level": "通用", "value": 150, "unit": "mg/L", "desc": "畜禽养殖"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "通用", "value": 80, "unit": "mg/L", "desc": "畜禽养殖"},
            ]},
            {"name": "总磷", "symbol": "TP", "limits": [
                {"level": "通用", "value": 8.0, "unit": "mg/L", "desc": "畜禽养殖"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "通用", "value": 200, "unit": "mg/L", "desc": "畜禽养殖"},
            ]},
        ]
    },
    "GB 26877-2011": {  # 汽车维修业水污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 80, "unit": "mg/L", "desc": "汽车维修业"},
                {"level": "间接排放", "value": 200, "unit": "mg/L", "desc": "汽车维修业"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "直接排放", "value": 50, "unit": "mg/L", "desc": "汽车维修业"},
                {"level": "间接排放", "value": 100, "unit": "mg/L", "desc": "汽车维修业"},
            ]},
            {"name": "石油类", "symbol": "Petroleum", "limits": [
                {"level": "直接排放", "value": 3, "unit": "mg/L", "desc": "汽车维修业"},
                {"level": "间接排放", "value": 10, "unit": "mg/L", "desc": "汽车维修业"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "直接排放", "value": 10, "unit": "mg/L", "desc": "汽车维修业"},
                {"level": "间接排放", "value": 25, "unit": "mg/L", "desc": "汽车维修业"},
            ]},
        ]
    },
    "GB 12523-2025": {  # 建筑施工噪声排放标准
        "factors": [
            {"name": "施工噪声", "symbol": "Noise", "limits": [
                {"level": "昼间", "value": 70, "unit": "dB(A)", "desc": "建筑施工场界"},
                {"level": "夜间", "value": 55, "unit": "dB(A)", "desc": "建筑施工场界"},
            ]},
        ]
    },
    "GB 4915-1996": {  # 水泥厂大气污染物排放标准
        "factors": [
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "一级", "value": 100, "unit": "mg/m³", "desc": "水泥厂"},
                {"level": "二级", "value": 150, "unit": "mg/m³", "desc": "水泥厂"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "一级", "value": 200, "unit": "mg/m³", "desc": "水泥厂"},
                {"level": "二级", "value": 400, "unit": "mg/m³", "desc": "水泥厂"},
            ]},
            {"name": "氮氧化物", "symbol": "NOx", "limits": [
                {"level": "一级", "value": 400, "unit": "mg/m³", "desc": "水泥厂"},
                {"level": "二级", "value": 800, "unit": "mg/m³", "desc": "水泥厂"},
            ]},
        ]
    },
    "GB 29495-2013": {  # 电子玻璃工业大气污染物排放标准
        "factors": [
            {"name": "颗粒物", "symbol": "PM", "limits": [
                {"level": "现有", "value": 50, "unit": "mg/m³", "desc": "电子玻璃工业"},
                {"level": "新建", "value": 30, "unit": "mg/m³", "desc": "电子玻璃工业"},
            ]},
            {"name": "二氧化硫", "symbol": "SO2", "limits": [
                {"level": "现有", "value": 400, "unit": "mg/m³", "desc": "电子玻璃工业"},
                {"level": "新建", "value": 200, "unit": "mg/m³", "desc": "电子玻璃工业"},
            ]},
            {"name": "氮氧化物", "symbol": "NOx", "limits": [
                {"level": "现有", "value": 700, "unit": "mg/m³", "desc": "电子玻璃工业"},
                {"level": "新建", "value": 500, "unit": "mg/m³", "desc": "电子玻璃工业"},
            ]},
            {"name": "氯化氢", "symbol": "HCl", "limits": [
                {"level": "通用", "value": 30, "unit": "mg/m³", "desc": "电子玻璃工业"},
            ]},
        ]
    },
    "GB 20425-2006": {  # 皂素工业水污染物排放标准
        "factors": [
            {"name": "化学需氧量", "symbol": "COD", "limits": [
                {"level": "直接排放", "value": 100, "unit": "mg/L", "desc": "皂素工业"},
                {"level": "间接排放", "value": 300, "unit": "mg/L", "desc": "皂素工业"},
            ]},
            {"name": "悬浮物", "symbol": "SS", "limits": [
                {"level": "直接排放", "value": 70, "unit": "mg/L", "desc": "皂素工业"},
                {"level": "间接排放", "value": 150, "unit": "mg/L", "desc": "皂素工业"},
            ]},
            {"name": "氨氮", "symbol": "NH3-N", "limits": [
                {"level": "直接排放", "value": 15, "unit": "mg/L", "desc": "皂素工业"},
                {"level": "间接排放", "value": 30, "unit": "mg/L", "desc": "皂素工业"},
            ]},
            {"name": "总磷", "symbol": "TP", "limits": [
                {"level": "直接排放", "value": 0.5, "unit": "mg/L", "desc": "皂素工业"},
                {"level": "间接排放", "value": 1.0, "unit": "mg/L", "desc": "皂素工业"},
            ]},
        ]
    },
}


def supplement():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 因子缓存: symbol -> factor_id
    factor_cache = {}
    for row in c.execute("SELECT id, symbol FROM pollution_factors"):
        factor_cache[row[1]] = row[0]

    supplemented = 0
    skipped = []

    for std_num, data in SUPPLEMENT_LIMITS.items():
        # 查找数据库中该标准
        rows = c.execute(
            "SELECT id, title, standard_type FROM standards WHERE standard_number = ?",
            (std_num,)
        ).fetchall()
        if not rows:
            skipped.append((std_num, "数据库中无此标准"))
            continue

        for std_id, std_title, std_type in rows:
            # 检查是否已有限值
            existing = c.execute(
                "SELECT COUNT(*) FROM pollution_limits WHERE standard_title = ?",
                (std_title,)
            ).fetchone()[0]
            if existing > 0:
                skipped.append((std_num, f"已有{existing}条限值，跳过"))
                continue

            # 构建 pollution_factors JSON
            pf_json = []
            for f in data["factors"]:
                symbol = f["symbol"]
                pf_json.append({"name": f["name"], "symbol": symbol, "limits": f["limits"]})

                # 写入 pollution_factors 表（如不存在）
                if symbol not in factor_cache:
                    c.execute(
                        "INSERT INTO pollution_factors (name, symbol, unit, created_at) VALUES (?, ?, ?, ?)",
                        (f["name"], symbol, f["limits"][0]["unit"], now)
                    )
                    factor_cache[symbol] = c.lastrowid
                factor_id = factor_cache[symbol]

                # 写入 pollution_limits 表
                for limit in f["limits"]:
                    c.execute("""
                        INSERT INTO pollution_limits
                            (factor_id, standard_title, limit_value, unit, standard_type, description, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        factor_id, std_title, limit["value"], limit["unit"],
                        std_type or "国家标准", f"{limit['level']} - {limit['desc']}", now,
                    ))

            # 更新 standards 表的 pollution_factors 字段
            c.execute(
                "UPDATE standards SET pollution_factors = ? WHERE id = ?",
                (json.dumps(pf_json, ensure_ascii=False), std_id)
            )
            supplemented += 1
            print(f"  ✓ {std_num} | {std_title[:30]} | {len(data['factors'])}个因子")

    conn.commit()

    # 统计
    total_factors = c.execute("SELECT COUNT(*) FROM pollution_factors").fetchone()[0]
    total_limits = c.execute("SELECT COUNT(*) FROM pollution_limits").fetchone()[0]
    standards_with_limits = c.execute(
        "SELECT COUNT(DISTINCT standard_title) FROM pollution_limits"
    ).fetchone()[0]

    print(f"\n{'='*60}")
    print(f"补充完成!")
    print(f"  本次补充标准数: {supplemented}")
    print(f"  污染因子总数: {total_factors}")
    print(f"  污染限值总数: {total_limits}")
    print(f"  含限值的标准数: {standards_with_limits}")
    if skipped:
        print(f"\n  跳过 {len(skipped)} 项:")
        for s in skipped:
            print(f"    {s[0]}: {s[1]}")
    print(f"{'='*60}")

    conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("补充排放标准的污染因子限值数据")
    print(f"数据来源: 生态环境部 https://www.mee.gov.cn/ywgz/fgbz/bz/")
    print(f"待补充标准数: {len(SUPPLEMENT_LIMITS)}")
    print("=" * 60)
    supplement()
