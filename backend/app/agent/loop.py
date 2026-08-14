"""
Agent 推理循环 — ReAct/Plan-and-Execute 模式
类比 Claude Code / OpenClaw 的多步推理架构
支持: 工具调用、记忆检索、自进化循环
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import asyncio
import re
import json
from datetime import datetime


class AgentLoop:
    """
    Agent 推理引擎

    执行流程:
    1. 理解用户意图 → 检索记忆 → 调用工具 → 推理 → 生成回复
    2. 支持多轮工具调用（ReAct: Thought → Action → Observation）
    3. 自进化：定期回顾对话，发现知识缺口，自动补充
    """

    # 内置工具列表（Agent 可识别并调用）
    TOOL_REGISTRY = {
        "search_standards": {
            "description": "搜索环保法规和排放限值标准",
            "params": {"query": "搜索关键词"},
        },
        "get_factor_limits": {
            "description": "获取特定污染因子的所有排放限值",
            "params": {"factor_name": "污染因子名称或符号"},
        },
        "compare_standards": {
            "description": "对比多个标准的限值差异",
            "params": {"standard_ids": "标准ID列表"},
        },
        "analyze_device": {
            "description": "分析设备监测数据，检测异常和预测趋势",
            "params": {"device_id": "设备ID"},
        },
        "check_exceedances": {
            "description": "检查近期超标记录",
            "params": {"hours": "检查时间范围(小时)"},
        },
        "generate_report": {
            "description": "生成环保报告",
            "params": {"template_type": "报告类型", "params": "报告参数"},
        },
        "search_news": {
            "description": "搜索环保相关新闻",
            "params": {"keyword": "关键词"},
        },
        "crawl_standards": {
            "description": "从网络爬取最新环保标准并入库",
            "params": {"source": "爬取来源"},
        },
        "upload_data": {
            "description": "上传并分析监测数据",
            "params": {"content": "数据内容", "format": "数据格式"},
        },
        "web_search": {
            "description": "网络搜索最新环保资讯和政策动态",
            "params": {"query": "搜索关键词", "max_results": "返回结果数量"},
        },
        "search_regulation": {
            "description": "查询化工园区环保公约条款及企业入驻要求",
            "params": {"query": "搜索关键词", "top_k": "返回结果数量"},
        },
    }

    def __init__(self, memory, tools):
        self.memory = memory
        self.max_steps = 10  # 最大推理步数
        self._llm = None

    @property
    def llm(self):
        """延迟加载 LLM 引擎"""
        if self._llm is None:
            from app.llm_engine import LLMEngine
            self._llm = LLMEngine()
        return self._llm

    async def run(
        self,
        query: str,
        session_id: str,
        tools,
        memories: List[Dict],
        knowledge: Dict,
        mode: str = "react",
    ) -> Dict[str, Any]:
        """
        执行 Agent 推理循环

        Args:
            query: 用户输入
            session_id: 会话ID
            tools: Tools 实例
            memories: 相关记忆
            knowledge: 知识库检索结果
            mode: react（思维链）| plan（规划）| simple（简单）

        Returns:
            {reply, type, steps, tools_used, memories_used}
        """
        intent = self._classify_intent(query)
        result = {
            "reply": "",
            "type": intent,
            "steps": [],
            "tools_used": [],
            "memories_used": len(memories),
        }

        if mode == "react":
            result = await self._react_loop(query, session_id, tools, memories, knowledge, result)
        elif mode == "plan":
            result = await self._plan_loop(query, session_id, tools, memories, knowledge, result)
        else:
            result["reply"] = await self._simple_reply(query, tools, memories, knowledge)
            result["type"] = "general"

        # 保存语义记忆
        if result["reply"] and len(result["reply"]) > 50:
            from app.db.models import AgentState
            now = datetime.now()
            existing = tools.db.query(AgentState).filter(AgentState.key == "last_reply_preview").first()
            if existing:
                existing.value = result["reply"][:200]
                existing.updated_at = now
            else:
                tools.db.add(AgentState(key="last_reply_preview", value=result["reply"][:200], updated_at=now))
            tools.db.commit()

        return result

    async def _react_loop(
        self, query, session_id, tools, memories, knowledge, result
    ) -> Dict:
        """
        ReAct 推理循环: Thought → Action → Observation
        类比 Claude Code 的工具调用模式
        """
        steps = []
        current_query = query
        max_steps = min(self.max_steps, 8)

        for step in range(max_steps):
            # 1. 思考（判断是否需要调用工具）
            thought, need_tool = self._decide_action(current_query, memories, knowledge)
            steps.append({"step": step + 1, "type": "thought", "content": thought})

            if not need_tool:
                # 不需要工具，直接生成回复
                reply = await self._generate_reply(current_query, steps, memories, knowledge)
                result["reply"] = reply
                result["steps"] = steps
                return result

            # 2. 选择工具
            tool_name, tool_args = self._select_tool(current_query, thought)
            if not tool_name:
                reply = await self._generate_reply(current_query, steps, memories, knowledge)
                result["reply"] = reply
                return result

            # 3. 执行工具
            observation = await self._execute_tool(tool_name, tool_args, tools)
            steps.append({
                "step": step + 1,
                "type": "action",
                "tool": tool_name,
                "args": tool_args,
                "observation": str(observation)[:500],
            })
            result["tools_used"].append(tool_name)

            # 4. 将观察结果作为新输入，继续推理
            current_query = f"根据以下观察结果回答: {observation}"
            knowledge = await tools.search_knowledge(current_query)

        # 超时，返回部分结果
        result["reply"] = await self._generate_reply(
            query, steps, memories, knowledge
        )
        return result

    async def _plan_loop(
        self, query, session_id, tools, memories, knowledge, result
    ) -> Dict:
        """
        Plan-and-Execute: 先规划，再逐步执行
        适合复杂多步任务
        """
        # 1. 规划阶段
        plan = self._create_plan(query, tools)
        result["steps"] = plan
        result["type"] = "plan"

        # 2. 执行计划
        replies = []
        for step in plan:
            if step.get("action") == "tool_call":
                obs = await self._execute_tool(step["tool"], step.get("args", {}), tools)
                step["result"] = str(obs)[:300]
                result["tools_used"].append(step["tool"])
            elif step.get("action") == "memory_retrieve":
                mems = self.memory.retrieve(session_id, step["query"], top_k=3)
                step["results"] = mems

        # 3. 汇总回复
        result["reply"] = await self._generate_reply(query, plan, memories, knowledge)
        return result

    async def _simple_reply(
        self, query, tools, memories, knowledge
    ) -> str:
        """简单模式：直接生成回复，不调用工具"""
        return await self._generate_reply(query, [], memories, knowledge)

    def _classify_intent(self, query: str) -> str:
        """分类用户意图"""
        q = query.lower()
        if any(kw in q for kw in ["标准", "限值", "排放", "规定"]):
            return "knowledge_query"
        elif any(kw in q for kw in ["报告", "生成", "编制", "写"]):
            return "report_generation"
        elif any(kw in q for kw in ["超标", "异常", "预警", "检测"]):
            return "exceedance_check"
        elif any(kw in q for kw in ["公约", "条款", "入驻要求", "法规", "规定"]):
            return "regulation_query"
        elif any(kw in q for kw in ["预测", "趋势", "未来", "预计"]):
            return "prediction"
        elif any(kw in q for kw in ["新闻", "资讯", "动态", "最新"]):
            return "news_query"
        elif any(kw in q for kw in ["合规", "排查", "检查"]):
            return "compliance_check"
        elif any(kw in q for kw in ["爬取", "采集", "搜索", "查找"]):
            return "web_crawl"
        elif any(kw in q for kw in ["上传", "导入", "分析数据"]):
            return "data_upload"
        elif any(kw in q for kw in ["进化", "学习", "改进", "升级"]):
            return "evolution"
        else:
            return "general"

    def _decide_action(self, query, memories, knowledge) -> tuple:
        """判断是否需要调用工具"""
        # 如果用户问的是简单问候或感谢，不需要工具
        if any(kw in query.lower() for kw in ["你好", "谢谢", "再见", "哈哈"]):
            return "这是一个简单问候，不需要调用工具", False

        # 如果有知识库检索结果，可以考虑直接回复
        if knowledge.get("standards", {}).get("limits"):
            return "已有知识库结果，可以尝试直接回答", False

        # 否则需要调用工具
        return "需要调用工具获取更多信息", True

    def _select_tool(self, query, thought) -> tuple:
        """根据意图选择工具 — 优先使用 LLM，降级到关键词匹配"""
        import logging
        logger = logging.getLogger(__name__)

        # 1. 尝试 LLM 自主决策
        if self.llm.enabled:
            llm_result = self._llm_select_tool_llm(query)
            if llm_result:
                return llm_result

        # 2. 降级：关键词匹配
        q = query.lower()

        if any(kw in q for kw in ["标准", "限值", "排放"]):
            return "search_standards", {"query": query}
        elif any(kw in q for kw in ["因子", "cod", "vocs", "氨氮"]):
            return "get_factor_limits", {"factor_name": query}
        elif any(kw in q for kw in ["对比", "比较", "差异"]):
            return "compare_standards", {"query": query}
        elif any(kw in q for kw in ["设备", "监测", "数据"]):
            return "analyze_device", {"query": query}
        elif any(kw in q for kw in ["超标", "异常"]):
            return "check_exceedances", {"hours": 24}
        elif any(kw in q for kw in ["报告"]):
            return "generate_report", {"template_type": "daily_inspection"}
        elif any(kw in q for kw in ["新闻", "资讯"]):
            return "search_news", {"keyword": query}
        elif any(kw in q for kw in ["爬取", "采集"]):
            return "crawl_standards", {"source": "auto"}
        elif any(kw in q for kw in ["搜索", "最新", "政策"]):
            return "web_search", {"query": query}
        elif any(kw in q for kw in ["公约", "条款", "入驻要求", "法规", "规定"]):
            return "search_regulation", {"query": query}
        else:
            return "search_standards", {"query": query}

    def _llm_select_tool_llm(self, query: str) -> Optional[tuple]:
        """使用 LLM 选择工具，失败时返回 None"""
        tools_desc = json.dumps({
            name: tool["description"]
            for name, tool in self.TOOL_REGISTRY.items()
        }, ensure_ascii=False, indent=2)

        system_prompt = (
            "你是一个化工环保Agent的工具选择器。"
            "根据用户问题，从可用工具中选择最合适的一个。"
            "只返回JSON，不要有任何其他内容。"
            "格式：{\"tool\": \"工具名\", \"args\": {\"参数\": \"值\"}}"
            "如果不需要调用工具，返回：{\"tool\": \"none\", \"args\": {}}"
        )

        user_message = (
            f"可用工具列表：\n{tools_desc}\n\n"
            f"用户问题：{query}\n\n"
            f"请返回最合适的工具调用JSON。"
        )

        try:
            result = self.llm.chat(
                messages=[{"role": "user", "content": user_message}],
                system_prompt=system_prompt,
                max_tokens=200,
                temperature=0.0,
            )
            reply = result.get("reply", "")
            if not reply or "未配置" in reply:
                return None

            import re
            json_match = re.search(r'\{[^}]+\}', reply)
            if json_match:
                parsed = json.loads(json_match.group())
                tool_name = parsed.get("tool", "")
                args = parsed.get("args", {})
                if tool_name and tool_name in self.TOOL_REGISTRY:
                    return tool_name, args
        except Exception as e:
            logger.debug("LLM工具选择失败，降级到关键词匹配: %s", str(e))

        return None

    async def _execute_tool(self, tool_name: str, args: dict, tools) -> Any:
        """执行工具调用"""
        from app.db.models import Device
        device_id = args.get("device_id")
        if tool_name == "analyze_device" and not device_id:
            # 从查询中提取设备ID或名称
            query = args.get("query", "")
            if query:
                dev = tools.db.query(Device).filter(Device.name.contains(query)).first()
                if dev:
                    device_id = dev.id
                else:
                    device_id = tools.db.query(Device).order_by(Device.id).first()
                    device_id = device_id.id if device_id else 1
            if not device_id:
                device_id = tools.db.query(Device).order_by(Device.id).first()
                device_id = device_id.id if device_id else 1
            args["device_id"] = device_id

        tool_methods = {
            "search_standards": lambda: tools.search_standards(args.get("query", "")),
            "get_factor_limits": lambda: tools.get_factor_limits(args.get("factor_name", "")),
            "compare_standards": lambda: tools.compare_standards(args.get("standard_ids", [])),
            "analyze_device": lambda: tools.analyze_device(args.get("device_id", 1)),
            "check_exceedances": lambda: tools.check_exceedances(args.get("hours", 24)),
            "generate_report": lambda: tools.generate_report(
                args.get("template_type", "daily_inspection"),
                args.get("params", {}),
            ),
            "search_news": lambda: tools.search_news(args.get("keyword", "")),
            "crawl_standards": lambda: tools.crawl_andingest_standards(
                args.get("source", "auto")
            ),
            "upload_data": lambda: tools.process_uploaded_data(args),
            "search_regulation": lambda: tools.search_regulation(args.get("query", "")),
        }

        method = tool_methods.get(tool_name)
        if not method:
            return {"error": f"未知工具: {tool_name}"}

        try:
            result = await method()
            return result
        except Exception as e:
            return {"error": str(e)}

    async def _generate_reply(
        self, query: str, context, memories, knowledge
    ) -> str:
        """
        生成回复 — 集成 LLM 或基于规则的回复
        当前版本使用规则生成，后续可替换为 LLM
        """
        intent = self._classify_intent(query)
        reply_parts = []

        # 1. 基于意图的回复模板
        if intent == "knowledge_query":
            reply_parts.append(self._reply_knowledge(query, knowledge))
        elif intent == "report_generation":
            reply_parts.append(self._reply_report(query))
        elif intent == "exceedance_check":
            reply_parts.append(self._reply_exceedance(query))
        elif intent == "prediction":
            reply_parts.append(self._reply_prediction(query))
        elif intent == "news_query":
            reply_parts.append(self._reply_news(query))
        elif intent == "regulation_query":
            reply_parts.append(self._reply_regulation(query, knowledge))
        elif intent == "general":
            reply_parts.append(self._reply_general(query, memories))
        else:
            reply_parts.append(self._reply_general(query, memories))

        # 2. 附加记忆提示
        if memories:
            reply_parts.append("\n\n**相关历史记忆:**")
            for m in memories[:3]:
                reply_parts.append(f"- {m['text'][:100]}...")

        return "\n\n".join(reply_parts)

    def _reply_knowledge(self, query, knowledge) -> str:
        """知识查询回复"""
        factors = knowledge.get("standards", {}).get("factors", [])
        limits = knowledge.get("standards", {}).get("limits", [])
        standards = knowledge.get("standards", {}).get("standards", [])

        if not factors and not limits and not standards:
            return f"关于「{query}」，当前知识库中暂无匹配结果。\n\n建议: 运行 /crawl/standards 命令从网络采集最新标准。"

        parts = []
        if factors:
            parts.append(f"找到 {len(factors)} 个相关污染因子：\n")
            for f in factors[:5]:
                parts.append(f"• **{f['name']}** ({f['symbol']})")
                for lim in f.get("limits", [])[:3]:
                    parts.append(f"  - {lim['standard']}: {lim['value']} {f['unit']}")
            parts.append("")

        if limits:
            parts.append(f"**限值汇总（{len(limits)} 条）:**\n")
            for l in limits[:10]:
                parts.append(f"- {l['factor']}: {l['standard']} = {l['value']}")

        if standards:
            parts.append(f"\n**相关标准（{len(standards)} 条）:**\n")
            for s in standards[:5]:
                parts.append(f"- [{s['type']}] {s['title']}")

        return "\n".join(parts)

    def _reply_report(self, query) -> str:
        return """我已为您准备报告生成功能。您可以：

