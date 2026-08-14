# -*- coding: utf-8 -*-
"""
化工环保Agent - Streamlit 版
直接读取 SQLite 数据库，无需 FastAPI 后端
"""
import sqlite3
import os
import pandas as pd
import streamlit as st

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), "backend", "env_agent.db")


@st.cache_resource
def get_connection():
    """获取数据库连接（缓存）"""
    if not os.path.exists(DB_PATH):
        st.error(f"数据库不存在: {DB_PATH}")
        st.stop()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def query_db(sql, params=()):
    """执行查询，返回字典列表"""
    conn = get_connection()
    cur = conn.execute(sql, params)
    return [dict(row) for row in cur.fetchall()]


# ==================== 页面配置 ====================
st.set_page_config(
    page_title="化工环保Agent - 知识库",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==================== 侧边栏 ====================
st.sidebar.title("化工环保Agent")
st.sidebar.markdown("### 环保法律法规标准库")
menu = st.sidebar.radio(
    "功能菜单",
    ["📚 知识库", "🔬 污染因子限值", "📰 环保新闻", "📊 数据统计"],
)

# 数据库概览
try:
    total_std = query_db("SELECT COUNT(*) as c FROM standards")[0]["c"]
    total_limits = query_db("SELECT COUNT(*) as c FROM pollution_limits")[0]["c"]
    total_factors = query_db("SELECT COUNT(*) as c FROM pollution_factors")[0]["c"]
    st.sidebar.markdown("---")
    st.sidebar.metric("标准总数", f"{total_std:,}")
    st.sidebar.metric("污染因子", total_factors)
    st.sidebar.metric("排放限值", total_limits)
except Exception:
    st.sidebar.warning("数据库连接失败")


# ==================== 知识库页面 ====================
if menu == "📚 知识库":
    st.title("📚 环保法律法规标准库")

    # 搜索栏
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        keyword = st.text_input("搜索标准名称/编号/行业", placeholder="如: 大气污染物、GB 16297、化工")
    with col2:
        category_filter = st.selectbox(
            "污染类别",
            ["全部", "废气", "废水", "噪声", "土壤", "固废", "辐射", "大气", "水", "综合"],
        )
    with col3:
        type_filter = st.selectbox(
            "标准类型",
            ["全部", "强制性国家标准", "推荐性国家标准", "行业标准", "地方标准"],
        )

    # 构建查询
    sql = "SELECT * FROM standards WHERE 1=1"
    params = []
    if keyword:
        sql += " AND (title LIKE ? OR standard_number LIKE ? OR industry LIKE ?)"
        params += [f"%{keyword}%"] * 3
    if category_filter != "全部":
        sql += " AND category = ?"
        params.append(category_filter)
    if type_filter != "全部":
        sql += " AND standard_type = ?"
        params.append(type_filter)

    # 分页
    page_size = st.session_state.get("page_size", 20)
    page = st.number_input("页码", min_value=1, value=1, step=1)
    offset = (page - 1) * page_size
    sql += " ORDER BY publish_date DESC LIMIT ? OFFSET ?"
    params += [page_size, offset]

    try:
        rows = query_db(sql, tuple(params))
        # 获取总数
        count_sql = sql.split("ORDER BY")[0].replace("SELECT *", "SELECT COUNT(*) as c")
        count_params = params[:-2]
        total = query_db(count_sql, tuple(count_params))[0]["c"]
        total_pages = (total + page_size - 1) // page_size

        st.markdown(f"**共 {total:,} 条标准，第 {page}/{total_pages} 页**")

        # 标准列表
        for row in rows:
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(
                        f"**{row['standard_number']}** | {row['title']}"
                    )
                    st.caption(
                        f"类别: {row['category']} | 行业: {row['industry']} | "
                        f"类型: {row['standard_type']}"
                    )
                with col2:
                    if st.button("查看详情", key=f"btn_{row['id']}"):
                        st.session_state["selected_std"] = row["id"]

                # 详情展开
                if st.session_state.get("selected_std") == row["id"]:
                    st.markdown("---")
                    # 标准信息
                    info_col1, info_col2 = st.columns(2)
                    with info_col1:
                        st.markdown(f"**标准编号**: {row['standard_number']}")
                        st.markdown(f"**标准名称**: {row['title']}")
                        st.markdown(f"**标准类型**: {row['standard_type']}")
                    with info_col2:
                        st.markdown(f"**类别**: {row['category']}")
                        st.markdown(f"**适用行业**: {row['industry']}")
                        pub = str(row['publish_date'][:10]) if row['publish_date'] else "未知"
                        impl = str(row['implement_date'][:10]) if row['implement_date'] else "未知"
                        st.markdown(f"**发布日期**: {pub}")
                        st.markdown(f"**实施日期**: {impl}")

                    # 污染因子限值
                    limits = query_db(
                        """SELECT pl.*, pf.name as factor_name, pf.symbol
                           FROM pollution_limits pl
                           LEFT JOIN pollution_factors pf ON pl.factor_id = pf.id
                           WHERE pl.standard_title = ?""",
                        (row["title"],),
                    )
                    st.markdown("#### 污染因子排放限值")
                    if limits:
                        df = pd.DataFrame(limits)
                        df = df[["factor_name", "limit_value", "unit", "description"]].rename(
                            columns={
                                "factor_name": "污染因子",
                                "limit_value": "排放限值",
                                "unit": "单位",
                                "description": "说明",
                            }
                        )
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.info("该标准暂无限值数据")

                    # 来源链接
                    if row.get("source_url"):
                        st.markdown(f"📄 [查看标准原文]({row['source_url']})")
                    st.markdown("---")
    except Exception as e:
        st.error(f"查询失败: {e}")


# ==================== 污染因子限值页面 ====================
elif menu == "🔬 污染因子限值":
    st.title("🔬 污染因子排放限值")

    # 因子列表
    factors = query_db("SELECT * FROM pollution_factors ORDER BY name")
    st.markdown(f"**共 {len(factors)} 个污染因子**")

    if factors:
        df_factors = pd.DataFrame(factors)[["name", "symbol", "unit"]].rename(
            columns={"name": "因子名称", "symbol": "符号", "unit": "单位"}
        )
        st.dataframe(df_factors, use_container_width=True, hide_index=True)

        # 选择因子查看限值
        st.markdown("---")
        st.markdown("### 按因子查询限值")
        selected_factor = st.selectbox(
            "选择污染因子",
            options=[f"{f['name']} ({f['symbol']})" for f in factors],
        )
        if selected_factor:
            symbol = selected_factor.split("(")[1].rstrip(")")
            limits = query_db(
                """SELECT pl.*, pf.name as factor_name
                   FROM pollution_limits pl
                   JOIN pollution_factors pf ON pl.factor_id = pf.id
                   WHERE pf.symbol = ?
                   ORDER BY pl.standard_title""",
                (symbol,),
            )
            if limits:
                df = pd.DataFrame(limits)[
                    ["standard_title", "limit_value", "unit", "description"]
                ].rename(
                    columns={
                        "standard_title": "标准名称",
                        "limit_value": "排放限值",
                        "unit": "单位",
                        "description": "说明",
                    }
                )
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("该因子暂无限值数据")


# ==================== 环保新闻页面 ====================
elif menu == "📰 环保新闻":
    st.title("📰 环保新闻")

    news = query_db(
        "SELECT * FROM news_items ORDER BY published_at DESC LIMIT 50"
    )
    st.markdown(f"**最近 {len(news)} 条新闻**")

    for item in news:
        st.markdown("---")
        st.markdown(f"### {item['title']}")
        pub = str(item['published_at'][:10]) if item['published_at'] else ""
        st.caption(f"来源: {item.get('source', '')} | 发布: {pub}")
        if item.get("summary"):
            st.markdown(item["summary"])
        if item.get("url"):
            st.markdown(f"📄 [查看原文]({item['url']})")


# ==================== 数据统计页面 ====================
elif menu == "📊 数据统计":
    st.title("📊 数据统计")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("标准总数", f"{total_std:,}")
    with col2:
        st.metric("污染因子", total_factors)
    with col3:
        st.metric("排放限值", total_limits)
    with col4:
        std_with_limits = query_db(
            "SELECT COUNT(DISTINCT standard_title) as c FROM pollution_limits"
        )[0]["c"]
        st.metric("含限值标准", std_with_limits)

    st.markdown("---")

    # 按类别统计
    st.markdown("### 按污染类别分布")
    cat_data = query_db(
        "SELECT category, COUNT(*) as count FROM standards GROUP BY category ORDER BY count DESC"
    )
    if cat_data:
        df_cat = pd.DataFrame(cat_data)
        st.bar_chart(df_cat.set_index("category"))

    # 按行业统计
    st.markdown("### 按适用行业分布 (Top 15)")
    ind_data = query_db(
        "SELECT industry, COUNT(*) as count FROM standards GROUP BY industry ORDER BY count DESC LIMIT 15"
    )
    if ind_data:
        df_ind = pd.DataFrame(ind_data)
        st.bar_chart(df_ind.set_index("industry"))

    # 按标准类型统计
    st.markdown("### 按标准类型分布")
    type_data = query_db(
        "SELECT standard_type, COUNT(*) as count FROM standards GROUP BY standard_type ORDER BY count DESC"
    )
    if type_data:
        df_type = pd.DataFrame(type_data)
        st.dataframe(df_type.rename(columns={"standard_type": "标准类型", "count": "数量"}), 
                     use_container_width=True, hide_index=True)
