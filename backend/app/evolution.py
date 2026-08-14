"""
Agent 自进化引擎 — 多维度能力进化
支持: 知识进化、工具进化、模式学习、反馈学习、自我反思
"""
import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import (
    ToolPerformance, EvolutionSnapshot, AgentState,
    ConversationTurn, SemanticMemory, UsageStat,
    Standard, PollutionFactor, PollutionLimit, RegulationClause,
)

logger = logging.getLogger(__name__)


class EvolutionEngine:
    """
    Agent 自进化引擎

    进化维度:
    1. 知识进化 — 自动发现知识缺口，爬取补充
    2. 工具进化 — 分析工具性能，优化选择策略
    3. 模式学习 — 学习用户常见问法，改进意图分类
    4. 反馈学习 — 根据用户反馈调整回复策略
    5. 自我反思 — 定期评估整体表现，生成改进计划
    """

    def __init__(self, db: Session, memory=None):
        self.db = db
        self.memory = memory

    # ──────────────────────────────────────────
    #  主进化循环
    # ──────────────────────────────────────────

    async def run_evolution_cycle(self, tools=None, memory=None, max_rounds: int = 1) -> Dict[str, Any]:
        """执行一轮完整进化"""
        round_num = self._get_next_round_number()
        snapshot = {
            "round_number": round_num,
            "timestamp": datetime.now().isoformat(),
            "knowledge_added": 0,
            "gaps_identified": 0,
            "gaps_filled": 0,
            "tool_calls_total": 0,
            "tool_success_rate": 0.0,
            "new_patterns_discovered": 0,
            "status": "running",
            "details": {},
        }

        try:
            # 维度1: 知识进化
            knowledge_result = await self._evolve_knowledge(tools)
            snapshot["knowledge_added"] = knowledge_result.get("new_standards", 0)
            snapshot["gaps_identified"] = knowledge_result.get("gaps_found", 0)
            snapshot["gaps_filled"] = knowledge_result.get("gaps_filled", 0)
            snapshot["details"]["knowledge"] = knowledge_result

            # 维度2: 工具性能优化
            tools_result = self._evolve_tools()
            snapshot["details"]["tools"] = tools_result

            # 维度3: 模式学习
            patterns_result = self._evolve_patterns()
            snapshot["new_patterns_discovered"] = patterns_result.get("new_patterns", 0)
            snapshot["details"]["patterns"] = patterns_result

            # 维度4: 反馈学习
            feedback_result = self._evolve_feedback()
            snapshot["details"]["feedback"] = feedback_result

            # 维度5: 自我反思
            reflect_result = await self._self_reflect(tools)
            snapshot["details"]["reflection"] = reflect_result

            # 更新工具成功率
            perf_stats = self._get_tool_performance_stats()
            snapshot["tool_calls_total"] = perf_stats.get("total", 0)
            snapshot["tool_success_rate"] = perf_stats.get("success_rate", 0.0)

            snapshot["status"] = "completed"
            self._save_snapshot(snapshot)
            logger.info("进化完成 第%d轮: 新增知识%d 缺口填充%d 新模式%d",
                        round_num, snapshot["knowledge_added"],
                        snapshot["gaps_filled"], snapshot["new_patterns_discovered"])

        except Exception as e:
            snapshot["status"] = "failed"
            snapshot["details"]["error"] = str(e)
            self._save_snapshot(snapshot)
            logger.error("进化任务失败: %s", str(e))

        return {
            "round": round_num,
            "knowledge_added": snapshot["knowledge_added"],
            "gaps_filled": snapshot["gaps_filled"],
            "new_patterns": snapshot["new_patterns_discovered"],
            "tool_success_rate": snapshot["tool_success_rate"],
            "status": snapshot["status"],
            "details": snapshot["details"],
        }

    # ──────────────────────────────────────────
    #  维度1: 知识进化
    # ──────────────────────────────────────────

    async def _evolve_knowledge(self, tools) -> Dict[str, Any]:
        """知识进化: 识别缺口 → 爬取补充 → 更新知识库"""
        result = {"gaps_found": 0, "gaps_filled": 0, "new_standards": 0}

        # 1a. 识别知识缺口（从未回答的问题中）
        gaps = self._identify_knowledge_gaps()
        result["gaps_found"] = len(gaps)
        logger.info("识别到 %d 个知识缺口", len(gaps))

        # 1b. 填充缺口（爬取相关标准）
        if tools and gaps:
            for gap in gaps[:3]:  # 每轮最多处理3个缺口
                try:
                    crawl_result = await tools.crawl_andingest_standards(
                        source="auto", query=gap.get("topic", ""), limit=5
                    )
                    result["new_standards"] += crawl_result.get("new_standards", 0)
                    result["gaps_filled"] += 1 if crawl_result.get("new_standards", 0) > 0 else 0
                except Exception as e:
                    logger.warning("缺口填充失败: %s", str(e))

        # 1c. 尝试从用户提问中提取新因子
        new_factors = self._extract_new_factors_from_queries()
        result["new_factors"] = len(new_factors)

        return result

    def _identify_knowledge_gaps(self) -> List[Dict]:
        """从未满足的用户需求中识别知识缺口"""
        # 查询包含否定/疑问词但未找到结果的会话
        gap_keywords = ["不知道", "查不到", "没有", "找不到", "不清楚", "为什么没有", "哪里"]
        sessions = (
            self.db.query(ConversationTurn.session_id)
            .filter(ConversationTurn.role == "user")
            .distinct()
            .all()
        )
        gaps = []
        seen = set()
        for (sid,) in sessions[:10]:
            turns = (
                self.db.query(ConversationTurn)
                .filter(ConversationTurn.session_id == sid)
                .order_by(ConversationTurn.timestamp.desc())
                .limit(10)
                .all()
            )
            for turn in turns:
                content = turn.content or ""
                if any(kw in content for kw in gap_keywords):
                    # 提取话题
                    topic = self._extract_topic(content)
                    key = f"{sid}:{content[:50]}"
                    if topic and key not in seen:
                        seen.add(key)
                        gaps.append({"session": sid, "query": content, "topic": topic})
        return gaps

    def _extract_new_factors_from_queries(self) -> List[Dict]:
        """从用户提问中提取可能的新型污染因子"""
        known_symbols = {f.symbol for f in self.db.query(PollutionFactor).all()}
        new_factors = []

        # 查找包含疑似因子符号的查询
        queries = (
            self.db.query(ConversationTurn)
            .filter(ConversationTurn.role == "user")
            .order_by(ConversationTurn.timestamp.desc())
            .limit(100)
            .all()
        )
        factor_pattern = re.compile(r'\b([A-Z]{2,4}[₀₁₂₃₄₅₆₇₈₉]*)\b')
        seen = set()

        for turn in queries:
            matches = factor_pattern.findall(turn.content or "")
            for m in matches:
                if m not in known_symbols and m not in seen:
                    seen.add(m)
                    new_factors.append({"symbol": m, "source_query": (turn.content or "")[:80]})

        return new_factors[:5]

    # ──────────────────────────────────────────
    #  维度2: 工具进化
    # ──────────────────────────────────────────

    def _evolve_tools(self) -> Dict[str, Any]:
        """分析工具性能，生成优化建议"""
        stats = self._get_tool_performance_stats()
        recommendations = []

        # 低成功率工具标记
        if stats.get("success_rate", 1.0) < 0.8:
            recommendations.append({
                "type": "low_success_rate",
                "tool": stats.get("top_failed_tool"),
                "suggestion": "检查该工具的参数校验和错误处理",
            })

        # 高频低效工具
        if stats.get("high_freq_low_success"):
            for item in stats["high_freq_low_success"]:
                recommendations.append({
                    "type": "high_freq_low_success",
                    "tool": item["tool"],
                    "call_count": item["count"],
                    "success_rate": item["rate"],
                    "suggestion": f"工具 {item['tool']} 调用频繁但成功率低，需优化",
                })

        return {
            "stats": stats,
            "recommendations": recommendations,
        }

    def _get_tool_performance_stats(self) -> Dict[str, Any]:
        """获取工具性能统计"""
        total = self.db.query(func.count(ToolPerformance.id)).scalar() or 0
        if total == 0:
            return {"total": 0, "success_rate": 1.0, "by_tool": {}}

        success_count = (
            self.db.query(func.count(ToolPerformance.id))
            .filter(ToolPerformance.success == True)
            .scalar() or 0
        )

        by_tool = (
            self.db.query(
                ToolPerformance.tool_name,
                func.count(ToolPerformance.id).label("total"),
                func.sum(func.cast(ToolPerformance.success, int)).label("success"),
            )
            .group_by(ToolPerformance.tool_name)
            .all()
        )

        tool_stats = {}
        for name, total_count, success_count_tool in by_tool:
            rate = success_count_tool / total_count if total_count > 0 else 0
            tool_stats[name] = {
                "total": total_count,
                "success": success_count_tool,
                "rate": round(rate, 3),
            }

        # 找出失败率最高的工具
        failed_tools = sorted(
            [(name, s) for name, s in tool_stats.items() if s["rate"] < 0.8],
            key=lambda x: x[1]["rate"],
        )
        top_failed = failed_tools[0][0] if failed_tools else None

        return {
            "total": total,
            "success_count": success_count,
            "success_rate": round(success_count / total, 3) if total > 0 else 1.0,
            "by_tool": tool_stats,
            "top_failed_tool": top_failed,
        }

    def record_tool_performance(
        self, tool_name: str, success: bool, latency_ms: int = 0,
        error_message: str = None, query_preview: str = None, session_id: str = None,
    ):
        """记录一次工具调用的性能数据"""
        perf = ToolPerformance(
            tool_name=tool_name,
            success=success,
            latency_ms=latency_ms,
            error_message=error_message[:200] if error_message else None,
            query_preview=query_preview[:200] if query_preview else None,
            session_id=session_id,
            created_at=datetime.now(),
        )
        self.db.add(perf)
        self.db.commit()

    # ──────────────────────────────────────────
    #  维度3: 模式学习
    # ──────────────────────────────────────────

    def _evolve_patterns(self) -> Dict[str, Any]:
        """从用户查询中学习常见模式，优化意图分类"""
        patterns = self._discover_query_patterns()
        new_count = 0

        for pattern in patterns:
            # 检查是否已存在相似模式
            existing = self.db.query(AgentState).filter(
                AgentState.key == f"pattern_{pattern['keyword']}"
            ).first()
            if not existing:
                now = datetime.now()
                self.db.add(AgentState(
                    key=f"pattern_{pattern['keyword']}",
                    value=json.dumps({
                        "keyword": pattern["keyword"],
                        "intent": pattern["intent"],
                        "examples": pattern["examples"][:5],
                        "count": pattern["count"],
                    }, ensure_ascii=False),
                    updated_at=now,
                ))
                new_count += 1

        return {"new_patterns": new_count, "total_patterns": len(patterns)}

    def _discover_query_patterns(self) -> List[Dict]:
        """发现用户查询中的常见模式"""
        # 分析最近100条用户查询，提取高频模式
        queries = (
            self.db.query(ConversationTurn)
            .filter(ConversationTurn.role == "user")
            .order_by(ConversationTurn.timestamp.desc())
            .limit(100)
            .all()
        )

        patterns = []
        for turn in queries:
            content = turn.content or ""
            # 提取关键词模式
            keywords = self._extract_query_keywords(content)
            intent = self._classify_intent_fast(content)
            patterns.append({
                "keyword": keywords[0] if keywords else content[:20],
                "intent": intent,
                "examples": [content[:80]],
                "count": 1,
            })

        return patterns[:10]

    def _extract_query_keywords(self, query: str) -> List[str]:
        """从查询中提取关键词"""
        keywords = []
        # 中文关键词
        cn_words = re.findall(r'[\u4e00-\u9fff]{2,4}', query)
        keywords.extend(cn_words[:3])
        # 英文缩写
        en_words = re.findall(r'\b[A-Z]{2,4}\b', query)
        keywords.extend(en_words[:2])
        return keywords

    def _classify_intent_fast(self, query: str) -> str:
        """快速意图分类（用于模式学习）"""
        q = query.lower()
        if any(kw in q for kw in ["标准", "限值", "排放", "规定"]):
            return "knowledge_query"
        elif any(kw in q for kw in ["报告", "生成", "编制"]):
            return "report_generation"
        elif any(kw in q for kw in ["超标", "异常", "预警"]):
            return "exceedance_check"
        elif any(kw in q for kw in ["新闻", "资讯", "动态"]):
            return "news_query"
        elif any(kw in q for kw in ["公约", "条款", "入驻"]):
            return "regulation_query"
        else:
            return "general"

    # ──────────────────────────────────────────
    #  维度4: 反馈学习
    # ──────────────────────────────────────────

    def _evolve_feedback(self) -> Dict[str, Any]:
        """从用户反馈中学习改进"""
        feedbacks = (
            self.db.query(UsageStat)
            .filter(UsageStat.feedback.isnot(None))
            .order_by(UsageStat.timestamp.desc())
            .limit(20)
            .all()
        )

        positive_count = sum(1 for f in feedbacks if f.feedback == 1)
        negative_count = sum(1 for f in feedbacks if f.feedback == -1)

        # 分析负反馈的模式
        negative_sessions = [f.session_id for f in feedbacks if f.feedback == -1]
        improvement_suggestions = []

        if negative_count > positive_count and negative_count >= 3:
            improvement_suggestions.append({
                "type": "low_satisfaction",
                "suggestion": "用户满意度偏低，建议增加更多上下文和示例回复",
            })

        # 从未获得反馈的会话中查找可改进点
        unfeedbacked = (
            self.db.query(UsageStat.session_id)
            .filter(UsageStat.feedback.is_(None))
            .distinct()
            .count()
        )

        return {
            "total_feedbacks": len(feedbacks),
            "positive": positive_count,
            "negative": negative_count,
            "unfeedbacked_sessions": unfeedbacked,
            "improvements": improvement_suggestions,
        }

    def record_feedback(self, session_id: str, feedback: int, query: str = None):
        """记录用户反馈"""
        stat = UsageStat(
            session_id=session_id,
            feedback=feedback,
            timestamp=datetime.now(),
        )
        if query:
            stat.query_type = query[:100]
        self.db.add(stat)
        self.db.commit()

    # ──────────────────────────────────────────
    #  维度5: 自我反思
    # ──────────────────────────────────────────

    async def _self_reflect(self, tools) -> Dict[str, Any]:
        """自我反思：评估整体表现，生成改进计划"""
        reflection = {
            "strengths": [],
            "weaknesses": [],
            "improvement_plan": [],
        }

        # 评估知识覆盖度
        standards_count = self.db.query(func.count(Standard.id)).scalar() or 0
        factors_count = self.db.query(func.count(PollutionFactor.id)).scalar() or 0
        clauses_count = self.db.query(func.count(RegulationClause.id)).scalar() or 0

        if standards_count < 10:
            reflection["weaknesses"].append("标准库覆盖不足，建议增加爬取频率")
        else:
            reflection["strengths"].append(f"标准库充足（{standards_count}条）")

        if clauses_count == 0:
            reflection["weaknesses"].append("公约条款库为空，需要初始化")
        else:
            reflection["strengths"].append(f"公约条款库完整（{clauses_count}条）")

        # 评估工具使用效率
        perf_stats = self._get_tool_performance_stats()
        if perf_stats.get("success_rate", 1.0) < 0.7:
            reflection["weaknesses"].append(f"工具调用成功率偏低（{perf_stats['success_rate']:.0%}）")
        else:
            reflection["strengths"].append(f"工具调用成功率良好（{perf_stats['success_rate']:.0%}）")

        # 生成改进计划
        if "标准库覆盖不足" in " ".join(reflection["weaknesses"]):
            reflection["improvement_plan"].append({
                "priority": "high",
                "action": "增加标准爬取来源",
                "detail": "添加更多环保标准网站作为爬取源",
            })
        if "工具调用成功率偏低" in " ".join(reflection["weaknesses"]):
            reflection["improvement_plan"].append({
                "priority": "medium",
                "action": "优化工具错误处理",
                "detail": "增加工具调用的异常捕获和降级策略",
            })

        reflection["improvement_plan"].append({
            "priority": "low",
            "action": "增强向量语义检索",
            "detail": "考虑接入真正的向量数据库（如 ChromaDB）提升检索精度",
        })

        return reflection

    # ──────────────────────────────────────────
    #  基础设施
    # ──────────────────────────────────────────

    def _get_next_round_number(self) -> int:
        """获取下一轮进化编号"""
        existing = self.db.query(AgentState).filter(
            AgentState.key == "evolution_rounds"
        ).first()
        current = int(existing.value) if existing and existing.value else 0
        return current + 1

    def _save_snapshot(self, snapshot: Dict[str, Any]):
        """保存进化快照"""
        ev = EvolutionSnapshot(
            round_number=snapshot["round_number"],
            timestamp=datetime.fromisoformat(snapshot["timestamp"]),
            knowledge_added=snapshot["knowledge_added"],
            gaps_identified=snapshot["gaps_identified"],
            gaps_filled=snapshot["gaps_filled"],
            tool_calls_total=snapshot["tool_calls_total"],
            tool_success_rate=snapshot["tool_success_rate"],
            new_patterns_discovered=snapshot["new_patterns_discovered"],
            status=snapshot["status"],
            details=snapshot["details"],
            created_at=datetime.now(),
        )
        self.db.add(ev)
        self.db.commit()

        # 更新进化计数
        now = datetime.now()
        existing = self.db.query(AgentState).filter(
            AgentState.key == "evolution_rounds"
        ).first()
        if existing:
            existing.value = str(snapshot["round_number"])
            existing.updated_at = now
        else:
            self.db.add(AgentState(
                key="evolution_rounds", value=str(snapshot["round_number"]),
                updated_at=now,
            ))
        self.db.commit()

    def get_evolution_history(self, limit: int = 10) -> List[Dict]:
        """获取进化历史"""
        snapshots = (
            self.db.query(EvolutionSnapshot)
            .order_by(EvolutionSnapshot.round_number.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "round": s.round_number,
                "timestamp": str(s.timestamp),
                "knowledge_added": s.knowledge_added,
                "gaps_filled": s.gaps_filled,
                "new_patterns": s.new_patterns_discovered,
                "tool_success_rate": s.tool_success_rate,
                "status": s.status,
                "details": s.details or {},
            }
            for s in snapshots
        ]

    def get_evolution_stats(self) -> Dict[str, Any]:
        """获取进化统计摘要"""
        total_rounds = (
            self.db.query(AgentState).filter(AgentState.key == "evolution_rounds").first()
        )
        total_knowledge = (
            self.db.query(func.sum(EvolutionSnapshot.knowledge_added))
            .scalar() or 0
        )
        total_gaps_filled = (
            self.db.query(func.sum(EvolutionSnapshot.gaps_filled))
            .scalar() or 0
        )
        recent = self.get_evolution_history(limit=5)
        latest = recent[0] if recent else {}

        return {
            "total_rounds": int(total_rounds.value) if total_rounds else 0,
            "total_knowledge_added": total_knowledge,
            "total_gaps_filled": total_gaps_filled,
            "latest_round": latest,
            "recent_history": recent,
        }