1. **日常巡查报告** — 检查治理设施运行、污染物排放、整改建议
2. **超标分析报告** — 分析超标原因、影响评估、整改措施
3. **合规排查报告** — 全面检查废气/废水/固废合规性
4. **年度环保报告** — 年度排放统计、投资回顾、改进计划

请告诉我您需要生成哪种报告，并提供相关参数（如日期、车间名称等）。

您也可以直接说："帮我生成今天的一号车间日常巡查报告"，我会自动填写参数。"""

    def _reply_exceedance(self, query) -> str:
        return "正在检查超标记录..."  # 实际由工具调用结果填充

    def _reply_prediction(self, query) -> str:
        return "正在分析排放趋势..."

    def _reply_news(self, query) -> str:
        return f"正在搜索关于「{query}」的环保资讯..."

    def _reply_regulation(self, query, knowledge) -> str:
        """公约条款查询回复"""
        clauses = knowledge.get("regulation", {}).get("clauses", [])
        if not clauses:
            return f"关于「{query}」，当前公约知识库中暂无匹配结果。\n\n建议: 运行 /api/regulation/seed 初始化公约数据。"

        parts = [f"找到 {len(clauses)} 条相关公约条款：\n"]
        for c in clauses[:5]:
            parts.append(f"• **{c['article_no']} — {c['article_title']}**（{c['chapter']}）")
            parts.append(f"  {c['content'][:150]}...")
            if c.get("action_required"):
                ar = c["action_required"]
                if isinstance(ar, dict) and "items" in ar:
                    parts.append(f"  📋 要求: {'; '.join(ar['items'][:4])}")
            parts.append("")
        return "\n".join(parts)

    def _reply_general(self, query, memories) -> str:
        return f"""收到您的问题：「{query}」

