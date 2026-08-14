"""
飞书通知模块 — 将告警信息推送至飞书群/个人
"""
import os
import json
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

LARK_APP_ID = os.getenv("LARK_APP_ID", "")
LARK_APP_SECRET = os.getenv("LARK_APP_SECRET", "")
LARK_ENCRYPT_KEY = os.getenv("LARK_ENCRYPT_KEY", "")
LARK_VERIFICATION_TOKEN = os.getenv("LARK_VERIFICATION_TOKEN", "")
DEFAULT_RECEIVER_ID = os.getenv("LARK_DEFAULT_RECEIVER_ID", "")  # open_id
DEFAULT_RECEIVE_TYPE = os.getenv("LARK_DEFAULT_RECEIVE_TYPE", "open_id")  # open_id / union_id / email


class LarkNotifier:
    """飞书消息推送"""

    def __init__(
        self,
        app_id: str = None,
        app_secret: str = None,
        encrypt_key: str = None,
    ):
        self.app_id = app_id or LARK_APP_ID
        self.app_secret = app_secret or LARK_APP_SECRET
        self.encrypt_key = encrypt_key or LARK_ENCRYPT_KEY
        self.enabled = bool(self.app_id and self.app_secret)
        self._token_cache: Dict[str, Any] = {}
        self._token_expires_at: float = 0

    def _get_access_token(self) -> Optional[str]:
        """获取 tenant_access_token，带缓存"""
        import time
        now = time.time()
        if self._token_expires_at > now:
            return self._token_cache.get("access_token")

        try:
            import httpx
            resp = httpx.post(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                json={"app_id": self.app_id, "app_secret": self.app_secret},
                timeout=10,
            )
            data = resp.json()
            if data.get("code") == 0:
                token = data["tenant_access_token"]
                expire = data.get("expire", 7200)
                self._token_cache["access_token"] = token
                self._token_expires_at = now + expire - 300
                return token
            logger.warning("获取飞书 token 失败: %s", data.get("msg"))
        except Exception as e:
            logger.error("飞书 token 请求异常: %s", str(e))
        return None

    def send_message(
        self,
        text: str,
        receive_id: str = None,
        receive_type: str = None,
        msg_type: str = "text",
    ) -> Dict[str, Any]:
        """发送飞书消息"""
        if not self.enabled:
            return {"success": False, "error": "飞书应用未配置（需设置 LARK_APP_ID / LARK_APP_SECRET）"}

        token = self._get_access_token()
        if not token:
            return {"success": False, "error": "获取飞书 token 失败"}

        receiver = receive_id or DEFAULT_RECEIVER_ID
        rtype = receive_type or DEFAULT_RECEIVE_TYPE

        if not receiver:
            return {"success": False, "error": "未指定接收者（receive_id 或 LARK_DEFAULT_RECEIVER_ID）"}

        try:
            import httpx
            resp = httpx.post(
                f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={rtype}",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "receive_id": receiver,
                    "msg_type": msg_type,
                    "content": json.dumps({"text": text}, ensure_ascii=False),
                },
                timeout=15,
            )
            data = resp.json()
            if data.get("code") == 0:
                return {"success": True, "message_id": data.get("data", {}).get("message_id")}
            return {"success": False, "error": data.get("msg", str(data)), "raw": data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def send_alert_card(
        self,
        device_name: str,
        factor: str,
        value: float,
        limit: float,
        unit: str,
        severity: str,
        message: str,
        receiver_id: str = None,
        receiver_type: str = None,
    ) -> Dict[str, Any]:
        """发送告警卡片消息"""
        emoji = "🔴" if severity == "critical" else "🟡"
        title = f"{emoji} 环保告警 — {device_name}"
        color = "red" if severity == "critical" else "orange"

        card = {
            "config": {"wide_screen_mode": True},
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**{title}**\n\n"
                                   f"- **设备**: {device_name}\n"
                                   f"- **因子**: {factor}\n"
                                   f"- **当前值**: {value} {unit}\n"
                                   f"- **限值**: {limit} {unit}\n"
                                   f"- **严重程度**: {'严重超标（1.5倍以上）' if severity == 'critical' else '一般超标'}\n"
                                   f"- **时间**: 实时监测\n\n"
                                   f">{message}",
                    },
                },
                {
                    "tag": "hr",
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "lark_md", "content": "📋 查看告警详情"},
                            "type": "primary" if severity == "critical" else "default",
                            "url": f"http://localhost:8000/alerts",
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "lark_md", "content": "✅ 确认已知晓"},
                            "type": "default",
                            "url": f"http://localhost:8000/alerts",
                        },
                    ],
                },
            ],
            "header": {
                "title": {"tag": "plain_text", "content": f"{emoji} {title}"},
                "template": color,
            },
        }

        try:
            import httpx
            token = self._get_access_token()
            if not token:
                return {"success": False, "error": "获取飞书 token 失败"}

            receiver = receiver_id or DEFAULT_RECEIVER_ID
            rtype = receiver_type or DEFAULT_RECEIVE_TYPE

            if not receiver:
                return {"success": False, "error": "未指定接收者"}

            resp = httpx.post(
                f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={rtype}",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "receive_id": receiver,
                    "msg_type": "interactive",
                    "content": json.dumps(card, ensure_ascii=False),
                },
                timeout=15,
            )
            data = resp.json()
            if data.get("code") == 0:
                return {"success": True, "message_id": data.get("data", {}).get("message_id")}
            return {"success": False, "error": data.get("msg", str(data)), "raw": data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def send_group_message(
        self,
        text: str,
        chat_id: str,
        msg_type: str = "text",
    ) -> Dict[str, Any]:
        """发送到飞书群组"""
        if not self.enabled:
            return {"success": False, "error": "飞书应用未配置"}

        token = self._get_access_token()
        if not token:
            return {"success": False, "error": "获取飞书 token 失败"}

        try:
            import httpx
            resp = httpx.post(
                "https://open.feishu.cn/open-apis/im/v1/messages",
                headers={"Authorization": f"Bearer {token}"},
                params={"receive_id_type": "chat_id"},
                json={
                    "receive_id": chat_id,
                    "msg_type": msg_type,
                    "content": json.dumps({"text": text}, ensure_ascii=False),
                },
                timeout=15,
            )
            data = resp.json()
            if data.get("code") == 0:
                return {"success": True, "message_id": data.get("data", {}).get("message_id")}
            return {"success": False, "error": data.get("msg", str(data)), "raw": data}
        except Exception as e:
            return {"success": False, "error": str(e)}


# 模块级单例
_notifier: Optional[LarkNotifier] = None


def get_notifier() -> LarkNotifier:
    global _notifier
    if _notifier is None:
        _notifier = LarkNotifier()
    return _notifier


def notify_alert(
    device_name: str,
    factor: str,
    value: float,
    limit: float,
    unit: str,
    severity: str,
    message: str,
    use_card: bool = True,
) -> Dict[str, Any]:
    """便捷函数：发送告警通知"""
    notifier = get_notifier()
    if not notifier.enabled:
        logger.info("飞书通知未启用，跳过告警推送: device=%s factor=%s", device_name, factor)
        return {"success": False, "reason": "not_configured"}

    if use_card:
        return notifier.send_alert_card(
            device_name=device_name,
            factor=factor,
            value=value,
            limit=limit,
            unit=unit,
            severity=severity,
            message=message,
        )
    else:
        emoji = "🔴" if severity == "critical" else "🟡"
        return notifier.send_message(
            text=f"{emoji} 环保告警\n设备: {device_name}\n因子: {factor} = {value}{unit}（限值: {limit}{unit}）\n{message}"
        )
