from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean, create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./env_agent.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
Base = declarative_base()


class Standard(Base):
    __tablename__ = "standards"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    standard_number = Column(String(100), default="")  # 标准编号，如 GB 16297-1996
    standard_type = Column(String(50), nullable=False)
    industry = Column(String(200), default="通用行业")
    category = Column(String(100), default="")  # 废气/废水/固废/土壤/噪声/地下水等
    sub_category = Column(String(100), default="")  # 细分领域：大气综合/污水排放/地表水等
    pollution_factors = Column(JSON, default=[])
    publish_date = Column(DateTime, default=datetime.now)
    implement_date = Column(DateTime)
    content = Column(Text)
    source_url = Column(String(500))
    pdf_url = Column(String(500), default="")  # PDF下载链接
    status = Column(String(20), default="active")  # active/obsolete
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class PollutionFactor(Base):
    __tablename__ = "pollution_factors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    symbol = Column(String(50), nullable=False, unique=True)
    unit = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.now)


class PollutionLimit(Base):
    __tablename__ = "pollution_limits"
    id = Column(Integer, primary_key=True, index=True)
    factor_id = Column(Integer, nullable=False)
    standard_title = Column(String(200), nullable=False)
    limit_value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    standard_type = Column(String(50), nullable=False)
    description = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)


class EnterpriseStandard(Base):
    __tablename__ = "enterprise_standards"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    industry = Column(String(100))
    pollution_factor = Column(String(50))
    limit_value = Column(Float)
    unit = Column(String(20))
    description = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)


class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    contact_name = Column(String(100))
    contact_phone = Column(String(20))
    contact_email = Column(String(200))
    address = Column(String(500))
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.now)


class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    name = Column(String(200), nullable=False)
    factor = Column(String(50), nullable=False)
    unit = Column(String(20), nullable=False)
    location = Column(String(200))
    protocol = Column(String(50), default="mqtt")
    topic = Column(String(200))
    mn = Column(String(50), nullable=True)
    ip_address = Column(String(50), nullable=True)
    port = Column(Integer, default=8000)
    timeout = Column(Float, default=5.0)
    status = Column(String(20), default="offline")
    created_at = Column(DateTime, default=datetime.now)


class DeviceReading(Base):
    __tablename__ = "device_readings"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=True)
    device_id = Column(Integer, nullable=False, index=True)
    factor = Column(String(50), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    status = Column(String(20), default="normal")
    raw_data = Column(Text, nullable=True)
    data_type = Column(String(20), default="direct")
    created_at = Column(DateTime, default=datetime.now)


class NewsItem(Base):
    __tablename__ = "news_items"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    summary = Column(String(2000))
    source = Column(String(100))
    url = Column(String(500))
    published_at = Column(DateTime, nullable=False)
    tags = Column(JSON, default=[])
    category = Column(String(20), default="industry")
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


class ReportTemplate(Base):
    __tablename__ = "report_templates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)
    description = Column(String(500))
    fields = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.now)


class ReportInstance(Base):
    __tablename__ = "report_instances"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=True)
    template_id = Column(Integer, nullable=False)
    params = Column(JSON)
    content = Column(Text)
    status = Column(String(20), default="generated")
    generated_at = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    meta_data = Column(JSON, default=dict)


class SemanticMemory(Base):
    __tablename__ = "semantic_memories"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    text = Column(Text, nullable=False)
    embedding_hash = Column(String(32))
    meta_data = Column(JSON, default=dict)
    created_at = Column(DateTime, nullable=False)
    access_count = Column(Integer, default=0)


class UsageStat(Base):
    __tablename__ = "usage_stats"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    query_type = Column(String(50))
    tool_used = Column(String(50))
    timestamp = Column(DateTime, nullable=False)
    feedback = Column(Integer)  # 1=helpful, -1=not_helpful


class AgentState(Base):
    __tablename__ = "agent_state"
    key = Column(String(100), primary_key=True)
    value = Column(Text)
    updated_at = Column(DateTime, nullable=False)


class CrawlLog(Base):
    __tablename__ = "crawl_logs"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(200), nullable=False)
    url = Column(String(500))
    title = Column(String(500))
    new_standards = Column(Integer, default=0)
    status = Column(String(20), default="success")
    crawled_at = Column(DateTime, nullable=False)


class ReportExportStat(Base):
    __tablename__ = "report_export_stats"
    id = Column(Integer, primary_key=True, index=True)
    report_instance_id = Column(Integer, nullable=False, index=True)
    format_type = Column(String(10), nullable=False)  # pdf / xlsx
    file_size = Column(Integer, default=0)
    success = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=True)
    device_id = Column(Integer, nullable=False, index=True)
    factor = Column(String(50), nullable=False)
    value = Column(Float, nullable=False)
    limit_value = Column(Float)
    unit = Column(String(20), nullable=False)
    severity = Column(String(20), default="warning")
    status = Column(String(20), default="unread")
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    device_ids = Column(JSON, default=[])
    standard_ids = Column(JSON, default=[])
    status = Column(String(20), default="pending")
    result_summary = Column(Text)
    passed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime)


class RegulationClause(Base):
    __tablename__ = "regulation_clauses"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(200), nullable=False)
    chapter = Column(String(200))
    article_no = Column(String(50))
    article_title = Column(String(500))
    content = Column(Text, nullable=False)
    keywords = Column(JSON, default=[])
    action_required = Column(JSON)
    platform_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)


class ToolPerformance(Base):
    """工具性能追踪 — 记录每次工具调用的成功/失败/延迟"""
    __tablename__ = "tool_performance"
    id = Column(Integer, primary_key=True, index=True)
    tool_name = Column(String(100), nullable=False, index=True)
    success = Column(Boolean, default=True)
    latency_ms = Column(Integer)
    error_message = Column(Text)
    query_preview = Column(String(200))
    session_id = Column(String(100))
    created_at = Column(DateTime, default=datetime.now)


class EvolutionSnapshot(Base):
    """进化快照 — 记录每次进化的状态和结果"""
    __tablename__ = "evolution_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    round_number = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    knowledge_added = Column(Integer, default=0)
    gaps_identified = Column(Integer, default=0)
    gaps_filled = Column(Integer, default=0)
    tool_calls_total = Column(Integer, default=0)
    tool_success_rate = Column(Float)
    new_patterns_discovered = Column(Integer, default=0)
    status = Column(String(20), default="completed")
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.now)
