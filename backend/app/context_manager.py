# -*- coding: utf-8 -*-
"""
上下文管理器 — 对话历史压缩与摘要生成
解决长对话导致的上下文溢出问题
"""
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ContextManager:
    """
    上下文管理器
    - 对话超过max_turns时自动压缩历史
    - 保留关键信息，丢弃冗余细节
    - 支持跨会话的上下文恢复
    """

    def __init__(self, max_turns: int = 20, summary_threshold: int = 15):
        self.max_turns = max_turns
        self.summary_threshold = summary_threshold
        self.compression_cache = {}  # session_id -> 压缩后的摘要

    def should_compress(self, conversation: List[Dict], turn_count: int) -> bool:
        """判断是否需要压缩上下文"""
        return turn_count >= self.summary_threshold

    def compress_history(
        self,
        conversation: List[Dict],
        session_id: str,
        llm_client=None,
    ) -> List[Dict]:
        """
        压缩对话历史：
        - 保留最近 N 轮完整对话
        - 对早期对话生成摘要
        - 替换为 [摘要] + 最近N轮
        """
        if len(conversation) <= self.max_turns:
            return conversation

        # 分割：早期对话需要摘要，近期保留完整
        keep_count = self.max_turns
        to_compress = conversation[:-keep_count]
        recent = conversation[-keep_count:]

        if not to_compress:
            return recent

        # 尝试用LLM生成摘要
        if llm_client and llm_client.enabled:
            compressed = self._compress_with_llm(to_compress, llm_client)
        else:
            compressed = self._compress_without_llm(to_compress)

        # 合并
        result = [{"role": "system", "content": compressed}] + recent
        logger.info("上下文压缩完成: %d轮 → %d轮", len(conversation), len(result))
        return result

    def _compress_with_llm(
        self, history: List[Dict], llm_client
    ) -> str:
        """使用LLM生成对话摘要"""
        # 提取关键信息
        summaries = []
        for turn in history[:10]:  # 只处理前10轮
            if turn["role"] == "user":
                summaries.append(f"用户问了: {turn['content'][:100]}")
            elif turn["role"] == "assistant":
                summaries.append(f"Agent回答了: {turn['content'][:100]}")

        context = "\n".join(summaries)
        prompt = f"""请为以下环保对话生成一个简洁的摘要（50字以内），保留关键信息：标准编号、限值数值、设备异常、风险警告。

对话历史:
{context}

摘要:"""

        result = llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.1,
        )
        summary = result.get("reply", "").strip()
        return f"[对话摘要] {summary}"

    def _compress_without_llm(
        self, history: List[Dict]
    ) -> str:
        """无LLM时的降级压缩：提取关键信息"""
        key_facts = []
        for turn in history[:15]:
            if turn["role"] == "user":
                content = turn["content"]
                # 提取标准编号
                import re
                nums = re.findall(r'(GB|HJ|DB|GHZB)\s*[\d/]+\s*[-—–]\s*\d{2,4}', content)
                for num in nums:
                    key_facts.append(f"标准: {num.strip()}")
                # 提取关键词
                for kw in ['超标', '异常', '限值', '标准', '排放', '污染物']:
                    if kw in content:
                        key_facts.append(f"主题: {kw}")

        # 去重+截断
        seen = set()
        unique = []
        for f in key_facts:
            if f not in seen:
                seen.add(f)
                unique.append(f)
                if len(unique) >= 5:
                    break

        return f"[对话摘要] 涉及主题: {', '.join(unique[:5])}"

    def get_context_window(
        self,
        conversation: List[Dict],
        llm_client=None,
    ) -> List[Dict]:
        """获取适合送入LLM的上下文窗口"""
        if not conversation:
            return [{"role": "system", "content": "环保法规助手"}]

        # 压缩逻辑
        if self.should_compress(conversation, len(conversation)):
            return self.compress_history(conversation, "unknown", llm_client)

        return conversation

    def clear_session(self, session_id: str):
        """清除会话的压缩缓存"""
        self.compression_cache.pop(session_id, None)

    def get_session_summary(self, session_id: str) -> Optional[str]:
        """获取会话摘要"""
        return self.compression_cache.get(session_id)
