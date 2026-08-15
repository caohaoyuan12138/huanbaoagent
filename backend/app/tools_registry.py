# -*- coding: utf-8 -*-
"""
工具注册表 — 所有工具的定义、描述、参数schema
供LLM理解和选择工具使用
"""
from typing import Dict, Any, List, Optional

# ──────────────────────────────────────────
# 工具注册表
# ──────────────────────────────────────────
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "search_standards": {
        "name": "search_standards",
        "description": "搜索环保标准，支持按名称/编号/行业/标准类型模糊搜索。返回标准列表和污染因子限值。",
        "category": "knowledge",
        "parameters": {
            "query": {
                "type": "string",
                "description": "搜索关键词，如'大气污染物'、'GB 16297'、'化工'"
            }
        },
        "examples": [
            "查询大气污染物综合排放标准",
            "搜索GB 16297标准"
        ]
    },
    "get_factor_limits": {
        "name": "get_factor_limits",
        "description": "查询特定污染因子的全部排放限值，包含所有适用标准和限值数值。",
        "category": "knowledge",
        "parameters": {
            "factor_name": {
                "type": "string",
                "description": "污染因子名称或符号，如'化学需氧量'、'COD'、'颗粒物'"
            }
        },
        "examples": [
            "查询COD的排放限值",
            "颗粒物排放限值"
        ]
    },
    "compare_standards": {
        "name": "compare_standards",
        "description": "对比多个环保标准之间的差异，包括限值对比、适用行业对比、标准层级对比。",
        "category": "knowledge",
        "parameters": {
            "standard_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "要对比的标准ID列表"
            }
        },
        "examples": [
            "对比GB 16297和GB 31570",
            "比较不同行业的废水排放标准"
        ]
    },
    "analyze_device": {
        "name": "analyze_device",
        "description": "分析监测设备数据，包括统计概览、异常检测、趋势分析、超限预测。返回设备排放数据和AI建议。",
        "category": "data_analysis",
        "parameters": {
            "device_id": {
                "type": "integer",
                "description": "设备ID，默认1"
            }
        },
        "examples": [
            "分析1号设备的排放数据",
            "设备2的异常检测"
        ]
    },
    "check_exceedances": {
        "name": "check_exceedances",
        "description": "检查过去指定时间内的超标记录，返回超标设备、因子、数值和时间。",
        "category": "data_analysis",
        "parameters": {
            "hours": {
                "type": "integer",
                "description": "检查过去多少小时的记录，默认24",
                "default": 24
            }
        },
        "examples": [
            "过去24小时超标记录",
            "检查最近48小时异常"
        ]
    },
    "generate_report": {
        "name": "generate_report",
        "description": "根据模板生成环保报告，支持日常巡检、超标分析、合规检查、年度报告等类型。",
        "category": "report",
        "parameters": {
            "template_type": {
                "type": "string",
                "enum": ["daily_inspection", "exceed_analysis", "compliance_check", "annual_report"],
                "description": "报告模板类型",
                "default": "daily_inspection"
            },
            "params": {
                "type": "object",
                "description": "报告参数，如开始/结束日期、设备ID列表等"
            }
        },
        "examples": [
            "生成今日巡检报告",
            "生成超标分析报告"
        ]
    },
    "search_news": {
        "name": "search_news",
        "description": "搜索环保新闻资讯，包括政策法规、行业标准、行业动态、企业新闻等。",
        "category": "information",
        "parameters": {
            "keyword": {
                "type": "string",
                "description": "搜索关键词"
            }
        },
        "examples": [
            "最新环保政策法规",
            "化工行业排放新标准新闻"
        ]
    },
    "search_regulation": {
        "name": "search_regulation",
        "description": "查询化工园区入驻公约和条款，包括入驻要求、禁止/限制产业、环保责任等。",
        "category": "knowledge",
        "parameters": {
            "query": {
                "type": "string",
                "description": "查询关键词，如'入驻要求'、'禁止产业'、'环保责任'"
            }
        },
        "examples": [
            "查询园区入驻环保要求",
            "禁止入驻的产业类型"
        ]
    },
    "web_search": {
        "name": "web_search",
        "description": "搜索网络获取最新环保政策、标准和资讯。当知识库中没有相关信息时使用。",
        "category": "information",
        "parameters": {
            "query": {
                "type": "string",
                "description": "搜索查询"
            },
            "max_results": {
                "type": "integer",
                "description": "最大结果数，默认5",
                "default": 5
            }
        },
        "examples": [
            "搜索最新VOCs排放标准政策",
            "2024年环保法规更新"
        ]
    },
    "crawl_standards": {
        "name": "crawl_standards",
        "description": "从生态环境部、国家标准公开等平台爬取最新环保标准并入库。⚠️ 此操作会写入数据库，需谨慎使用。",
        "category": "data_management",
        "parameters": {
            "source": {
                "type": "string",
                "enum": ["auto", "mee", "std"],
                "description": "数据来源：auto=自动选择, mee=生态环境部, std=国家标准全文公开"
            },
            "limit": {
                "type": "integer",
                "description": "最大爬取数量，默认20",
                "default": 20
            }
        },
        "examples": [
            "从生态环境部爬取新标准",
            "采集国标平台最新标准"
        ]
    },
    "upload_data": {
        "name": "upload_data",
        "description": "处理用户上传的CSV/JSON数据文件，导入为设备监测记录。⚠️ 此操作会写入数据库，需谨慎使用。",
        "category": "data_management",
        "parameters": {
            "content": {
                "type": "string",
                "description": "文件内容（CSV或JSON格式）"
            },
            "filename": {
                "type": "string",
                "description": "文件名"
            },
            "device_name": {
                "type": "string",
                "description": "关联设备名称"
            },
            "factor": {
                "type": "string",
                "description": "监测因子名称"
            }
        },
        "examples": [
            "上传监测数据文件",
            "导入CSV格式的排放数据"
        ]
    },
}


def get_tool_schema() -> Dict[str, Any]:
    """返回完整的工具Schema，供LLM理解"""
    return {
        "tools": TOOL_REGISTRY,
        "categories": list(set(t["category"] for t in TOOL_REGISTRY.values())),
        "tool_count": len(TOOL_REGISTRY),
    }


def get_tool_descriptions() -> str:
    """返回简洁的工具描述文本，适合放入prompt"""
    lines = []
    for name, info in TOOL_REGISTRY.items():
        lines.append(f"  {name}: {info['description']}")
    return "\n".join(lines)


def get_tool_names() -> List[str]:
    """返回所有工具名称列表"""
    return list(TOOL_REGISTRY.keys())
