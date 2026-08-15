from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging
import time

logger = logging.getLogger(__name__)

SQLALCHEMY_DATABASE_URL = "sqlite:///./env_agent.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def init_db():
    from app.db.models import Base
    Base.metadata.create_all(bind=engine)
    # 迁移: 为 devices 表添加健康指标列
    _migrate_devices_table()
    # 迁移: 创建 sites 表
    _migrate_sites_table()
    # 创建关键索引加速查询
    _create_indexes()


def _migrate_devices_table():
    """迁移: 添加设备健康指标列"""
    with engine.connect() as conn:
        for col_sql in [
            "ALTER TABLE devices ADD COLUMN site_id INTEGER",
            "ALTER TABLE devices ADD COLUMN last_seen DATETIME",
            "ALTER TABLE devices ADD COLUMN latency_ms FLOAT",
            "ALTER TABLE devices ADD COLUMN uptime_percent FLOAT DEFAULT 0.0",
            "ALTER TABLE devices ADD COLUMN total_readings INTEGER DEFAULT 0",
        ]:
            try:
                conn.execute(text(col_sql))
            except Exception:
                pass  # 列已存在则忽略
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_devices_site ON devices(site_id)"))
        conn.commit()


def _migrate_sites_table():
    """迁移: 创建站点表"""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER,
                name VARCHAR(200) NOT NULL,
                code VARCHAR(50),
                address VARCHAR(500),
                parent_id INTEGER,
                contact_name VARCHAR(100),
                contact_phone VARCHAR(20),
                status VARCHAR(20) DEFAULT 'active',
                created_at DATETIME NOT NULL
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sites_tenant ON sites(tenant_id)"))
        conn.commit()


def _create_indexes():
    """创建额外的数据库索引"""
    indexes = [
        # 设备读数常用查询索引
        "CREATE INDEX IF NOT EXISTS idx_readings_device_tenant ON device_readings(device_id, tenant_id)",
        "CREATE INDEX IF NOT EXISTS idx_readings_factor_ts ON device_readings(factor, timestamp)",
        # 标准表索引
        "CREATE INDEX IF NOT EXISTS idx_standards_number ON standards(standard_number)",
        "CREATE INDEX IF NOT EXISTS idx_standards_title ON standards(title)",
        "CREATE INDEX IF NOT EXISTS idx_standards_category ON standards(category)",
        # 污染因子索引
        "CREATE INDEX IF NOT EXISTS idx_factors_symbol ON pollution_factors(symbol)",
        # 污染限值索引
        "CREATE INDEX IF NOT EXISTS idx_limits_standard ON pollution_limits(standard_title)",
        "CREATE INDEX IF NOT EXISTS idx_limits_factor ON pollution_limits(factor_id)",
        # 新闻索引
        "CREATE INDEX IF NOT EXISTS idx_news_title ON news_items(title)",
        "CREATE INDEX IF NOT EXISTS idx_news_published ON news_items(published_at)",
        # 向量记忆索引
        "CREATE INDEX IF NOT EXISTS idx_semantic_session ON semantic_memories(session_id, memory_type)",
        # 告警索引
        "CREATE INDEX IF NOT EXISTS idx_alerts_device ON alerts(device_id)",
        "CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at)",
        # 合规报告索引（tenant_id 列可能不存在）
    ]
    with engine.connect() as conn:
        for sql in indexes:
            try:
                conn.execute(text(sql))
            except Exception as e:
                logger.warning("索引创建失败 %s: %s", sql[:50], str(e)[:50])
        conn.commit()
