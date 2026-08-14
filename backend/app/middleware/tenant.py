"""
租户隔离中间件
从请求头 X-Tenant-Id 提取租户ID，自动过滤查询结果
"""
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
import uuid


class TenantMiddleware(BaseHTTPMiddleware):
    _admin_paths = {
        "/api/tenants",
        "/api/health",
        "/api/agent/vector/stats",
    }

    def _is_admin_request(self, request: Request) -> bool:
        if request.url.path.startswith("/api/tenants"):
            return True
        if request.url.path.startswith("/api/health"):
            return True
        if request.headers.get("X-Admin-Mode") == "true":
            return True
        return False

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if self._is_admin_request(request):
            request.state.tenant_id = None
            request.state.is_admin = True
        else:
            tenant_id_header = request.headers.get("X-Tenant-Id")
            if tenant_id_header:
                try:
                    tenant_id = int(tenant_id_header)
                    request.state.tenant_id = tenant_id
                    request.state.is_admin = False
                except (ValueError, TypeError):
                    request.state.tenant_id = None
                    request.state.is_admin = True
            else:
                request.state.tenant_id = None
                request.state.is_admin = True

        response = await call_next(request)
        return response

    @staticmethod
    def get_tenant_id(request: Request) -> Optional[int]:
        return getattr(request.state, "tenant_id", None)

    @staticmethod
    def is_admin(request: Request) -> bool:
        return getattr(request.state, "is_admin", True)


def with_tenant_filter(query, model_class, tenant_id_attr="tenant_id", request=None):
    """
    为查询自动添加 tenant_id 过滤条件。
    如果 request.state.tenant_id 存在且不为 None，则追加过滤条件。
    """
    if request and hasattr(request.state, "tenant_id"):
        tid = request.state.tenant_id
        if tid is not None:
            tenant_attr = getattr(model_class, tenant_id_attr, None)
            if tenant_attr is not None:
                query = query.filter(tenant_attr == tid)
    return query
