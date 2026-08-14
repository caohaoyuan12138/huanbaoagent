"""
数据库迁移脚本 — 添加 Modbus HJ212 相关字段
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app.db.database import engine


def migrate():
    with engine.connect() as conn:
        # 检查并添加 devices 表的新字段
        conn.execute(text("""
            ALTER TABLE devices ADD COLUMN mn VARCHAR(50)
        """))
        print("已添加 devices.mn 字段")

        conn.execute(text("""
            ALTER TABLE devices ADD COLUMN ip_address VARCHAR(50)
        """))
        print("已添加 devices.ip_address 字段")

        conn.execute(text("""
            ALTER TABLE devices ADD COLUMN port INTEGER DEFAULT 8000
        """))
        print("已添加 devices.port 字段")

        conn.execute(text("""
            ALTER TABLE devices ADD COLUMN timeout FLOAT DEFAULT 5.0
        """))
        print("已添加 devices.timeout 字段")

        # 检查并添加 device_readings 表的新字段
        conn.execute(text("""
            ALTER TABLE device_readings ADD COLUMN raw_data TEXT
        """))
        print("已添加 device_readings.raw_data 字段")

        conn.execute(text("""
            ALTER TABLE device_readings ADD COLUMN data_type VARCHAR(20) DEFAULT 'direct'
        """))
        print("已添加 device_readings.data_type 字段")

        conn.commit()
        print("\n数据库迁移完成!")


if __name__ == "__main__":
    migrate()
