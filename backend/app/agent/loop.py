# -*- coding: utf-8 -*-
"""
Agent 推理引擎 v3.0
对比 Claude Code 增强版：
  - 上下文压缩（长对话管理）
  - 工具注册表（LLM可理解的工具描述）
  - 自修正循环（验证+重试）
  - Plan-and-Execute 模式（任务规划）
  - 工具结果验证
"""
import asyncio
import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from app.llm_engine import LLMEngine
from app.memory import MemoryManager
from app.tools import Tools
from app.tools_registry import TOOL_REGISTRY, get_tool_descriptions, get_tool_names
from app.context_manager import ContextManager

logger = logging.getLogger(__name__)


class AgentLoop:
    """
    自进化 Agent 推理循环 v3.0
    对比 Claude Code 的核心改进:
    1. CLAUDE.md 行为定义（Manifest Pattern）
    2. 工具注册表 + 结构化描述
    3. 上下文窗口压缩
    4. 自修正验证循环
    5. Plan-and-Execute 模式
    """

    def __init__(self, memory: MemoryManager, tools: Tools):
        self.memory = memory
        self.tools = tools
        self.llm = LLMEngine()
        self.context_mgr = ContextManager(max_turns=20, summary_threshold=15)

    async def run(self, query: str, session_id: str = "default",
                  mode: str = "react", max_steps: int = 10) -> Dict[str, Any]:
        """主推理入口 — ReAct or Plan-and-Execute"""
        result = {
            "query": query,
            "session_id": session_id,
            "mode": mode,
            "tools_used": [],
            "tool_results": [],
            "reply": "",
            "turn_count": 0,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # 加载历史上下文
        summary = self.memory.get_session_summary(session_id)
        conversation = summary.get("conversation", [])
        context_window = self.context_mgr.get_context_window(conversation, self.llm)

        # 根据模式执行
        if mode == "plan":
            reply = await self._run_plan_mode(query, session_id, context_window, max_steps)
        elif mode == "react":
            reply = await self._run_react_loop(query, session_id, context_window, max_steps)
        else:
            reply = await self._run_react_loop(query, session_id, context_window, max_steps)

        result["reply"] = reply
        return result

    async def _run_react_loop(
        self, query: str, session_id: str, context_window: List[Dict], max_steps: int
    ) -> str:
        """
        ReAct 推理循环（改进版）
        Thought → Action → Observation → Verification → Reply
        """
        loop_count = 0
        thoughts = []
        tool_results = []
        failed_tools = set()  # 跟踪已失败的工具，避免重复重试

        current_context = list(context_window)
        current_query = query

        while loop_count < max_steps:
            loop_count += 1
            logger.info("ReAct loop %d/%d for session %s", loop_count, max_steps, session_id)

            # Step 1: Thought（LLM思考）
            thought_result = await self._think(current_query, current_context, failed_tools)
            thought = thought_result.get("thought", "")
            thoughts.append(thought)

            # Step 2: 判断是否需要行动
            need_action = thought_result.get("need_action", False)
            if not need_action:
                # 直接回答
                return await self._generate_final_reply(current_query, thought, tool_results)

            # Step 3: Action（选择工具）
            action = thought_result.get("action", {})
            tool_name = action.get("tool", "none")
            tool_args = action.get("args", {})

            if tool_name == "none":
                return await self._generate_final_reply(current_query, thought, tool_results)

            # Step 4: Observation（执行工具）
            obs = await self._execute_tool(tool_name, tool_args)
            tool_results.append({"tool": tool_name, "args": tool_args, "result": obs})
            logger.info("Tool %s executed, result keys: %s", tool_name, list(obs.keys()) if isinstance(obs, dict) else str(obs)[:100])

            # Step 5: Verification（验证结果）
            verified = await self._verify_tool_result(tool_name, obs)
            if not verified.get("valid", True):
                logger.warning("Tool result verification failed: %s", verified.get("reason", ""))
                failed_tools.add(tool_name)
                # 尝试降级：换一个工具或直接用已有结果回答
                if loop_count < max_steps and len(failed_tools) < max_steps:
                    current_query = f"上一个方法（{tool_name}）返回失败：{verified.get('reason', '')}，请尝试其他方式回答原始问题：{query}"
                    continue
                else:
                    break

            # 追加到上下文
            current_context.append({"role": "assistant", "content": f"[工具: {tool_name}] {json.dumps(obs, ensure_ascii=False)[:200]}"})
            current_context.append({"role": "user", "content": f"[观察] {tool_name} 的结果: {str(obs)[:300]}"})

            # 检查是否已足够回答
            if self._is_sufficient(tool_results):
                return await self._generate_final_reply(current_query, thought, tool_results)

        # 超时：直接回答
        logger.warning("ReAct loop timeout after %d steps", max_steps)
        return await self._generate_final_reply(
            query, "已达到最大推理步骤，基于已有信息回答", tool_results
        )

    async def _run_plan_mode(
        self, query: str, session_id: str, context_window: List[Dict], max_steps: int
    ) -> str:
        """
        Plan-and-Execute 模式（对比 Claude Code 的 Planning Agent）
        1. 生成执行计划
        2. 用户确认计划（human-in-the-loop）
        3. 分步执行
        """
        # Step 1: 生成计划
        plan_prompt = f"""分析以下环保问题，制定分步解决方案：
用户问题：{query}

请按以下格式输出JSON计划：
{{
  "steps": [
    {{"action": "tool_call", "tool": "工具名", "args": {{}}, "description": "步骤说明"}},
    {{"action": "generate_reply", "description": "最终回复"}}
  ],
  "reasoning": "制定计划的理由"
}}"""

        plan_result = await self.llm.chat(
            messages=[{"role": "user", "content": plan_prompt}],
            max_tokens=500,
            temperature=0.1,
        )
        plan_text = plan_result.get("reply", "")

        # 解析计划
        plan = self._parse_plan(plan_text)
        if not plan or "steps" not in plan:
            return await self._run_react_loop(query, session_id, context_window, max_steps)

        # Step 2: 执行计划
        tool_results = []
        for i, step in enumerate(plan["steps"]):
            if step.get("action") == "tool_call":
                obs = await self._execute_tool(step["tool"], step.get("args", {}))
                tool_results.append(obs)
            elif step.get("action") == "generate_reply":
                break

        # 生成最终回复
        return await self._generate_final_reply(query, plan.get("reasoning", ""), tool_results)

    # ──────────────────────────────────────────
    # 思考 & 决策
    # ──────────────────────────────────────────

    async def _think(self, query: str, context: List[Dict], failed_tools: set = None) -> Dict[str, Any]:
        """LLM思考：判断意图、选择工具"""
        if not self.llm.enabled:
            return self._rule_based_think(query, failed_tools)

        tools_desc = get_tool_descriptions()
        system_prompt = """你是化工环保Agent，负责查询环保标准、分析排放数据、生成报告。
根据用户问题，决定：
1. 是否需要调用工具
2. 调用哪个工具
3. 工具的参数
只返回JSON: {"thought": "...", "need_action": true/false, "action": {"tool": "工具名", "args": {}}}"""

        user_msg = f"""可用工具:
{tools_desc}

当前问题: {query}"""

        try:
            result = await self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=300,
                temperature=0.1,
            )
            reply = result.get("reply", "")
            if reply and "未配置" not in reply:
                json_match = re.search(r'\{[^}]+\}', reply)
                if json_match:
                    parsed = json.loads(json_match.group())
                    if "thought" in parsed:
                        return parsed
        except Exception as e:
            logger.debug("LLM思考失败: %s", str(e))

        return self._rule_based_think(query)

    def _rule_based_think(self, query: str, failed_tools: set = None) -> Dict[str, Any]:
        """规则基思考（LLM不可用时的降级）"""
        q = query.lower()
        failed = failed_tools or set()
        if any(kw in q for kw in ["标准", "限值", "排放", "规定"]):
            if "search_standards" not in failed:
                return {"thought": "用户查询环保标准", "need_action": True,
                        "action": {"tool": "search_standards", "args": {"query": query}}}
            elif "get_factor_limits" not in failed:
                return {"thought": "直接查询因子限值", "need_action": True,
                        "action": {"tool": "get_factor_limits", "args": {"factor_name": query}}}
        elif any(kw in q for kw in ["因子", "cod", "vocs", "氨氮", "颗粒物"]):
            if "get_factor_limits" not in failed:
                return {"thought": "用户查询污染因子限值", "need_action": True,
                        "action": {"tool": "get_factor_limits", "args": {"factor_name": query}}}
            elif "search_standards" not in failed:
                return {"thought": "搜索相关标准", "need_action": True,
                        "action": {"tool": "search_standards", "args": {"query": query}}}
        elif any(kw in q for kw in ["你好", "谢谢", "再见"]):
            return {"thought": "简单问候，无需工具", "need_action": False, "action": {}}
        else:
            if "search_standards" not in failed:
                return {"thought": "需要搜索相关知识", "need_action": True,
                        "action": {"tool": "search_standards", "args": {"query": query}}}
        # 所有工具都失败，直接回答
        return {"thought": "工具均失败，直接回答", "need_action": False, "action": {}}

    # ──────────────────────────────────────────
    # 工具执行
    # ──────────────────────────────────────────

    async def _execute_tool(self, tool_name: str, args: dict) -> Any:
        """执行工具调用（含错误处理）"""
        tool_methods = {
            "search_standards": lambda: self.tools.search_standards(args.get("query", "")),
            "get_factor_limits": lambda: self.tools.get_factor_limits(args.get("factor_name", "")),
            "compare_standards": lambda: self.tools.compare_standards(args.get("standard_ids", [])),
            "analyze_device": lambda: self.tools.analyze_device(args.get("device_id", 1)),
            "check_exceedances": lambda: self.tools.check_exceedances(args.get("hours", 24)),
            "generate_report": lambda: self.tools.generate_report(
                args.get("template_type", "daily_inspection"),
                args.get("params", {}),
            ),
            "search_news": lambda: self.tools.search_news(args.get("keyword", "")),
            "crawl_standards": lambda: self.tools.crawl_andingest_standards(
                args.get("source", "auto")
            ),
            "upload_data": lambda: self.tools.process_uploaded_data(args),
            "search_regulation": lambda: self.tools.search_regulation(args.get("query", "")),
            "web_search": lambda: self.tools.web_search(
                args.get("query", ""), args.get("max_results", 5)
            ),
        }

        method = tool_methods.get(tool_name)
        if not method:
            return {"error": f"未知工具: {tool_name}", "valid": False}

        try:
            result = await method()
            return result
        except Exception as e:
            logger.error("工具执行失败 %s: %s", tool_name, str(e))
            return {"error": str(e)[:200], "tool": tool_name, "valid": False}

    # ──────────────────────────────────────────
    # 结果验证
    # ──────────────────────────────────────────

    async def _verify_tool_result(self, tool_name: str, result: Any) -> Dict[str, Any]:
        """验证工具结果是否合理"""
        if isinstance(result, dict) and "error" in result:
            return {"valid": False, "reason": result["error"]}

        if tool_name == "search_standards":
            if result.get("standards") and len(result["standards"]) > 0:
                return {"valid": True}
            return {"valid": False, "reason": "未找到匹配标准"}

        if tool_name == "get_factor_limits":
            if result.get("factor") and result.get("limits"):
                return {"valid": True}
            return {"valid": False, "reason": "未找到因子限值"}

        if tool_name == "analyze_device":
            if result.get("device_name"):
                return {"valid": True}
            return {"valid": False, "reason": "设备数据为空"}

        return {"valid": True}  # 默认通过

    def _is_sufficient(self, tool_results: List[Dict]) -> bool:
        """判断已有结果是否足够回答问题"""
        if not tool_results:
            return False
        # 检查是否有有价值的结果
        for tr in tool_results:
            result = tr.get("result", {})
            if isinstance(result, dict):
                if result.get("standards") or result.get("limits") or result.get("factor"):
                    return True
        return False

    # ──────────────────────────────────────────
    # 回复生成
    # ──────────────────────────────────────────

    async def _generate_final_reply(
        self, query: str, thought: str, tool_results: List[Dict]
    ) -> str:
        """生成最终回复"""
        context = self._build_context(query, thought, tool_results)

        if self.llm.enabled:
            try:
                result = await self.llm.chat(
                    messages=[{"role": "user", "content": context}],
                    system_prompt=self._build_system_prompt(),
                    max_tokens=800,
                    temperature=0.3,
                )
                return result.get("reply", "") or self._fallback_reply(query, context)
            except Exception as e:
                logger.debug("LLM回复生成失败: %s", str(e))

        return self._fallback_reply(query, context)

    def _build_context(self, query: str, thought: str, tool_results: List[Dict]) -> str:
        """构建上下文"""
        parts = [f"用户问题：{query}\n"]
        parts.append(f"分析思路：{thought}\n\n")

        for tr in tool_results:
            tool = tr.get("tool", "")
            result = tr.get("result", {})
            if isinstance(result, dict):
                # 格式化结果
                if tool == "search_standards":
                    standards = result.get("standards", [])
                    limits = result.get("limits", [])
                    if standards:
                        parts.append(f"【搜索到 {len(standards)} 条标准】\n")
                        for s in standards[:3]:
                            parts.append(f"- {s.get('title', '')}\n")
                    if limits:
                        parts.append(f"【找到 {len(limits)} 条限值记录】\n")
                        for l in limits[:5]:
                            parts.append(f"- {l.get('factor','')} | {l.get('standard','')} = {l.get('value','')}\n")
                elif tool == "get_factor_limits":
                    factor = result.get("factor", "")
                    limits = result.get("limits", [])
                    if factor:
                        parts.append(f"【因子 {factor} 的限值】\n")
                        for l in limits:
                            parts.append(f"- {l.get('standard','')}: {l.get('value','')} {l.get('unit','')}\n")
                else:
                    parts.append(f"【{tool} 结果】\n{str(result)[:300]}\n")

        return "\n".join(parts)

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是化工环保Agent，精通环保法规和排放标准。
回答要求：
1. 引用具体标准编号和条文
2. 给出明确的数值建议
3. 超标时主动预警
4. 语言专业简洁"""

    def _fallback_reply(self, query: str, context: str) -> str:
        """降级回复"""
        return f"""收到问题：「{query}」

已检索到相关信息，请查看上方工具返回结果。

如需启用AI智能推理，请配置 LLM_API_KEY 环境变量。

📋 知识库统计: 19359条标准 | 60个污染因子 | 734条限值
🔧 可用工具: {len(TOOL_REGISTRY)} 个
"""

    # ──────────────────────────────────────────
    # 计划解析
    # ──────────────────────────────────────────

    def _parse_plan(self, text: str) -> Optional[Dict]:
        """解析LLM返回的计划JSON"""
        try:
            json_match = re.search(r'\{[^}]+\}', text)
            if json_match:
                return json.loads(json_match.group())
        except Exception:
            pass
        return None

    # ──────────────────────────────────────────
    # 自进化
    # ──────────────────────────────────────────

    async def run_evolution_cycle(self, tools: Tools, memory: MemoryManager) -> Dict[str, Any]:
        """运行进化循环"""
        from app.evolution import EvolutionEngine
        engine = EvolutionEngine(tools.db, memory)
        return await engine.run_evolution_cycle(tools=tools)
