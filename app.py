# -*- coding: utf-8 -*-
"""
化工环保Agent - Streamlit 版
匹配原 Vue3 + Element Plus 设计风格
深色绿渐变侧边栏 + 白色卡片 + 绿色主题
"""
import sqlite3
import os
import re
import json
import pandas as pd
import streamlit as st
from datetime import datetime

# ==================== 全局配置 ====================
st.set_page_config(
    page_title="环保法律法规标准库",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ==================== 自定义 CSS（匹配原前端风格）====================
CSS = """
<style>
/* === 全局 === */
[data-testid="stAppViewContainer"] {
  background: #f5f7fa;
}
[data-testid="stHeader"] { display: none; }
[data-testid="stSidebar"] { display: none; }

/* === 顶部导航条 === */
.top-bar {
  height: 56px;
  background: #fff;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  position: sticky;
  top: 0;
  z-index: 100;
  border-radius: 0 0 12px 12px;
}
.top-bar h1 {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}
.top-bar h1 span { color: #22c55e; }

/* === 卡片 === */
.card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  overflow: hidden;
  margin-bottom: 16px;
}
.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-header h3 {
  font-size: 15px;
  font-weight: 500;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}
.card-body { padding: 20px; }

/* === 统计卡片 === */
.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  transition: box-shadow 0.2s;
  border-left: 4px solid #22c55e;
}
.stat-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.stat-label { color: #666; font-size: 13px; margin-bottom: 8px; }
.stat-value { font-size: 28px; font-weight: 700; color: #1a1a1a; }
.stat-sub { font-size: 12px; color: #999; margin-top: 4px; }

/* === 标签 === */
.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  margin-right: 4px;
}
.tag-green { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }
.tag-blue { background: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe; }
.tag-yellow { background: #fefce8; color: #854d0e; border: 1px solid #fde68a; }
.tag-red { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
.tag-gray { background: #f3f4f6; color: #4b5563; border: 1px solid #e5e7eb; }
.tag-purple { background: #faf5ff; color: #6b21a8; border: 1px solid #e9d5ff; }

/* === 新闻卡片 === */
.news-card {
  background: #fff;
  border-radius: 10px;
  padding: 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}
.news-card:hover {
  border-color: #4ade80;
  box-shadow: 0 4px 12px rgba(74,222,128,0.15);
  transform: translateY(-2px);
}
.news-title {
  font-size: 14px;
  font-weight: 500;
  color: #1a1a1a;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.5;
}
.news-summary {
  font-size: 12px;
  color: #666;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 12px;
}
.news-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: #999;
}

/* === 标准列表行 === */
.std-row {
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: background 0.15s;
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.std-row:hover { background: #f8faf9; }
.std-row:last-child { border-bottom: none; }
.std-num { font-weight: 600; color: #22c55e; font-size: 14px; white-space: nowrap; min-width: 130px; }
.std-title { flex: 1; font-size: 14px; color: #1a1a1a; }
.std-meta { font-size: 12px; color: #999; margin-top: 2px; }

/* === 侧边导航 === */
.side-nav {
  width: 220px;
  height: 100vh;
  background: linear-gradient(180deg, #1a3a2a 0%, #0d2118 100%);
  position: fixed;
  left: 0;
  top: 0;
  z-index: 200;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 8px rgba(0,0,0,0.3);
}
.side-nav-header {
  padding: 20px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
.side-nav-header h2 {
  color: #4ade80;
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}
.side-nav-header p {
  color: rgba(255,255,255,0.5);
  font-size: 12px;
  margin: 4px 0 0;
}
.side-nav-menu { flex: 1; padding: 8px 0; overflow-y: auto; }
.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  color: rgba(255,255,255,0.7);
  cursor: pointer;
  transition: all 0.2s;
  border-left: 3px solid transparent;
  font-size: 14px;
}
.nav-item:hover { background: rgba(255,255,255,0.05); color: #fff; }
.nav-item.active {
  background: rgba(74,222,128,0.1);
  color: #4ade80;
  border-left-color: #4ade80;
}
.side-nav-footer {
  padding: 12px;
  border-top: 1px solid rgba(255,255,255,0.1);
  color: rgba(255,255,255,0.4);
  font-size: 11px;
  text-align: center;
}

/* === 页面内容 === */
.page-content {
  margin-left: 220px;
  min-height: 100vh;
  padding: 20px 24px;
  background: #f5f7fa;
}

/* === 污染因子表 === */
.factor-table th { background: #f8faf9 !important; font-weight: 500; }
.factor-table td { font-size: 13px; }
.limit-value { font-size: 15px; font-weight: 600; color: #e6a23c; }

/* === 分页 === */
.pagination-bar {
  padding: 12px 0;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
}
.pagination-bar button {
  padding: 4px 12px;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
}
.pagination-bar button:hover { background: #f0f0f0; }
.pagination-bar button:disabled { opacity: 0.5; cursor: default; }
.pagination-bar .page-info { color: #666; font-size: 13px; }

/* === 搜索框 === */
.search-input {
  padding: 8px 12px;
  border: 1px solid #d0d7de;
  border-radius: 8px;
  font-size: 14px;
  width: 250px;
  outline: none;
  transition: border-color 0.2s;
}
.search-input:focus { border-color: #22c55e; }
.search-select {
  padding: 8px 12px;
  border: 1px solid #d0d7de;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  background: #fff;
}

/* === 按钮 === */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #22c55e;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
  text-decoration: none;
}
.btn-primary:hover { background: #16a34a; }
.btn-small {
  padding: 4px 10px;
  font-size: 12px;
  border-radius: 6px;
}

/* === 详情弹窗（用 expander 模拟） === */
.detail-panel {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  padding: 20px;
  margin-top: 12px;
}
.detail-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}
.meta-text { font-size: 13px; color: #666; }
.section-title {
  font-size: 15px;
  font-weight: 500;
  color: #1a1a1a;
  margin: 16px 0 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.detail-link {
  color: #2563eb;
  text-decoration: none;
  font-size: 13px;
}
.detail-link:hover { text-decoration: underline; }

/* === 响应式 === */
@media (max-width: 768px) {
  .side-nav { display: none; }
  .page-content { margin-left: 0; }
}
</style>
"""

# ==================== 数据库连接 ====================
DB_PATH = os.path.join(os.path.dirname(__file__), "backend", "env_agent.db")

@st.cache_resource
def get_conn():
    if not os.path.exists(DB_PATH):
        st.error(f"数据库不存在: {DB_PATH}")
        return None
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

conn = get_conn()


# ==================== 工具函数 ====================
def query_db(sql, params=()):
    if not conn:
        return []
    cur = conn.execute(sql, params)
    return [dict(row) for row in cur.fetchall()]

def fmt_date(d):
    if not d:
        return "-"
    s = str(d)
    return s[:10]

def tag_color(category):
    colors = {
        "废气": "tag-yellow", "废水": "tag-green", "噪声": "tag-red",
        "土壤": "tag-green", "固废": "tag-gray", "辐射": "tag-purple",
        "大气": "tag-yellow", "水": "tag-green", "综合": "tag-gray",
    }
    return colors.get(category, "tag-gray")

def type_tag(t):
    if "强制" in t:
        return '<span class="tag tag-red">强制性国标</span>'
    if "推荐" in t:
        return '<span class="tag tag-green">推荐性国标</span>'
    if "行业" in t:
        return '<span class="tag tag-blue">行业标准</span>'
    if "地方" in t:
        return '<span class="tag tag-gray">地方标准</span>'
    return '<span class="tag tag-gray">' + (t or "其他") + '</span>'

def render_pagination(total, page, page_size, page_name):
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    st.markdown(f'<div class="pagination-bar">', unsafe_allow_html=True)
    st.markdown(f'<span class="page-info">共 {total} 条，第 {page}/{total_pages} 页</span>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    return page, total_pages


# ==================== 注入 CSS ====================
st.markdown(CSS, unsafe_allow_html=True)

# ==================== 侧边栏（HTML 实现） ====================
st.markdown("""
<div class="side-nav">
  <div class="side-nav-header">
    <h2>🌱 环保Agent</h2>
    <p>化工行业环保智能助手</p>
  </div>
  <nav class="side-nav-menu">
    <div class="nav-item {% if page=='dashboard' %}active{% endif %}" data-page="dashboard">📊 仪表盘</div>
    <div class="nav-item {% if page=='knowledge' %}active{% endif %}" data-page="knowledge">📚 知识库</div>
    <div class="nav-item {% if page=='news' %}active{% endif %}" data-page="news">📰 环保资讯</div>
    <div class="nav-item {% if page=='factors' %}active{% endif %}" data-page="factors">🔬 污染因子限值</div>
    <div class="nav-item {% if page=='stats' %}active{% endif %}" data-page="stats">📈 数据统计</div>
  </nav>
  <div class="side-nav-footer">v2.0 · 19359 条标准</div>
</div>
""", unsafe_allow_html=True)

# 通过 URL hash 或 st.session_state 切换页面
if "page" not in st.session_state:
    st.session_state.page = "dashboard"

# 侧边栏点击
for item in ["dashboard", "knowledge", "news", "factors", "stats"]:
    pass  # 通过按钮实现

# 顶部导航条
st.markdown("""
<div class="top-bar">
  <h1>🌱 <span>环保法律法规标准库</span></h1>
  <span style="font-size:12px;color:#999">数据来源: 国家标准公开 + 生态环境部</span>
</div>
""", unsafe_allow_html=True)

# 页面内容区
st.markdown('<div class="page-content">', unsafe_allow_html=True)

# ==================== 页面切换 ====================
current_page = st.session_state.get("page", "dashboard")

# 侧边栏按钮（放在页面内容区顶部）
page_buttons = st.container()
with page_buttons:
    cols = st.columns([1, 1, 1, 1, 1])
    for i, (name, icon, label) in enumerate([
        ("dashboard", "📊", "仪表盘"),
        ("knowledge", "📚", "知识库"),
        ("news", "📰", "环保资讯"),
        ("factors", "🔬", "污染因子限值"),
        ("stats", "📈", "数据统计"),
    ]):
        with cols[i]:
            if st.button(label, key=f"nav_{name}",
                         style="text-align:center;color:#666;background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:8px 4px;font-size:13px;",
                         height="small"):
                st.session_state.page = name
                st.rerun()

# ==================== 仪表盘 ====================
if current_page == "dashboard":
    # 统计卡片
    total_std = query_db("SELECT COUNT(*) as c FROM standards")[0]["c"]
    total_factors = query_db("SELECT COUNT(*) as c FROM pollution_factors")[0]["c"]
    total_limits = query_db("SELECT COUNT(*) as c FROM pollution_limits")[0]["c"]
    std_with_limits = query_db("SELECT COUNT(DISTINCT standard_title) as c FROM pollution_limits")[0]["c"]
    total_news = query_db("SELECT COUNT(*) as c FROM news_items")[0]["c"]

    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        st.markdown(f'<div class="stat-card"><div class="stat-label">标准总数</div><div class="stat-value" style="color:#22c55e">{total_std:,}</div><div class="stat-sub">国标/行标/地标</div></div>', unsafe_allow_html=True)
    with sc2:
        st.markdown(f'<div class="stat-card"><div class="stat-label">污染因子</div><div class="stat-value" style="color:#3b82f6">{total_factors}</div><div class="stat-sub">含排放限值</div></div>', unsafe_allow_html=True)
    with sc3:
        st.markdown(f'<div class="stat-card"><div class="stat-label">排放限值</div><div class="stat-value" style="color:#f59e0b">{total_limits}</div><div class="stat-sub">记录条数</div></div>', unsafe_allow_html=True)
    with sc4:
        st.markdown(f'<div class="stat-card"><div class="stat-label">环保资讯</div><div class="stat-value" style="color:#a78bfa">{total_news}</div><div class="stat-sub">条最新新闻</div></div>', unsafe_allow_html=True)

    # 分类统计
    st.markdown('<div class="card" style="margin-top:16px"><div class="card-header"><h3>📊 按污染类别分布</h3></div><div class="card-body">', unsafe_allow_html=True)
    cat_data = query_db("SELECT category, COUNT(*) as cnt FROM standards GROUP BY category ORDER BY cnt DESC LIMIT 10")
    if cat_data:
        df_cat = pd.DataFrame(cat_data)
        chart_col, table_col = st.columns([1, 1])
        with chart_col:
            st.bar_chart(df_cat.set_index("category")["cnt"], use_container_width=True)
        with table_col:
            st.dataframe(df_cat.rename(columns={"category": "类别", "cnt": "数量"}), use_container_width=True, hide_index=True)
    st.markdown("</div></div>", unsafe_allow_html=True)

    # 最新新闻
    st.markdown('<div class="card"><div class="card-header"><h3>📰 最新环保资讯</h3></div><div class="card-body">', unsafe_allow_html=True)
    news_rows = query_db("SELECT * FROM news_items ORDER BY published_at DESC LIMIT 6")
    if news_rows:
        nc1, nc2, nc3 = st.columns(3)
        for i, item in enumerate(news_rows[:6]):
            with [nc1, nc2, nc3][i % 3]:
                pub = fmt_date(item.get("published_at"))
                tags = item.get("tags")
                tag_html = ""
                if tags:
                    try:
                        tag_list = json.loads(tags) if isinstance(tags, str) else tags
                        tag_html = " ".join(f'<span class="tag tag-gray">{t}</span>' for t in tag_list[:2])
                    except:
                        pass
                st.markdown(f'''
                <div class="news-card" onclick="window.location.href='?page=news'">
                  <div class="news-title">{item['title'][:50]}...</div>
                  <div class="news-meta">
                    <div class="news-tags">{tag_html}</div>
                    <span>{item.get('source', '')} · {pub}</span>
                  </div>
                </div>
                ''', unsafe_allow_html=True)
    else:
        st.info("暂无新闻数据")
    st.markdown("</div></div>", unsafe_allow_html=True)

# ==================== 知识库 ====================
elif current_page == "knowledge":
    st.markdown('<div class="card"><div class="card-header">', unsafe_allow_html=True)
    st.markdown('<h3>📚 环保法律法规标准库</h3>', unsafe_allow_html=True)

    # 搜索和筛选
    col_s1, col_s2, col_s3 = st.columns([3, 1, 1])
    with col_s1:
        keyword = st.text_input("搜索标准名称/编号/行业", placeholder="如: 大气污染物、GB 16297、化工", label_visibility="collapsed", key="kw_input")
    with col_s2:
        cat_filter = st.selectbox("污染类别", ["全部", "废气", "废水", "噪声", "土壤", "固废", "辐射", "大气", "水", "综合"], label_visibility="collapsed", key="cat_filter")
    with col_s3:
        type_filter = st.selectbox("标准类型", ["全部", "强制性国家标准", "推荐性国家标准", "行业标准", "地方标准"], label_visibility="collapsed", key="type_filter")

    st.markdown("</div>", unsafe_allow_html=True)

    # 构建查询
    sql = "SELECT * FROM standards WHERE 1=1"
    params = []
    if keyword:
        sql += " AND (title LIKE ? OR standard_number LIKE ? OR industry LIKE ?)"
        params += [f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"]
    if cat_filter != "全部":
        sql += " AND category = ?"
        params.append(cat_filter)
    if type_filter != "全部":
        sql += " AND standard_type = ?"
        params.append(type_filter)

    # 获取总数
    count_sql = re.sub(r"SELECT \* FROM", "SELECT COUNT(*) as c FROM", sql)
    total = query_db(count_sql, tuple(params))[0]["c"]

    page_size = 30
    page = st.number_input("页码", min_value=1, value=1, step=1, key="kw_page", label_visibility="collapsed")
    offset = (page - 1) * page_size
    sql += " ORDER BY publish_date DESC LIMIT ? OFFSET ?"
    params += [page_size, offset]

    total_pages = max(1, (total + page_size - 1) // page_size)

    st.markdown(f"**共 {total:,} 条标准，第 {page}/{total_pages} 页**", unsafe_allow_html=True)
    st.markdown("")

    # 标准列表
    rows = query_db(sql, tuple(params))
    for row in rows:
        expanded = st.session_state.get(f"detail_{row['id']}", False)

        # 展开行
        with st.expander(f"{row['standard_number']} | {row['title']}", expanded=expanded):
            # 元信息
            meta_cols = st.columns(2)
            with meta_cols[0]:
                st.markdown(f"**标准编号**: {row['standard_number']}")
                st.markdown(f"**标准名称**: {row['title']}")
                st.markdown(f"**标准类型**: {row['standard_type']}")
            with meta_cols[1]:
                st.markdown(f"**类别**: {row['category']}")
                st.markdown(f"**适用行业**: {row['industry']}")
                st.markdown(f"**发布日期**: {fmt_date(row.get('publish_date'))}")
                st.markdown(f"**实施日期**: {fmt_date(row.get('implement_date'))}")

            # 污染因子限值
            limits = query_db(
                """SELECT pl.*, pf.name as factor_name, pf.symbol
                   FROM pollution_limits pl
                   LEFT JOIN pollution_factors pf ON pl.factor_id = pf.id
                   WHERE pl.standard_title = ?""",
                (row["title"],)
            )
            if limits:
                st.markdown(f'<div class="section-title">污染因子排放限值 <span class="tag tag-yellow">{len(limits)} 项</span></div>', unsafe_allow_html=True)
                df_lim = pd.DataFrame(limits)[["factor_name", "limit_value", "unit", "standard_type", "description"]].rename(
                    columns={"factor_name": "污染因子", "limit_value": "排放限值", "unit": "单位", "standard_type": "标准类型", "description": "说明"}
                )
                st.dataframe(df_lim, use_container_width=True, hide_index=True, height=200)
            else:
                st.info("该标准暂无限值数据")

            # 来源链接
            if row.get("source_url"):
                url = row["source_url"]
                if not url.startswith("http"):
                    url = "https://www.mee.gov.cn" + url
                st.markdown(f'📄 [查看标准原文]({url})', unsafe_allow_html=True)

        # 列表行（简洁视图）
        st.markdown(f'''
        <div class="std-row">
          <span class="std-num">{row['standard_number']}</span>
          <div style="flex:1">
            <div style="font-size:14px;color:#1a1a1a;font-weight:500">{row['title']}</div>
            <div class="std-meta">
              <span class="tag {tag_color(row.get('category',''))}">{row.get('category','其他')}</span>
              <span style="color:#999;margin-left:8px">{row.get('industry','')}</span>
              <span style="color:#999;margin-left:8px">· {fmt_date(row.get('publish_date'))}</span>
            </div>
          </div>
        </div>
        ''', unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

    # 分页按钮
    st.markdown('<div class="pagination-bar">', unsafe_allow_html=True)
    col_prev, col_page, col_next = st.columns([1, 2, 1])
    with col_prev:
        if page > 1:
            st.button("← 上一页", key="prev", type="primary" if False else "secondary")
    with col_page:
        st.markdown(f'<span class="page-info">第 {page} / {total_pages} 页</span>', unsafe_allow_html=True)
    with col_next:
        if page < total_pages:
            st.button("下一页 →", key="next", type="primary" if False else "secondary")
    st.markdown("</div>", unsafe_allow_html=True)

# ==================== 环保资讯 ====================
elif current_page == "news":
    st.markdown('<div class="card"><div class="card-header"><h3>📰 环保资讯</h3></div></div>', unsafe_allow_html=True)

    # 筛选
    nc_col1, nc_col2 = st.columns([3, 1])
    with nc_col1:
        news_kw = st.text_input("搜索资讯...", placeholder="搜索标题...", label_visibility="collapsed", key="news_kw")
    with nc_col2:
        news_cat = st.selectbox("类别", ["全部", "政策法规", "行业标准", "行业动态", "环保新闻"], label_visibility="collapsed", key="news_cat")

    sql = "SELECT * FROM news_items WHERE 1=1"
    params = []
    if news_kw:
        sql += " AND (title LIKE ? OR summary LIKE ?)"
        params += [f"%{news_kw}%", f"%{news_kw}%"]
    if news_cat != "全部":
        sql += " AND category = ?"
        params.append(news_cat.lower())
    sql += " ORDER BY published_at DESC"

    news_rows = query_db(sql)
    st.markdown(f"**共 {len(news_rows)} 条资讯**", unsafe_allow_html=True)

    # 新闻卡片网格
    for i, item in enumerate(news_rows):
        col_idx = i % 3
        cols = st.columns(3)
        with cols[col_idx]:
            pub = fmt_date(item.get("published_at"))
            tag_list = []
            try:
                tl = json.loads(item.get("tags", "[]")) if item.get("tags") else []
                tag_list = tl[:2]
            except:
                pass
            tag_html = " ".join(f'<span class="tag tag-gray">{t}</span>' for t in tag_list)
            summary = (item.get("summary") or "")[:100] + ("..." if len(item.get("summary") or "") > 100 else "")
            url = item.get("url", "")

            st.markdown(f'''
            <div class="news-card" style="margin-bottom:12px">
              <div class="news-title">{item['title']}</div>
              <div class="news-summary">{summary}</div>
              <div class="news-meta">
                <div class="news-tags">{tag_html}</div>
                <span>{item.get('source','')} · {pub}</span>
              </div>
            </div>
            ''', unsafe_allow_html=True)
            if url:
                st.markdown(f'<a href="{url}" target="_blank" class="detail-link">🔗 原文链接</a>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

# ==================== 污染因子限值 ====================
elif current_page == "factors":
    st.markdown('<div class="card"><div class="card-header"><h3>🔬 污染因子排放限值查询</h3></div></div>', unsafe_allow_html=True)

    factors = query_db("SELECT * FROM pollution_factors ORDER BY name")
    st.markdown(f"**共 {len(factors)} 个污染因子**", unsafe_allow_html=True)
    st.markdown("")

    if factors:
        # 因子列表表格
        df_f = pd.DataFrame(factors)[["name", "symbol", "unit"]].rename(
            columns={"name": "因子名称", "symbol": "符号", "unit": "单位"}
        )
        st.dataframe(df_f, use_container_width=True, hide_index=True, height=300)

        st.markdown("---")
        st.markdown("### 按因子查看限值")
        selected = st.selectbox(
            "选择污染因子",
            options=[f"{f['name']} ({f['symbol']})" for f in factors],
            key="factor_select",
        )
        if selected:
            symbol = selected.split("(")[1].rstrip(")")
            limits = query_db(
                """SELECT pl.*, pf.name as factor_name
                   FROM pollution_limits pl
                   JOIN pollution_factors pf ON pl.factor_id = pf.id
                   WHERE pf.symbol = ?
                   ORDER BY pl.standard_title""",
                (symbol,),
            )
            if limits:
                df_l = pd.DataFrame(limits)[["standard_title", "limit_value", "unit", "description"]].rename(
                    columns={"standard_title": "标准名称", "limit_value": "排放限值", "unit": "单位", "description": "说明"}
                )
                st.dataframe(df_l, use_container_width=True, hide_index=True)
            else:
                st.info("该因子暂无限值数据")

    st.markdown("</div></div>", unsafe_allow_html=True)

# ==================== 数据统计 ====================
elif current_page == "stats":
    st.markdown('<div class="card"><div class="card-header"><h3>📈 数据统计</h3></div></div>', unsafe_allow_html=True)

    total_std = query_db("SELECT COUNT(*) as c FROM standards")[0]["c"]
    total_factors = query_db("SELECT COUNT(*) as c FROM pollution_factors")[0]["c"]
    total_limits = query_db("SELECT COUNT(*) as c FROM pollution_limits")[0]["c"]
    std_with = query_db("SELECT COUNT(DISTINCT standard_title) as c FROM pollution_limits")[0]["c"]

    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1: st.metric("标准总数", f"{total_std:,}")
    with sc2: st.metric("污染因子", total_factors)
    with sc3: st.metric("排放限值", total_limits)
    with sc4: st.metric("含限值标准", std_with)

    # 按类别
    st.markdown("### 按污染类别分布")
    cat_data = query_db("SELECT category, COUNT(*) as cnt FROM standards GROUP BY category ORDER BY cnt DESC")
    if cat_data:
        df = pd.DataFrame(cat_data)
        st.bar_chart(df.set_index("category")["cnt"], use_container_width=True)
        st.dataframe(df.rename(columns={"category": "类别", "cnt": "数量"}), use_container_width=True, hide_index=True)

    # 按行业
    st.markdown("### 按适用行业分布 (Top 15)")
    ind_data = query_db("SELECT industry, COUNT(*) as cnt FROM standards GROUP BY industry ORDER BY cnt DESC LIMIT 15")
    if ind_data:
        df = pd.DataFrame(ind_data)
        st.bar_chart(df.set_index("industry")["cnt"], use_container_width=True)
        st.dataframe(df.rename(columns={"industry": "行业", "cnt": "数量"}), use_container_width=True, hide_index=True)

    # 按类型
    st.markdown("### 按标准类型分布")
    type_data = query_db("SELECT standard_type, COUNT(*) as cnt FROM standards GROUP BY standard_type ORDER BY cnt DESC")
    if type_data:
        df = pd.DataFrame(type_data)
        st.dataframe(df.rename(columns={"standard_type": "标准类型", "cnt": "数量"}), use_container_width=True, hide_index=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

# ==================== 关闭页面内容区 ====================
st.markdown("</div>", unsafe_allow_html=True)
