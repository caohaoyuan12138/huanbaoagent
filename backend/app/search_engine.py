"""
搜索引擎工具 — 集成 AnySearch 和 Tavily
用于 Agent 搜索最新环保资讯和政策动态
"""
import os
import asyncio
from typing import Dict, Any, List, Optional

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

# 搜索引擎配置
ANYSEARCH_API_KEY = os.getenv("ANYSEARCH_API_KEY", "as_sk_00833be6a9ef3d206858f1e3aa2fe359")
ANYSEARCH_BASE_URL = os.getenv("ANYSEARCH_BASE_URL", "https://api.anysearch.com/v1")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "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")
TAVILY_BASE_URL = os.getenv("TAVILY_BASE_URL", "https://api.tavily.com")

# 优先级：anysearch > tavily > 无
_search_mode = os.getenv("SEARCH_ENGINE", "anysearch")


class SearchEngine:
    """搜索引擎 — 支持 AnySearch 和 Tavily"""

    def __init__(self, mode: str = None):
        self.mode = mode or _search_mode
        self.enabled = HAS_HTTPX and bool(
            (self.mode == "anysearch" and ANYSEARCH_API_KEY) or
            (self.mode == "tavily" and TAVILY_API_KEY)
        )

    async def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """执行搜索"""
        if not self.enabled:
            return {"error": "搜索引擎未配置", "results": [], "source": "none"}

        if self.mode == "anysearch":
            return await self._search_anysearch(query, max_results)
        elif self.mode == "tavily":
            return await self._search_tavily(query, max_results)
        else:
            return {"error": f"不支持的搜索引擎: {self.mode}", "results": [], "source": self.mode}

    async def _search_anysearch(self, query: str, max_results: int) -> Dict[str, Any]:
        """AnySearch 搜索"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{ANYSEARCH_BASE_URL}/search",
                    headers={"Authorization": f"Bearer {ANYSEARCH_API_KEY}"},
                    json={
                        "query": query,
                        "count": max_results,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                results = []
                for item in data.get("data", {}).get("results", [])[:max_results]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("snippet", "")[:300],
                        "source": "anysearch",
                    })
                return {"results": results, "source": "anysearch", "count": len(results)}
        except Exception as e:
            return {"error": str(e)[:200], "results": [], "source": "anysearch"}

    async def _search_tavily(self, query: str, max_results: int) -> Dict[str, Any]:
        """Tavily 搜索"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{TAVILY_BASE_URL}/search",
                    json={
                        "api_key": TAVILY_API_KEY,
                        "query": query,
                        "max_results": max_results,
                        "search_depth": "basic",
                        "include_answer": True,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                results = []
                for item in data.get("results", [])[:max_results]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", "")[:300],
                        "source": "tavily",
                    })
                answer = data.get("answer", "")
                return {
                    "results": results,
                    "answer": answer,
                    "source": "tavily",
                    "count": len(results),
                }
        except Exception as e:
            return {"error": str(e)[:200], "results": [], "source": "tavily"}

    def get_status(self) -> Dict[str, Any]:
        """获取搜索引擎状态"""
        return {
            "enabled": self.enabled,
            "mode": self.mode,
            "anysearch_available": self.mode == "anysearch" and bool(ANYSEARCH_API_KEY),
            "tavily_available": self.mode == "tavily" and bool(TAVILY_API_KEY),
        }
