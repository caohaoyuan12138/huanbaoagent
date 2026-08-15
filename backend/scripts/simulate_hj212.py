"""
HJ212 协议模拟器 — 模拟真实 HJ212-2017 监测设备
用于测试系统的 HJ212 数据接收能力
用法: python simulate_hj212.py
"""
import sys
import os
import time
import random
import socket
import struct
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)

# 本地回环地址作为模拟设备地址
SIMULATOR_IP = "127.0.0.1"
SERVER_PORT = 8541  # 模拟 HJ212 服务端端口


class HJ212Simulator:
    """模拟 HJ212-2017 协议的监测设备"""

    def __init__(self, mn, ip, port=8000):
        self.mn = mn
        self.ip = ip
        self.port = port
        self.client = None

    def connect(self):
        """建立 TCP 连接（模拟设备连接平台）"""
        try:
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.settimeout(5.0)
            self.client.connect((self.ip, self.port))
            logger.info(f"HJ212设备连接成功: MN={self.mn}, {self.ip}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"HJ212连接失败: {e}")
            return False

    def _calc_crc16(self, data: bytes) -> int:
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    def _encode_hj212(self, data_str: str) -> bytes:
        """编码 HJ212 帧"""
        data_bytes = data_str.encode('gbk')
        header = f"##{self.mn}"
        header_bytes = header.encode('gbk')
        crc = self._calc_crc16(header_bytes + data_bytes)
        crc_hex = format(crc, '04X')
        frame = f"{header}{crc_hex}{len(data_bytes):04X}{data_str}"
        return frame.encode('gbk') + b'\r\n'

    def send_data(self, factors: dict):
        """发送 HJ212 数据帧"""
        if not self.client:
            return False

        # 构建数据内容
        data_parts = []
        for key, value in factors.items():
            data_parts.append(f"{key}={value:.2f}")

        data_str = "&".join(data_parts)
        cmd = f"CN=2011&MN={self.mn}&{data_str}"

        try:
            self.client.sendall(self._encode_hj212(cmd))
            logger.info(f"HJ212数据上报: MN={self.mn}, 数据={data_str}")
            return True
        except Exception as e:
            logger.error(f"发送失败: {e}")
            return False

    def close(self):
        if self.client:
            self.client.close()


def main():
    """
    HJ212 设备模拟器

    此脚本模拟了 HJ212 协议设备向环保平台发送数据。
    实际使用时，只需将 ip/port 指向本系统的 HJ212 接收端口即可。

    当前配置：模拟 3 个设备分别上报不同因子
    """
    logger.info("=" * 50)
    logger.info("HJ212 设备模拟器启动")
    logger.info(f"目标地址: {SIMULATOR_IP}:{SERVER_PORT}")
    logger.info("=" * 50)
    logger.info("")
    logger.info("说明: 此脚本模拟 HJ212 设备上报数据")
    logger.info("如需连接真实设备，请将设备的 IP/端口 配置为本机地址")
    logger.info("")

    devices = [
        HJ212Simulator("01001001", SIMULATOR_IP, SERVER_PORT),   # 废气
        HJ212Simulator("01002001", SIMULATOR_IP, SERVER_PORT),   # 废水
        HJ212Simulator("01003001", SIMULATOR_IP, SERVER_PORT),   # 噪声
    ]

    # 连接所有设备
    connected = []
    for dev in devices:
        if dev.connect():
            connected.append(dev)

    if not connected:
        logger.error("所有设备连接失败，请确认服务是否启动")
        return

    logger.info(f"成功连接 {len(connected)}/{len(devices)} 个设备\n")

    # 因子基准值
    factor_base = {
        "01001001": {"VOCs": 25.0, "SO2": 30.0, "NOx": 40.0},
        "01002001": {"COD": 35.0, "NH3-N": 8.0, "TP": 0.5},
        "01003001": {"噪声": 55.0},
    }

    try:
        while True:
            for dev in connected:
                base = factor_base.get(dev.mn, {})
                factors = {}
                for k, v in base.items():
                    # 随机波动 ±3%
                    factors[k] = v * (1 + random.gauss(0, 0.015))

                dev.send_data(factors)

            time.sleep(30)  # 每30秒上报一次
    except KeyboardInterrupt:
        logger.info("\n模拟器已停止")
    finally:
        for dev in connected:
            dev.close()


if __name__ == "__main__":
    main()
