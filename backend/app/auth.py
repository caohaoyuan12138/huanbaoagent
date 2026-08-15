# -*- coding: utf-8 -*-
"""
JWT 认证中间件
提供 API 访问控制，防止未授权调用
"""
import os
from datetime import datetime, timedelta
from typing import Optional

try:
    import jwt
    HAS_PYJWT = True
except ImportError:
    HAS_PYJWT = False


def _get_config():
    """从环境变量读取JWT配置"""
    return {
        "secret": os.getenv("JWT_SECRET_KEY", "change-me-to-a-random-secret"),
        "algorithm": os.getenv("JWT_ALGORITHM", "HS256"),
        "expire_days": int(os.getenv("JWT_EXPIRE_DAYS", "7")),
    }


def create_token(user_id: str, username: str = None, role: str = "user") -> str:
    """创建JWT token"""
    if not HAS_PYJWT:
        raise ImportError("请安装 PyJWT: pip install pyjwt")
    config = _get_config()
    now = datetime.utcnow()
    payload = {
        "sub": user_id,
        "username": username or user_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(days=config["expire_days"]),
    }
    return jwt.encode(payload, config["secret"], algorithm=config["algorithm"])


def verify_token(token: str) -> Optional[dict]:
    """验证JWT token，返回payload或None"""
    if not HAS_PYJWT:
        return None
    config = _get_config()
    try:
        payload = jwt.decode(token, config["secret"], algorithms=[config["algorithm"]])
        if payload.get("exp", 0) < datetime.utcnow().timestamp():
            return None
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def require_auth(headers: dict) -> Optional[dict]:
    """
    从请求头中提取并验证JWT token
    支持两种格式:
      - Authorization: Bearer <token>
      - X-API-Key: <token>
    """
    # 优先从 Authorization header 提取
    auth = headers.get("Authorization", "") or headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:].strip()
        return verify_token(token)

    # 从 X-API-Key header 提取
    api_key = headers.get("X-API-Key", "") or headers.get("x-api-key", "")
    if api_key:
        return verify_token(api_key.strip())

    return None
