"""
高考志愿填报建议 - Streamlit Web应用
功能: 输入分数/位次 → 冲/稳/保三档院校推荐
含: 免责声明 + 用户注册登录 + 免费/VIP分级
"""

import streamlit as st
import pandas as pd
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
from engine import recommend, get_available_years, get_major_categories
from auth import register_user, login_user, get_user, increment_query, get_tier_limits

st.set_page_config(page_title="高考志愿填报助手", page_icon="🎓", layout="wide")

# ============================================================
# Session state
# ============================================================
if 'user' not in st.session_state:
    st.session_state.user = None
if 'auth_mode' not in st.session_state:
    st.session_state.auth_mode = 'login'  # login / register

# ============================================================
# 免责声明 — 全局醒目
# ============================================================
st.markdown("""
<div style="
    background: linear-gradient(135deg, #fff3e0, #ffe0b2);
    border-left: 5px solid #ff6d00;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 16px;
    font-size: 0.92em;
    line-height: 1.6;
">
<strong style="color:#e65100;">⚠️ 重要免责声明</strong><br>
本工具基于公开历史数据提供<strong>参考性</strong>志愿填报建议，<strong>不构成任何报考决策依据</strong>。
院校录取分数线受当年招生计划、报考人数、政策调整等多重因素影响，实际录取结果可能与推荐存在偏差。
<strong>最终志愿填报请以各省教育考试院官方发布信息为准。</strong>
使用本工具即表示您已理解并接受上述风险，开发者不承担因参考本工具建议而产生的任何后果。
</div>
""", unsafe_allow_html=True)

