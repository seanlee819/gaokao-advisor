"""
高考志愿填报建议 - Streamlit Web应用
功能: 输入分数/位次 → 冲/稳/保三档院校推荐
"""

import streamlit as st
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from engine import recommend, get_available_years, get_major_categories
from database import get_db

st.set_page_config(
    page_title="高考志愿填报助手",
    page_icon="🎓",
    layout="wide",
)

# ============================================================
# 样式
# ============================================================
st.markdown("""
<style>
    .big-title { font-size: 2.2em; font-weight: 700; text-align: center; margin-bottom: 0; }
    .sub-title { color: #888; text-align: center; margin-bottom: 2em; font-size: 0.95em; }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px; padding: 20px; color: white; text-align: center;
    }
    .metric-card.chong { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    .metric-card.wen { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
    .metric-card.bao { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
    .tag-chong { background: #ff6b6b; color: white; padding: 2px 10px; border-radius: 12px; font-size: 0.8em; }
    .tag-wen { background: #339af0; color: white; padding: 2px 10px; border-radius: 12px; font-size: 0.8em; }
    .tag-bao { background: #51cf66; color: white; padding: 2px 10px; border-radius: 12px; font-size: 0.8em; }
    .school-row { padding: 12px; border-bottom: 1px solid #eee; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 标题
# ============================================================
st.markdown('<div class="big-title">🎓 高考志愿填报助手</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">位次法 + 线差法 · 冲 / 稳 / 保 智能推荐</div>', unsafe_allow_html=True)

# ============================================================
# 侧边栏 - 输入区
# ============================================================
with st.sidebar:
    st.header("📋 输入你的成绩")

    province = st.selectbox(
        "省份",
        ["北京","天津","河北","山西","内蒙古","辽宁","吉林","黑龙江",
         "上海","江苏","浙江","安徽","福建","江西","山东","河南",
         "湖北","湖南","广东","广西","海南","重庆","四川","贵州",
         "云南","西藏","陕西","甘肃","青海","宁夏","新疆"],
        help="选择你的高考省份"
    )

    # 根据省份显示科类
    comprehensive_provs = {"北京","天津","上海","浙江","山东","海南"}
    physical_history_provs = {"河北","辽宁","江苏","福建","湖北","湖南","广东","重庆"}
    
    if province in comprehensive_provs:
        cat_opts = ["综合"]
        default_cat = "综合"
    elif province in physical_history_provs:
        cat_opts = ["物理类","历史类"]
        default_cat = "物理类"
    else:
        cat_opts = ["理科","文科"]
        default_cat = "理科"

    category = st.selectbox("科类", cat_opts, index=cat_opts.index(default_cat))

    col1, col2 = st.columns(2)
    with col1:
        score = st.number_input("高考分数", min_value=0, max_value=750, value=580, step=1)
    with col2:
        rank = st.number_input("全省位次", min_value=0, max_value=9999999, value=30000, step=1,
                               help="一分一段表上的全省排名")

        # 专业偏好(可选)
        major_cats = ["不限"] + get_major_categories()
        major_choice = st.selectbox("专业方向(可选)", major_cats, index=0,
                                    help="选择偏好的专业门类，结果将只显示该门类有优势专业的院校")
        selected_major = None if major_choice == "不限" else major_choice

        st.markdown("---")
    st.caption("💡 位次比分数更稳定，建议优先参考位次")
    st.caption("📊 数据覆盖 2023-2025 年 8省批次线及 3,075 所院校录取线")
    st.caption("⚠️ 数据为模拟值，仅供参考，不构成实际报考建议")

    search_btn = st.button("🔍 开始推荐", type="primary", use_container_width=True)


# ============================================================
# 主区域 - 推荐结果
# ============================================================
if search_btn:
    with st.spinner("正在分析..."):
        result = recommend(score, rank, province, category, major_category=selected_major)

    if "error" in result:
        st.error(result["error"])
    else:
        info = result["my_info"]
        summary = result["summary"]

        # ── 考生信息卡片 ──
        st.markdown("### 📊 你的位置")
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("分数", f"{info['score']}分")
        with c2:
            st.metric("位次", f"{info['rank']:,}")
        with c3:
            st.metric("批次", info['batch'])
        with c4:
            st.metric("批次线", f"{info['batch_line']}分")
        with c5:
            st.metric("线差", f"+{info['score'] - info['batch_line']}分")

        # ── 三档统计 ──
        st.markdown("### 🎯 推荐概览")
        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            st.metric("🔴 冲 (可争取)", f"{summary['冲']} 所",
                     help="录取概率较低，但值得冲刺的院校")
        with mc2:
            st.metric("🔵 稳 (较匹配)", f"{summary['稳']} 所",
                     help="录取概率较高，与你的位次匹配")
        with mc3:
            st.metric("🟢 保 (稳录取)", f"{summary['保']} 所",
                     help="录取概率很高，确保有学上")

        st.markdown("---")

        # ── 详细推荐表 ──
        def render_table(label, data, tag_class):
            if not data:
                st.info(f"{label} 暂无数据")
                return

            st.markdown(f"### {label} ({len(data)}所)")

            df = pd.DataFrame([{
                "院校": d["name"],
                "层次": d["level"],
                "城市": d["city"],
                "近3年均分": f"{d['uni_avg_score']}",
                "线差": f"+{d['uni_diff']}",
                "综合分": f"{d['composite']:.0f}",
                "🟢 可报专业": ", ".join(d.get("majors_bao", [])) or "-",
                "🔵 边缘专业": ", ".join(d.get("majors_wen", [])) or "-",
                "🔴 冲刺专业": ", ".join(d.get("majors_chong", [])) or "-",
            } for d in data])

            # 用dataframe渲染
            st.dataframe(
                df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "院校": st.column_config.TextColumn(width="medium"),
                    "层次": st.column_config.TextColumn(width="small"),
                    "城市": st.column_config.TextColumn(width="small"),
                    "近3年均分": st.column_config.TextColumn(width="small"),
                    "线差": st.column_config.TextColumn(width="small"),
                    "综合分": st.column_config.TextColumn(width="small"),
                    "🟢 可报专业": st.column_config.TextColumn(width="large"),
                    "🔵 边缘专业": st.column_config.TextColumn(width="large"),
                    "🔴 冲刺专业": st.column_config.TextColumn(width="large"),
                }
            )

        render_table("🔴 冲 (Chance)", result["冲"], "chong")
        render_table("🔵 稳 (Target)", result["稳"], "wen")
        render_table("🟢 保 (Safety)", result["保"], "bao")

        # ── 提示 ──
        st.markdown("---")
        st.info("""
        **💡 使用建议**
        - **冲**: 选2-3所心仪的冲刺校，不要全填冲刺
        - **稳**: 选3-5所匹配校，这是最可能被录取的区间
        - **保**: 选2-3所保底校，确保万无一失
        - 最终志愿需结合兴趣专业、城市偏好、招生计划等因素综合决策
        """)

elif not search_btn:
    # 首次加载 - 显示说明
    st.info("👈 在左侧输入你的分数和位次，点击「开始推荐」查看结果")
    st.markdown("""
    ### 🧠 算法说明

    **位次法** (权重 60%): 比较你的全省位次与院校历年录取位次，位次越靠前越稳

    **线差法** (权重 40%): 比较你的分数与批次线的差值，对标院校历年线差

    **三档分类**:
    - 🔴 冲: 综合评分 < 35，难度较大
    - 🔵 稳: 综合评分 35-69，录取概率较高
    - 🟢 保: 综合评分 ≥ 70，几乎稳录

    **专业匹配**: 选择专业方向后，仅显示该门类有优势专业的院校，匹配院校额外+5分综合分
    """)
