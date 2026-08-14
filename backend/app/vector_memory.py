"""
向量语义记忆 — 基于 SQLite 的语义检索
使用关键词匹配 + TF-IDF 评分，无需额外依赖
"""
import json
import hashlib
import re
from typing import List, Dict, Any, Optional
from datetime import datetime


class VectorMemory:
    """
    基于 SQLite 的语义记忆系统

    功能:
    1. 关键词提取与 TF-IDF 相似度评分
    2. 跨会话语义检索
    3. 持久化存储到 SQLite
    """

    def __init__(self, db_path: str = "./agent_vector.db"):
        self.db_path = db_path
        self._conn = None
        self._conn_valid = False

    def _get_conn(self):
        """获取 SQLite 连接"""
        import sqlite3
        if self._conn is None or not self._conn_valid:
            try:
                self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
                self._conn.row_factory = sqlite3.Row
                self._conn.execute("PRAGMA journal_mode=WAL")
                # 直接在当前连接上建表，不再递归调用 _get_conn
                self._conn.execute("""
                    CREATE TABLE IF NOT EXISTS semantic_memories (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        text TEXT NOT NULL,
                        mem_type TEXT NOT NULL DEFAULT 'semantic_memory',
                        meta_data TEXT,
                        created_at DATETIME NOT NULL
                    )
                """)
                self._conn.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_store (
                        id TEXT PRIMARY KEY,
                        text TEXT NOT NULL,
                        meta_data TEXT,
                        created_at DATETIME NOT NULL
                    )
                """)
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_sem_session ON semantic_memories(session_id)")
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_sem_type ON semantic_memories(mem_type)")
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_kb_text ON knowledge_store(text)")
                self._conn.commit()
                self._conn_valid = True
            except Exception:
                self._conn = None
                self._conn_valid = False
                raise
        return self._conn

    def _init_tables(self):
        """初始化存储表 — 由 _get_conn 直接内联，此方法仅作为单独调用保留"""
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS semantic_memories (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                text TEXT NOT NULL,
                mem_type TEXT NOT NULL DEFAULT 'semantic_memory',
                meta_data TEXT,
                created_at DATETIME NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_store (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                meta_data TEXT,
                created_at DATETIME NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sem_session ON semantic_memories(session_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sem_type ON semantic_memories(mem_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_kb_text ON knowledge_store(text)")
        conn.commit()

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词（中英文混合）"""
        cn_words = re.findall(r'[\u4e00-\u9fff]{2,}', text)
        en_words = re.findall(r'[a-zA-Z]{3,}', text.lower())
        return list(set(cn_words + en_words))

    def _score_similarity(self, query: str, document: str) -> float:
        """TF-IDF 风格相似度评分"""
        query_kws = set(self._extract_keywords(query.lower()))
        doc_kws = set(self._extract_keywords(document.lower()))

        if not query_kws:
            return 0.0

        # 关键词交集覆盖率
        intersection = query_kws & doc_kws
        recall = len(intersection) / len(query_kws) if query_kws else 0

        # 位置加权：关键词在前面的文档得分更高
        pos_bonus = 0.0
        for kw in intersection:
            if document.lower().startswith(kw):
                pos_bonus += 0.1
            elif kw in document.lower()[:100]:
                pos_bonus += 0.05

        # 长度归一化
        length_penalty = min(len(document) / 500.0, 1.0)

        return (recall * 0.7 + pos_bonus + length_penalty * 0.1)

    def add_memory(self, session_id: str, text: str, metadata: Optional[Dict] = None) -> str:
        """添加语义记忆"""
        mem_id = hashlib.md5(f"{session_id}:{text[:100]}".encode()).hexdigest()
        now = datetime.now().isoformat()
        meta = json.dumps(metadata or {}, ensure_ascii=False)

        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO semantic_memories (id, session_id, text, mem_type, meta_data, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (mem_id, session_id, text[:2000], "semantic_memory", meta, now),
            )
            conn.commit()
        except Exception:
            conn.rollback()
        return mem_id

    def add_knowledge(self, text: str, metadata: Optional[Dict] = None) -> str:
        """添加知识条目到知识库"""
        mem_id = hashlib.md5(f"kb:{text[:100]}".encode()).hexdigest()
        now = datetime.now().isoformat()
        meta = json.dumps(metadata or {}, ensure_ascii=False)

        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO knowledge_store (id, text, meta_data, created_at) "
            "VALUES (?, ?, ?, ?)",
            (mem_id, text[:2000], meta, now),
        )
        conn.commit()
        return mem_id

    def search_memories(self, query: str, session_id: Optional[str] = None, top_k: int = 5) -> List[Dict]:
        """在语义记忆中检索"""
        conn = self._get_conn()
        if session_id:
            rows = conn.execute(
                "SELECT id, text, meta_data, created_at FROM semantic_memories "
                "WHERE session_id = ? AND text LIKE ?",
                (session_id, f"%{query[:20]}%"),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, text, meta_data, created_at FROM semantic_memories "
                "WHERE text LIKE ?",
                (f"%{query[:20]}%",),
            ).fetchall()

        scored = []
        for row in rows:
            score = self._score_similarity(query, row["text"])
            if score > 0.05:
                scored.append({
                    "text": row["text"],
                    "metadata": json.loads(row["meta_data"]) if row["meta_data"] else {},
                    "score": round(score, 4),
                    "created_at": row["created_at"],
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def search_knowledge(self, query: str, top_k: int = 5) -> List[Dict]:
        """在知识库中检索"""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, text, meta_data, created_at FROM knowledge_store "
            "WHERE text LIKE ?",
            (f"%{query[:20]}%",),
        ).fetchall()

        scored = []
        for row in rows:
            score = self._score_similarity(query, row["text"])
            if score > 0.05:
                scored.append({
                    "text": row["text"],
                    "metadata": json.loads(row["meta_data"]) if row["meta_data"] else {},
                    "score": round(score, 4),
                    "created_at": row["created_at"],
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def get_stats(self) -> Dict[str, Any]:
        """获取向量库统计"""
        conn = self._get_conn()
        mem_count = conn.execute("SELECT COUNT(*) FROM semantic_memories").fetchone()[0]
        kb_count = conn.execute("SELECT COUNT(*) FROM knowledge_store").fetchone()[0]
        return {"semantic_memories": mem_count, "knowledge_base": kb_count}

    def clear_all(self):
        """清除所有向量数据"""
        conn = self._get_conn()
        conn.execute("DELETE FROM semantic_memories")
        conn.execute("DELETE FROM knowledge_store")
        conn.commit()

    def search_all(self, query: str, session_id: Optional[str] = None, top_k: int = 10) -> List[Dict]:
        """综合搜索"""
        mem_results = self.search_memories(query, session_id, top_k)
        kb_results = self.search_knowledge(query, top_k)
        return mem_results + kb_results
