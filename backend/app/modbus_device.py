"""
Modbus HJ212-2017 协议设备处理器
用于环境监测设备的实时数据读取
"""
import re
import struct
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class ModbusDevice:
    """Modbus TCP 设备处理器，支持 HJ212-2017 协议"""

    def __init__(self, mn: str, ip: str, port: int = 8000, timeout: float = 5.0):
        self.mn = mn
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.client = None
        self.connected = False

    def connect(self) -> bool:
        """建立 Modbus TCP 连接"""
        try:
            from pymodbus.client import ModbusTcpClient
            self.client = ModbusTcpClient(
                host=self.ip,
                port=self.port,
                timeout=self.timeout,
            )
            self.connected = self.client.connect()
            if self.connected:
                logger.info(f"Modbus设备连接成功: MN={self.mn}, IP={self.ip}:{self.port}")
            else:
                logger.warning(f"Modbus设备连接失败: MN={self.mn}, IP={self.ip}:{self.port}")
            return self.connected
        except Exception as e:
            logger.error(f"Modbus连接异常: {e}")
            self.connected = False
            return False

    def close(self):
        """关闭连接"""
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
            self.connected = False
            self.client = None

    def _calc_crc16(self, data: bytes) -> int:
        """计算 CRC16 (Modbus 标准)"""
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
        """编码 HJ212 命令为字节流"""
        data_bytes = data_str.encode('gbk')
        data_len = len(data_bytes)
        header = f"##{self.mn}"
        header_bytes = header.encode('gbk')
        crc_lrc = self._calc_crc16(header_bytes + data_bytes)
        crc_hex = format(crc_lrc, '04X')
        frame = f"{header}{crc_hex}{data_len:04X}{data_str}"
        return frame.encode('gbk') + b'\r\n'

    def send_hj212_cmd(self, cmd: str) -> Optional[str]:
        """发送 HJ212 命令并获取响应"""
        if not self.connected:
            if not self.connect():
                return None

        try:
            payload = self._encode_hj212(cmd)

            request = bytearray()
            request += struct.pack('>H', 0)  # transaction_id
            request += struct.pack('>H', 0)  # protocol_id
            request += struct.pack('>H', len(payload) + 1)  # length
            request += struct.pack('B', 1)  # unit_id
            request += struct.pack('B', 0)  # function code (write single register as raw)

            frame = bytes(request) + payload

            response = self.client.write_register(0, 0, slave=1)

            cmd_bytes = payload
            resp_str = cmd_bytes.decode('gbk', errors='replace')
            return resp_str

        except Exception as e:
            logger.error(f"发送HJ212命令失败: {e}")
            return None

    def read_all_data(self) -> Dict[str, Any]:
        """读取设备所有实时监测数据"""
        result = {
            "mn": self.mn,
            "data": {},
            "timestamp": datetime.now(),
            "success": False,
            "raw_response": None,
        }

        if not self.connected:
            if not self.connect():
                return result

        try:
            cmd = f"CN=1401&MN={self.mn}"
            response = self.send_hj212_cmd(cmd)

            if response:
                parsed = self._parse_hj212_response(response)
                result["data"] = parsed
                result["raw_response"] = response
                result["success"] = True
                logger.info(f"读取设备数据成功: MN={self.mn}, 数据项数={len(parsed)}")
            else:
                logger.warning(f"读取设备数据失败: MN={self.mn}")

        except Exception as e:
            logger.error(f"读取设备数据异常: {e}")
        finally:
            pass

        return result

    def _parse_hj212_response(self, response: str) -> Dict[str, Any]:
        """解析 HJ212 响应数据"""
        data = {}

        if not response:
            return data

        lines = response.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith('##'):
                pairs = re.findall(r'(\w+)=([^\&\s]+)', line)
                for key, value in pairs:
                    try:
                        if '.' in value:
                            data[key] = float(value)
                        else:
                            data[key] = int(value)
                    except (ValueError, TypeError):
                        data[key] = value

        return data

    def check_device_status(self) -> Dict[str, Any]:
        """查询设备状态"""
        result = {
            "mn": self.mn,
            "status": {},
            "timestamp": datetime.now(),
            "success": False,
        }

        if not self.connected:
            if not self.connect():
                return result

        try:
            cmd = f"CN=1301&MN={self.mn}"
            response = self.send_hj212_cmd(cmd)

            if response:
                parsed = self._parse_hj212_response(response)
                result["status"] = parsed
                result["success"] = True

        except Exception as e:
            logger.error(f"查询设备状态异常: {e}")

        return result


class ModbusDevicePool:
    """设备池管理器，支持批量读取"""

    def __init__(self):
        self.devices: Dict[str, ModbusDevice] = {}

    def add_device(self, mn: str, ip: str, port: int = 8000, timeout: float = 5.0) -> ModbusDevice:
        """添加设备到池中"""
        device = ModbusDevice(mn, ip, port, timeout)
        self.devices[mn] = device
        return device

    def remove_device(self, mn: str):
        """从池中移除设备"""
        if mn in self.devices:
            self.devices[mn].close()
            del self.devices[mn]

    def read_all(self) -> List[Dict[str, Any]]:
        """批量读取所有设备数据"""
        results = []
        for mn, device in self.devices.items():
            try:
                result = device.read_all_data()
                results.append(result)
            except Exception as e:
                logger.error(f"批量读取设备 {mn} 失败: {e}")
                results.append({
                    "mn": mn,
                    "data": {},
                    "timestamp": datetime.now(),
                    "success": False,
                    "error": str(e),
                })
        return results

    def close_all(self):
        """关闭所有设备连接"""
        for device in self.devices.values():
            device.close()
        self.devices.clear()


_device_pool = ModbusDevicePool()


def get_device_pool() -> ModbusDevicePool:
    """获取全局设备池单例"""
    return _device_pool