# ============================================================
# 样式
# ============================================================
st.markdown("""
<style>
    .big-title { font-size: 2.0em; font-weight: 700; text-align: center; margin-bottom: 0; }
    .sub-title { color: #888; text-align: center; margin-bottom: 1.5em; font-size: 0.95em; }
    .vip-badge { 
        background: linear-gradient(135deg, #ffd700, #ff8c00); color: #333; 
        padding: 3px 12px; border-radius: 20px; font-size: 0.75em; font-weight: 700; 
    }
    .free-badge { 
        background: #e0e0e0; color: #666; 
        padding: 3px 12px; border-radius: 20px; font-size: 0.75em; 
    }
    .disclaimer-inline {
        background: #fff8e1; border: 1px solid #ffcc02; border-radius: 6px;
        padding: 8px 12px; margin: 8px 0; font-size: 0.82em; color: #795548;
    }
    .locked { opacity: 0.5; pointer-events: none; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 标题
# ============================================================
st.markdown('<div class="big-title">🎓 高考志愿填报助手</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">位次法 + 线差法 · 冲 / 稳 / 保 智能推荐 · 31省3329校</div>', unsafe_allow_html=True)

# ============================================================
# 侧边栏
# ============================================================
with st.sidebar:
    # ── 登录/注册 ──
    st.header("👤 账户")
    
    if st.session_state.user:
        user = st.session_state.user
        tier_label = "⭐ VIP会员" if user['tier'] == 'vip' else "🔓 免费用户"
        st.success(f"{tier_label}\n{user['email']}")
        
        limits = get_tier_limits(user['tier'])
        st.caption(f"今日剩余查询: {limits['max_queries'] - user['query_count']}次")
        
        if st.button("退出登录", use_container_width=True):
            st.session_state.user = None
            st.rerun()
    else:
        tab1, tab2 = st.tabs(["登录", "注册"])
        
        with tab1:
            login_email = st.text_input("邮箱", key="login_email", placeholder="your@email.com")
            login_pw = st.text_input("密码", type="password", key="login_pw")
            if st.button("登录", use_container_width=True):
                user, err = login_user(login_email, login_pw)
                if err:
                    st.error(err)
                else:
                    st.session_state.user = user
                    st.rerun()
        
        with tab2:
            reg_email = st.text_input("邮箱", key="reg_email", placeholder="your@email.com")
            reg_pw = st.text_input("密码(6位以上)", type="password", key="reg_pw")
            if st.button("注册", use_container_width=True):
                if len(reg_pw) < 6:
                    st.error("密码至少6位")
                elif '@' not in reg_email:
                    st.error("请输入有效的邮箱")
                else:
                    user, err = register_user(reg_email, reg_pw)
                    if err:
                        st.error(err)
                    else:
                        st.session_state.user = user
                        st.success("注册成功！免费用户可查询5次")
                        st.rerun()
    
    st.markdown("---")
    
    # ── VIP 升级 ──
    if st.session_state.user and st.session_state.user['tier'] == 'free':
        with st.expander("💰 升级VIP"):
            st.markdown("""
            **VIP特权 (¥39.9/季):**
            - ✅ 每档20所院校推荐
            - ✅ 专业录取详情
            - ✅ 位次对比分析
            - ✅ 导出PDF报告
            - ✅ 无限次查询
            
            [点击升级](https://example.com/pay) *(支付接入中)*
            """)
    
    st.markdown("---")
    
    # ── 输入区 ──
    st.header("📋 输入成绩")
    
    comprehensive = {"北京","天津","上海","浙江","山东","海南"}
    phys_hist = {"河北","辽宁","江苏","福建","湖北","湖南","广东","重庆"}
    
    province = st.selectbox("省份", sorted(list(comprehensive | phys_hist | {
        "河南","四川","山西","内蒙古","吉林","黑龙江","安徽","江西",
        "广西","贵州","云南","西藏","陕西","甘肃","青海","宁夏","新疆"
    })))
    
    if province in comprehensive:
        cat_opts = ["综合"]; default_cat = "综合"
    elif province in phys_hist:
        cat_opts = ["物理类","历史类"]; default_cat = "物理类"
    else:
        cat_opts = ["理科","文科"]; default_cat = "理科"
    
    category = st.selectbox("科类", cat_opts, index=cat_opts.index(default_cat))
    
    col1, col2 = st.columns(2)
    with col1:
        score = st.number_input("分数", 0, 750, 580)
    with col2:
        rank = st.number_input("位次", 0, 9999999, 30000)
    
    major_cats = ["不限"] + get_major_categories()
    selected_major = st.selectbox("专业方向(可选)", major_cats)
    major_filter = None if selected_major == "不限" else selected_major
    
    st.caption("📊 2023-2025批次线 · 3329所院校 · 9大门类35专业")
    
    search_btn = st.button("🔍 开始推荐", type="primary", use_container_width=True)

# ============================================================
# 主区域
# ============================================================
if search_btn:
    # 未登录用户也允许1次试用
    user = st.session_state.user
    limits = get_tier_limits(user['tier'] if user else 'free')
    
    if user and user['query_count'] >= limits['max_queries']:
        st.warning("免费查询次数已用完，请升级VIP继续使用")
    else:
        with st.spinner("正在分析..."):
            result = recommend(score, rank, province, category, major_category=major_filter)
        
        if user:
            increment_query(user['id'])
            st.session_state.user = get_user(user['id'])
        
        if "error" in result:
            st.error(result["error"])
        else:
            info = result["my_info"]
            s = result["summary"]
            top_n = limits['top_n']
            show_majors = limits['show_majors']
            
            # ── 考生信息卡 ──
            st.markdown("### 📊 你的位置")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("分数", f"{info['score']}分")
            c2.metric("位次", f"{info['rank']:,}")
            c3.metric("批次", info['batch'])
            c4.metric("批次线", f"{info['batch_line']}分")
            c5.metric("线差", f"+{info['score'] - info['batch_line']}分")
            
            # ── 概览 ──
            st.markdown("### 🎯 推荐概览")
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("🔴 冲", f"{s['冲']} 所", help="录取概率较低")
            mc2.metric("🔵 稳", f"{s['稳']} 所", help="录取概率较高")
            mc3.metric("🟢 保", f"{s['保']} 所", help="录取概率很高")
            
            st.markdown("---")
            
            # ── 免费用户限制提示 ──
            if not show_majors:
                st.info("🔓 免费版每档显示3所 · 专业详情仅VIP可见 · 升级查看全部")
            
            # ── 推荐表 ──
            def render_table(label, data, show_majors_detail, max_rows):
                if not data:
                    st.info(f"{label} 暂无数据")
                    return
                
                st.markdown(f"### {label} ({len(data)}所)")
                
                rows = []
                for d in data[:max_rows]:
                    row = {
                        "院校": d["name"], "层次": d["level"], "城市": d["city"],
                        "近3年均分": f"{d['uni_avg_score']}",
                        "综合分": f"{d['composite']:.0f}",
                    }
                    if show_majors_detail:
                        row["🟢可报专业"] = ", ".join(d.get("majors_bao", [])) or "-"
                        row["🔵边缘专业"] = ", ".join(d.get("majors_wen", [])) or "-"
                    rows.append(row)
                
                df = pd.DataFrame(rows)
                st.dataframe(df, hide_index=True, use_container_width=True)
                
                if len(data) > max_rows:
                    st.caption(f"仅显示前{max_rows}所，共{len(data)}所。升级VIP查看全部")
            
            render_table("🔴 冲", result["冲"], show_majors, top_n)
            render_table("🔵 稳", result["稳"], show_majors, top_n)
            render_table("🟢 保", result["保"], show_majors, top_n)
            
            # ── 每次推荐都跟免责 ──
            st.markdown("---")
            st.warning("⚠️ 以上推荐基于历史数据估算，仅供参考。实际录取受当年招生计划、报考热度、政策调整等多重因素影响，请以各省教育考试院官方发布为准。")

elif not search_btn:
    st.info("👈 在左侧输入分数和位次，点击「开始推荐」查看结果")
    st.markdown("""
    ### 🧠 算法说明
    **位次法** (权重60%): 比较你的全省位次与院校历年录取位次
    **线差法** (权重40%): 比较你的分数-批次线差值与院校线差
    
    ### 📊 数据说明
    - 覆盖31省份2023-2025年批次线
    - 收录3329所高等院校(含本科/专科)
    - 35个热门专业方向匹配
    - 位次基于部分省份真实一分一段表
    
    ### 💰 免费 vs VIP
    | 功能 | 免费 | VIP(¥39.9/季) |
    |------|------|---------------|
    | 院校推荐 | 每档3所 | 每档20所 |
    | 专业详情 | ✗ | ✓ |
    | 位次对比 | ✗ | ✓ |
    | 导出报告 | ✗ | ✓ |
    | 查询次数 | 5次 | 不限 |
    """)
