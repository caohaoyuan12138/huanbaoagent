"""
设备数据模拟器 — 用于测试和演示
模拟真实环境监测设备通过不同协议发送数据
用法: python simulate_devices.py
"""
import sys
import os
import time
import random
import asyncio
import json
import requests
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"


def get_devices():
    """获取所有设备"""
    resp = requests.get(f"{BASE_URL}/api/devices/devices")
    return resp.json().get("value", [])


def get_device_readings(device_id):
    """获取设备历史读数（用于计算趋势）"""
    try:
        resp = requests.get(
            f"{BASE_URL}/api/devices/devices/{device_id}/readings",
            params={"hours": 1, "page_size": 100}
        )
        data = resp.json()
        readings = data.get("value", []) if isinstance(data, dict) else data
        return [r["value"] for r in readings] if readings else []
    except:
        return []


def simulate_modbus_device(device, last_values=None):
    """模拟 Modbus/HJ212 设备上报数据"""
    if last_values is None:
        last_values = {}

    factor = device["factor"]
    unit = device["unit"]
    base_value = {
        "VOCs": 25.0, "COD": 35.0, "NH3-N": 8.0,
        "氨氮": 8.0, "噪声": 55.0, "颗粒物": 15.0,
        "SO2": 30.0, "NOx": 40.0, "烟尘": 10.0,
    }.get(factor, 50.0)

    # 基于历史数据做随机游走
    if last_values and len(last_values) > 0:
        current = last_values[-1]
    else:
        current = base_value

    # 随机波动 ±5%
    new_value = current * (1 + random.gauss(0, 0.02))
    new_value = max(0, new_value)

    # 偶尔制造超标
    if random.random() < 0.03:
        new_value = base_value * random.uniform(1.5, 2.5)

    # 判断状态
    limit_map = {"VOCs": 50, "COD": 50, "NH3-N": 15, "氨氮": 15, "噪声": 60, "颗粒物": 30}
    limit = limit_map.get(factor, 50)
    if new_value > limit:
        status = "exceed"
    elif new_value > limit * 0.8:
        status = "warning"
    else:
        status = "normal"

    # 批量上报
    payload = [{
        "factor": factor,
        "value": round(new_value, 2),
        "unit": unit,
        "status": status,
        "timestamp": datetime.now().isoformat(),
    }]

    resp = requests.post(
        f"{BASE_URL}/api/devices/devices/{device['id']}/readings/batch",
        json=payload
    )
    return new_value


def simulate_mqtt_device(device, last_values=None):
    """模拟 MQTT 设备上报"""
    return simulate_modbus_device(device, last_values)


def main():
    print("=" * 60)
    print("  环保设备数据模拟器")
    print("=" * 60)
    print(f"目标服务: {BASE_URL}")
    print()

    # 检查服务
    try:
        requests.get(f"{BASE_URL}/api/health", timeout=3)
    except:
        print("❌ 后端服务未启动，请先运行: python -m uvicorn main:app --port 8000")
        return

    devices = get_devices()
    if not devices:
        print("❌ 暂无设备，请先添加设备")
        return

    print(f"✅ 已连接，共 {len(devices)} 个设备\n")
    for d in devices:
        status_icon = "🟢" if d["status"] == "online" else "⚫"
        print(f"  {status_icon} [{d['id']}] {d['name']} | {d['factor']} ({d['unit']}) | {d['protocol']}")
    print()

    # 初始化历史值
    history = {d["id"]: [] for d in devices}

    print("开始模拟数据上报... (Ctrl+C 停止)\n")
    try:
        while True:
            for device in devices:
                if device["status"] != "online":
                    continue

                last_vals = history.get(device["id"], [])
                new_val = simulate_modbus_device(device, last_vals[-10:] if last_vals else None)
                history[device["id"]].append(new_val)
                if len(history[device["id"]]) > 100:
                    history[device["id"]] = history[device["id"]][-100:]

                # 只打印在线设备
                if device["status"] == "online":
                    limit_map = {"VOCs": 50, "COD": 50, "NH3-N": 15, "氨氮": 15, "噪声": 60}
                    limit = limit_map.get(device["factor"], 50)
                    status_icon = "🔴" if new_val > limit else "🟢" if new_val > limit * 0.8 else "⚪"
                    print(f"  {status_icon} {device['name']}: {new_val:.2f} {device['unit']} (限值: {limit})")

            time.sleep(30)  # 每30秒上报一次
    except KeyboardInterrupt:
        print("\n\n模拟器已停止")


if __name__ == "__main__":
    main()
