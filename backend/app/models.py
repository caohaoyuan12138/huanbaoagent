from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


class StandardType(str, Enum):
    NATIONAL = "national"       # 国标 GB
    INDUSTRY = "industry"       # 行标 HJ/SY 等
    LOCAL = "local"             # 地标 DB
    INTERNATIONAL = "international"  # 国际标准
    ENTERPRISE = "enterprise"   # 企标


class ReportType(str, Enum):
    DAILY_INSPECTION = "daily_inspection"      # 日常巡查报告
    EXCEED_ANALYSIS = "exceed_analysis"        # 超标分析报告
    COMPLIANCE_CHECK = "compliance_check"      # 合规排查报告
    ANNUAL_REPORT = "annual_report"            # 年度/季度报告


class PollutionFactor(str, Enum):
    COD = "cod"                  # 化学需氧量
    NH3N = "nh3n"               # 氨氮
    VOCs = "vocs"               # 挥发性有机物
    SO2 = "so2"                 # 二氧化硫
    NOX = "nox"                 # 氮氧化物
    PM = "pm"                   # 颗粒物
    THOM = "thom"               # 总汞及其化合物
    FENOL = "fenol"             # 苯酚
    AMMONIA = "ammonia"         # 氨


class DeviceDataPoint(BaseModel):
    timestamp: datetime
    value: float
    unit: str
    quality: str = "good"  # good/suspicious/bad


class DeviceReading(BaseModel):
    device_id: str
    factor: str
    value: float
    unit: str
    timestamp: datetime
    status: str = "normal"  # normal/warning/exceed


class NewsItem(BaseModel):
    id: str
    title: str
    summary: str
    source: str
    url: str
    published_at: datetime
    tags: List[str] = []
    category: str = "industry"  # industry/policy/news/standard


class AgentMessage(BaseModel):
    role: str  # user/assistant
    content: str
    timestamp: Optional[datetime] = None
