"""
Agent 记忆系统 — 短期对话记忆 + 长期语义记忆
类比 Claude Code 的记忆能力：记住用户偏好、历史对话、知识积累
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib
import json
import os


class MemoryManager:
    """
    三层记忆架构:
    1. 短期对话记忆: 每次会话的问答记录（SQLite）
    2. 长期语义记忆: 重要的知识沉淀（语义向量检索）
    3. 使用统计记忆: Agent 行为追踪与进化反馈
    """

    def __init__(self, db: Session):
        self.db = db
        self._init_tables()

    def _init_tables(self):
        """初始化记忆表"""
        from app.db.models import ConversationTurn, SemanticMemory, UsageStat, AgentState

        self.db.execute(text("""
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                meta_data TEXT DEFAULT '{}'
            )
        """))
        self.db.execute(text("CREATE INDEX IF NOT EXISTS idx_turns_session ON conversation_turns(session_id)"))

        self.db.execute(text("""
            CREATE TABLE IF NOT EXISTS semantic_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                text TEXT NOT NULL,
                embedding_hash TEXT,
                meta_data TEXT DEFAULT '{}',
                created_at DATETIME NOT NULL,
                access_count INTEGER DEFAULT 0
            )
        """))
        self.db.execute(text("CREATE INDEX IF NOT EXISTS idx_semantic_session ON semantic_memories(session_id)"))
        self.db.execute(text("CREATE INDEX IF NOT EXISTS idx_semantic_hash ON semantic_memories(embedding_hash)"))

        self.db.execute(text("""
            CREATE TABLE IF NOT EXISTS usage_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                query_type TEXT,
                tool_used TEXT,
                timestamp DATETIME NOT NULL,
                feedback INTEGER
            )
        """))
        self.db.execute(text("CREATE INDEX IF NOT EXISTS idx_usage_session ON usage_stats(session_id)"))

        # Agent 状态表 — 已由 AgentState ORM 模型管理，此处不再创建重复表

        self.db.commit()

    # ──────────────────────────────────────────
    #  短期对话记忆
    # ──────────────────────────────────────────

    def save_turn(self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None):
        """保存对话轮次"""
        from app.db.models import ConversationTurn
        turn = ConversationTurn(
            session_id=session_id,
            role=role,
            content=content,
            timestamp=datetime.now(),
            meta_data=metadata or {},
        )
        self.db.add(turn)
        self.db.commit()

    def get_turns(self, session_id: str, limit: int = 50) -> List[Dict]:
        """获取会话历史"""
        from app.db.models import ConversationTurn
        turns = (
            self.db.query(ConversationTurn)
            .filter(ConversationTurn.session_id == session_id)
            .order_by(ConversationTurn.timestamp.asc())
            .limit(limit)
            .all()
        )
        return [
            {
                "role": t.role,
                "content": t.content,
                "timestamp": str(t.timestamp),
                "metadata": t.meta_data or {},
            }
            for t in turns
        ]

    def get_recent_context(self, session_id: str, max_tokens: int = 4000) -> str:
        """获取最近的对话上下文（用于Agent推理）"""
        turns = self.get_turns(session_id, limit=30)
        context = []
        for t in turns[-10:]:
            role_label = "用户" if t["role"] == "user" else "Agent"
            context.append(f"[{role_label}]: {t['content'][:500]}")
        return "\n".join(context) if context else ""

    # ──────────────────────────────────────────
    #  长期语义记忆
    # ──────────────────────────────────────────

    def save_semantic(self, session_id: str, text: str, metadata: Optional[Dict] = None):
        """保存一条语义记忆"""
        from app.db.models import SemanticMemory
        embedding_hash = hashlib.md5(text.encode()).hexdigest()[:16]

        mem = SemanticMemory(
            session_id=session_id,
            text=text[:2000],
            embedding_hash=embedding_hash,
            meta_data=metadata or {},
            created_at=datetime.now(),
        )
        self.db.add(mem)
        self.db.commit()

    def retrieve(self, session_id: str, query: str, top_k: int = 3) -> List[Dict]:
        """检索相关记忆，带时间衰减"""
        from app.db.models import SemanticMemory
        import hashlib
        from datetime import datetime
        from sqlalchemy import and_, or_

        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        now = datetime.utcnow()

        # 策略1: 语义检索（前缀匹配）
        related = (
            self.db.query(SemanticMemory)
            .filter(
                SemanticMemory.session_id == session_id,
                SemanticMemory.embedding_hash.startswith(query_hash),
            )
            .order_by(SemanticMemory.access_count.desc())
            .limit(top_k * 2)
            .all()
        )

        # 策略2: 降级到文本包含匹配
        if not related:
            related = (
                self.db.query(SemanticMemory)
                .filter(
                    SemanticMemory.session_id == session_id,
                    SemanticMemory.text.contains(query[:10]),
                )
                .order_by(SemanticMemory.access_count.desc())
                .limit(top_k)
                .all()
            )

        # 时间衰减：越旧的记忆权重越低
        for m in related:
            if m.created_at:
                age_days = (now - m.created_at).days
                decay_factor = 1.0 / (1.0 + age_days * 0.05)
                m.access_count = max(0, int(m.access_count * decay_factor))

        try:
            self.db.commit()
        except Exception:
            self.db.rollback()

        results = []
        for m in related:
            meta = m.meta_data or {}
            results.append({
                "text": m.text,
                "type": meta.get("type", "semantic"),
                "access_count": m.access_count,
                "created_at": m.created_at,
            })

        if len(results) >= top_k:
            return results[:top_k]

        return results

    def get_semantic_memories(self, session_id: str, limit: int = 20) -> List[Dict]:
        """获取某会话的所有语义记忆"""
        from app.db.models import SemanticMemory
        memories = (
            self.db.query(SemanticMemory)
            .filter(SemanticMemory.session_id == session_id)
            .order_by(SemanticMemory.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "text": m.text,
                "metadata": m.meta_data or {},
                "created_at": str(m.created_at),
            }
            for m in memories
        ]

    # ──────────────────────────────────────────
    #  使用统计与反馈
    # ──────────────────────────────────────────

    def record_usage(self, session_id: str, query: str, query_type: str, tool_used: Optional[str] = None):
        """记录一次Agent使用"""
        from app.db.models import UsageStat
        stat = UsageStat(
            session_id=session_id,
            query_type=query_type,
            tool_used=tool_used,
            timestamp=datetime.now(),
        )
        self.db.add(stat)
        self.db.commit()

    def record_feedback(self, session_id: str, feedback: int):
        """记录用户对回复的反馈"""
        from app.db.models import UsageStat
        stat = UsageStat(
            session_id=session_id,
            feedback=feedback,
            timestamp=datetime.now(),
        )
        self.db.add(stat)
        self.db.commit()

    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计"""
        from app.db.models import UsageStat, ConversationTurn, SemanticMemory

        total_interactions = self.db.query(func.count(UsageStat.id)).scalar() or 0
        total_turns = self.db.query(func.count(ConversationTurn.id)).scalar() or 0
        total_semantic = self.db.query(func.count(SemanticMemory.id)).scalar() or 0

        tool_stats = (
            self.db.query(
                UsageStat.tool_used,
                func.count(UsageStat.id).label("count"),
            )
            .filter(UsageStat.tool_used.isnot(None))
            .group_by(UsageStat.tool_used)
            .all()
        )

        return {
            "total": total_interactions,
            "turns": total_turns,
            "semantic_memories": total_semantic,
            "tool_calls": sum(c for _, c in tool_stats),
            "tool_breakdown": {row[0]: row[1] for row in tool_stats} if tool_stats else {},
            "knowledge_entries": total_semantic,
            "evolution_rounds": 0,
        }

    # ──────────────────────────────────────────
    #  会话管理
    # ──────────────────────────────────────────

    def list_sessions(self) -> List[Dict]:
        """列出所有会话"""
        from app.db.models import ConversationTurn, SemanticMemory, UsageStat

        sessions = self.db.query(ConversationTurn.session_id).distinct().all()
        result = []
        for (sid,) in sessions:
            turn_count = (
                self.db.query(func.count(ConversationTurn.id))
                .filter(ConversationTurn.session_id == sid)
                .scalar() or 0
            )
            semantic_count = (
                self.db.query(func.count(SemanticMemory.id))
                .filter(SemanticMemory.session_id == sid)
                .scalar() or 0
            )
            result.append({
                "session_id": sid,
                "turn_count": turn_count,
                "semantic_count": semantic_count,
                "created_at": self.get_session_created(sid),
            })
        return sorted(result, key=lambda x: x["created_at"], reverse=True)

    def get_session_created(self, session_id: str) -> str:
        """获取会话创建时间"""
        from app.db.models import ConversationTurn
        earliest = (
            self.db.query(func.min(ConversationTurn.timestamp))
            .filter(ConversationTurn.session_id == session_id)
            .scalar()
        )
        return str(earliest) if earliest else "unknown"

    def clear_session(self, session_id: str):
        """清除单个会话记忆"""
        from app.db.models import ConversationTurn, SemanticMemory, UsageStat
        self.db.query(ConversationTurn).filter(
            ConversationTurn.session_id == session_id
        ).delete()
        self.db.query(SemanticMemory).filter(
            SemanticMemory.session_id == session_id
        ).delete()
        self.db.query(UsageStat).filter(
            UsageStat.session_id == session_id
        ).delete()
        self.db.commit()

    def clear_all(self):
        """清除所有记忆"""
        from app.db.models import ConversationTurn, SemanticMemory, UsageStat
        self.db.query(ConversationTurn).delete()
        self.db.query(SemanticMemory).delete()
        self.db.query(UsageStat).delete()
        self.db.commit()

    def get_session_summary(self, session_id: str) -> Dict:
        """获取会话摘要"""
        turns = self.get_turns(session_id, limit=10)
        sems = self.get_semantic_memories(session_id, limit=5)

        last_queries = [t["content"] for t in turns if t["role"] == "user"][-5:]
        key_memories = [m["text"][:100] for m in sems]

        return {
            "session_id": session_id,
            "total_turns": len(turns),
            "total_semantic": len(sems),
            "recent_queries": last_queries,
            "key_memories": key_memories,
            "conversation": turns[-6:],
        }