我正在为您分析，需要调用相关工具获取准确信息。请稍候...

💡 **提示**: 您可以具体描述需求，例如：
- "查询COD排放限值"
- "生成2025年7月的日常巡查报告"
- "分析DA001设备的排放趋势"
- "搜索最新的VOCs标准"
- "帮我爬取生态环境部最新标准"
- "对比GB31570和GB16297的VOCs限值差异"
"""

    def _create_plan(self, query: str, tools) -> List[Dict]:
        """为复杂任务创建执行计划"""
        intent = self._classify_intent(query)
        plan = []

        if intent == "knowledge_query":
            plan.append({"action": "tool_call", "tool": "search_standards", "args": {"query": query}})
        elif intent == "report_generation":
            plan.append({"action": "memory_retrieve", "query": "用户历史报告偏好"})
            plan.append({"action": "tool_call", "tool": "generate_report", "args": {"template_type": "daily_inspection", "params": {"date": "2025-07-14"}}})
        elif intent == "prediction":
            plan.append({"action": "tool_call", "tool": "analyze_device", "args": {"query": query}})
        else:
            plan.append({"action": "tool_call", "tool": "search_standards", "args": {"query": query}})

        return plan

    async def run_evolution_cycle(self, tools, memory) -> Dict[str, Any]:
        """
        自进化循环入口 — 委托给 EvolutionEngine
        保留向后兼容
        """
        from app.evolution import EvolutionEngine
        engine = EvolutionEngine(tools.db, memory)
        return await engine.run_evolution_cycle(tools=tools)
