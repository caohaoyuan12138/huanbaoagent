"""
Modbus HJ212 设备种子数据脚本
创建 3 个示例 Modbus 环境监测设备
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.database import SessionLocal
from app.db.models import Device


def seed_modbus_devices():
    db = SessionLocal()
    try:
        devices = [
            Device(
                name="废气排放监控-DA001",
                factor="VOCs",
                unit="mg/m³",
                location="厂区北侧废气排放口",
                protocol="modbus_hj212",
                topic="",
                mn="01001001",
                ip_address="192.168.1.100",
                port=8000,
                timeout=5.0,
                status="offline",
            ),
            Device(
                name="废水排放监控-WW001",
                factor="COD",
                unit="mg/L",
                location="厂区总排口废水监测站",
                protocol="modbus_hj212",
                topic="",
                mn="01002001",
                ip_address="192.168.1.101",
                port=8000,
                timeout=5.0,
                status="offline",
            ),
            Device(
                name="厂界噪声监控-NO001",
                factor="噪声",
                unit="dB(A)",
                location="厂区东边界噪声监测点",
                protocol="modbus_hj212",
                topic="",
                mn="01003001",
                ip_address="192.168.1.102",
                port=8000,
                timeout=5.0,
                status="offline",
            ),
        ]

        total_added = 0
        for d in devices:
            existing = db.query(Device).filter(Device.mn == d.mn).first()
            if not existing:
                db.add(d)
                total_added += 1
                print(f"新增设备: {d.name} (MN={d.mn})")
            else:
                print(f"设备已存在: {d.name} (MN={d.mn})")

        db.commit()
        print(f"\n种子完成: 新增 {total_added} 个 Modbus 设备")

        all_devices = db.query(Device).all()
        print(f"\n所有设备 ({len(all_devices)} 个):")
        for d in all_devices:
            print(f"  [{d.id}] {d.name} | 协议: {d.protocol} | MN: {d.mn or 'N/A'} | IP: {d.ip_address or 'N/A'}")

    except Exception as e:
        print(f"种子失败: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_modbus_devices()
