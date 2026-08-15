"""
LLM 智能引擎 — 集成 Agnes AI API
支持 OpenAI 兼容格式的推理和自然语言理解
"""
import json
import os
import asyncio
from typing import Dict, Any, List, Optional

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# LLM 配置（从环境变量读取，强制要求 API Key）
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://apihub.agnes-ai.cn/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "agnes-2.0-flash")


class LLMEngine:
    """LLM 推理引擎 — 支持 Agnes AI、DeepSeek、OpenAI 兼容接口"""

    def __init__(self, base_url: str = None, api_key: str = None, model: str = None):
        self.base_url = base_url or LLM_BASE_URL
        self.api_key = api_key or LLM_API_KEY
        self.model = model or LLM_MODEL
        self.enabled = bool(self.api_key) and HAS_HTTPX

    async def chat(self, messages: List[Dict[str, str]], system_prompt: str = None,
                   max_tokens: int = 2000, temperature: float = 0.3) -> Dict[str, Any]:
        """调用 LLM 生成回复"""
        if not self.enabled:
            return {"error": "LLM API 未配置，请在 .env 中设置 LLM_API_KEY", "reply": ""}

        if not HAS_HTTPX:
            return {"error": "httpx 未安装，请运行: pip install httpx", "reply": ""}

        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": all_messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                reply = data["choices"][0]["message"]["content"].strip()
                usage = data.get("usage", {})
                return {
                    "reply": reply,
                    "model": self.model,
                    "tokens_used": usage.get("total_tokens", 0),
                    "success": True,
                }
        except httpx.TimeoutException:
            return {"error": "LLM 请求超时", "reply": ""}
        except Exception as e:
            return {"error": str(e)[:200], "reply": ""}

    async def generate_reply(self, query: str, context: str = "", memories: List[Dict] = None,
                             knowledge: Dict = None) -> str:
        """生成智能回复（集成上下文和记忆）"""
        if not self.enabled:
            return self._fallback_reply(query, context, memories, knowledge)

        system_prompt = self._build_system_prompt(knowledge, memories)
        user_message = f"[历史记忆]\n{context}\n\n[用户问题]\n{query}"

        result = await self.chat(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=system_prompt,
        )
        return result.get("reply", "")

    def _build_system_prompt(self, knowledge: Dict = None, memories: List[Dict] = None) -> str:
        """构建系统提示词"""
        parts = [
            "你是一名专业的化工行业环保助手，精通国内外环保法规、排放标准、污染治理技术。",
            "你的职责是：查询环保标准、分析排放数据、生成环保报告、预警超标风险、解答环保技术问题。",
            "回答要求：准确引用标准条文，给出具体数值和建议，语言专业简洁。",
            "如果用户询问标准限值，请引用具体标准编号和限值数值。",
            "如果用户询问设备异常，请结合排放标准和历史数据分析原因。",
        ]

        if knowledge:
            standards = knowledge.get("standards", {})
            limits = standards.get("limits", [])
            if limits:
                parts.append(f"\n[知识库结果] 找到 {len(limits)} 条限值记录，请在回答中引用。")

        if memories and len(memories) > 0:
            mem_text = "\n".join(f"- {m.get('text', '')[:150]}" for m in memories[:3])
            parts.append(f"\n[相关历史记忆]\n{mem_text}")

        return "\n".join(parts)

    def _fallback_reply(self, query: str, context: str, memories, knowledge) -> str:
        """LLM 不可用时的降级回复"""
        return f"""收到您的问题：「{query}」

💡 当前 LLM 引擎未启用，已启用规则模式。

已为您检索到以下知识库信息：
{self._format_knowledge(knowledge)}

如需启用 AI 智能推理，请在 backend/.env 中配置：
  LLM_API_KEY=sk-xxxx
"""

    def _format_knowledge(self, knowledge: Dict) -> str:
        if not knowledge:
            return "暂无知识库结果"
        parts = []
        for lim in knowledge.get("standards", {}).get("limits", [])[:5]:
            parts.append(f"- {lim.get('factor','')} | {lim.get('standard','')} = {lim.get('value','')}")
        return "\n".join(parts) if parts else "暂无匹配结果"