class StateManager:
    """Agent状态管理 — 保存进化进度、配置等"""

    def __init__(self, db: Session):
        self.db = db
        self._init_table()

    def _init_table(self):
        from app.db.models import AgentState
        self.db.execute(text("""
            CREATE TABLE IF NOT EXISTS agent_state (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at DATETIME NOT NULL
            )
        """))
        self.db.commit()

    def set(self, key: str, value: Any):
        from app.db.models import AgentState
        now = datetime.now()
        existing = self.db.query(AgentState).filter(AgentState.key == key).first()
        if existing:
            existing.value = json.dumps(value) if not isinstance(value, str) else value
            existing.updated_at = now
        else:
            self.db.add(AgentState(
                key=key,
                value=json.dumps(value) if not isinstance(value, str) else value,
                updated_at=now,
            ))
        self.db.commit()

    def get(self, key: str, default=None):
        from app.db.models import AgentState
        row = self.db.query(AgentState).filter(AgentState.key == key).first()
        if not row:
            return default
        try:
            return json.loads(row.value)
        except (json.JSONDecodeError, TypeError):
            return row.value

    def get_all(self) -> Dict[str, Any]:
        from app.db.models import AgentState
        rows = self.db.query(AgentState).all()
        result = {}
        for row in rows:
            try:
                result[row.key] = json.loads(row.value)
            except (json.JSONDecodeError, TypeError):
                result[row.key] = row.value
        return result
