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
from features import estimate_probability, generate_plan, get_school_detail, generate_pdf_report

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
        limits = get_tier_limits(user['tier'])
        tier_emoji = {"free":"🔓","enhanced":"🔵","complete":"👑"}.get(user['tier'],"🔓")
        st.success(f"{tier_emoji} {limits['name']}\n{user['email']}")
        
        st.caption(f"已用查询: {user['query_count']}/{limits['max_queries']}次" if limits['max_queries'] < 9999 else f"已用查询: {user['query_count']}次(不限)")
        
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
    
    # ── 升级面板 ──
    if st.session_state.user and st.session_state.user['tier'] != 'complete':
        current_tier = st.session_state.user['tier']
        with st.expander("💰 升级版本"):
            if current_tier == 'free':
                st.markdown("""
                **🔵 增强版 ¥29.9（买断·永久）**
                - ✅ 每档10所院校推荐（vs 免费版3所）
                - ✅ 专业录取详情（可报/边缘/冲刺）
                - ✅ 位次对比分析
                - ✅ 导出PDF报考方案
                - ✅ 30次完整查询
                """)
                st.markdown("""
                **👑 完全版 ¥59.9（买断·永久）**
                - ✅ 增强版全部功能
                - ✅ 每档20所院校推荐
                - ✅ 不限次数查询
                - ✅ 专业就业数据（薪资/评分）
                - ✅ 历年趋势对比
                - ✅ 优先数据更新
                """)
            elif current_tier == 'enhanced':
                st.markdown("""
                **👑 完全版 ¥30（增强版补差价升级）**
                - ✅ 每档20所院校（vs 增强版10所）
                - ✅ 不限次数查询
                - ✅ 专业就业数据（薪资/评分）
                - ✅ 历年趋势对比
                """)
            st.caption("💳 支付接入中，暂可联系管理员手动开通")
    
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
            
            # ── 推荐表(含概率) ──
            def render_table(label, data, show_majors_detail, max_rows):
                if not data:
                    st.info(f"{label} 暂无数据")
                    return
                
                st.markdown(f"### {label} ({len(data)}所)")
                
                rows = []
                for d in data[:max_rows]:
                    prob, prob_label = estimate_probability(d['composite'], info['batch'])
                    row = {
                        "院校": d["name"], "层次": d["level"], "城市": d["city"],
                        "近3年均分": f"{d['uni_avg_score']}",
                        "综合分": f"{d['composite']:.0f}",
                        "录取概率": f"{prob}%",
                    }
                    if show_majors_detail:
                        row["🟢可报专业"] = ", ".join(d.get("majors_bao", [])) or "-"
                    rows.append(row)
                
                df = pd.DataFrame(rows)
                st.dataframe(df, hide_index=True, use_container_width=True)
                
                if len(data) > max_rows:
                    st.caption(f"仅显示前{max_rows}所，共{len(data)}所。升级版本查看全部")
            
            render_table("🔴 冲", result["冲"], show_majors, top_n)
            render_table("🔵 稳", result["稳"], show_majors, top_n)
            render_table("🟢 保", result["保"], show_majors, top_n)
            
            # ── 每次推荐都跟免责 ──
            st.markdown("---")
            
            # ── 志愿方案生成器 ──
            if show_majors:
                st.markdown("### 📋 一键生成志愿方案")
                if st.button("🎯 生成我的志愿填报方案", type="secondary"):
                    plan = generate_plan(result, province, category, score)
                    st.session_state['plan'] = plan
                    
                    col_a, col_b, col_c = st.columns(3)
                    for col, tag, emoji in [(col_a,"冲","🔴"), (col_b,"稳","🔵"), (col_c,"保","🟢")]:
                        with col:
                            st.markdown(f"**{emoji} {tag}**")
                            for s in plan[tag]:
                                st.markdown(f"- **{s['name']}** ({s['level']})\n  {s['city']} · {s['score']}分 · 概率{s['probability']}%")
                    
                    # PDF导出
                    if limits.get('export'):
                        output = os.path.join(os.path.dirname(__file__), f"志愿方案_{province}_{category}_{score}分.docx")
                        generate_pdf_report(plan, info, output)
                        with open(output, "rb") as f:
                            st.download_button("📥 下载PDF报告", f, file_name=f"志愿方案_{province}_{category}_{score}分.docx")
            
            # ── 院校对比 ──
            if show_majors:
                st.markdown("---")
                st.markdown("### 🔍 院校对比")
                all_names = [s['name'] for s in (result.get('冲',[]) + result.get('稳',[]) + result.get('保',[]))[:50]]
                compare_schools = st.multiselect("选择2-3所院校对比", all_names, max_selections=3)
                
                if compare_schools:
                    cols = st.columns(len(compare_schools))
                    for i, name in enumerate(compare_schools):
                        detail = get_school_detail(name)
                        if detail:
                            with cols[i]:
                                st.markdown(f"**{detail['name']}**")
                                st.caption(f"{detail['level']} · {detail['city']} · {'公办' if detail['is_public'] else '民办'}")
                                st.caption(f"类型: {detail['type']}")
                                if detail['majors']:
                                    st.caption("优势专业:")
                                    for m in detail['majors'][:3]:
                                        st.caption(f"  {m['name']} (就业{m['employment_score']}分 ¥{m['avg_salary']:,})")
            
            # 免责
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
    
    ### 💰 三档定价（买断制·永久有效）
    | 功能 | 🔓 免费版 | 🔵 增强版 ¥29.9 | 👑 完全版 ¥59.9 |
    |------|-----------|----------------|----------------|
    | 院校推荐 | 每档3所 | 每档10所 | 每档20所 |
    | 专业详情 | ✗ | ✓ | ✓ |
    | 位次对比 | ✗ | ✓ | ✓ |
    | 导出报告 | ✗ | ✓ | ✓ |
    | 查询次数 | 3次 | 30次 | 不限 |
    | 就业数据 | ✗ | ✗ | ✓ |
    | 趋势对比 | ✗ | ✗ | ✓ |
    | 有效期限 | 永久 | **买断·永久** | **买断·永久** |
    """)
