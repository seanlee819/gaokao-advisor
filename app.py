"""
看金榜 · 高考志愿填报助手
免费版 · 位次法+线差法 · 冲/稳/保 · 31省3329校
"""
import streamlit as st
import pandas as pd
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
from engine import recommend, get_major_categories
from features import estimate_probability, generate_plan, generate_pdf_report, compare_schools

st.set_page_config(page_title="看金榜 · 高考志愿填报", page_icon="🎓", layout="wide")

# ── session state ──
for key, default in [("result",None), ("plan",None)]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── 免责声明 ──
st.markdown("""<div style="background:linear-gradient(135deg,#fff3e0,#ffe0b2);border-left:5px solid #ff6d00;border-radius:8px;padding:14px 18px;margin-bottom:16px;font-size:.92em;line-height:1.6">
<strong style="color:#e65100">⚠️ 重要免责声明</strong><br>
本工具基于公开历史数据提供<strong>参考性</strong>志愿填报建议，<strong>不构成任何报考决策依据</strong>。
最终志愿填报请以各省教育考试院官方发布信息为准。
</div>""", unsafe_allow_html=True)

st.markdown('<div style="font-size:2em;font-weight:700;text-align:center">🎓 看金榜</div>', unsafe_allow_html=True)
st.markdown('<div style="color:#888;text-align:center;margin-bottom:1.5em">位次法+线差法 · 冲/稳/保 智能推荐 · 31省3329校 · 2023-2026数据</div>', unsafe_allow_html=True)

# ── 侧边栏：输入 ──
with st.sidebar:
    st.header("📋 输入成绩")
    
    comprehensive = {"北京","天津","上海","浙江","山东","海南"}
    phys_hist = {"河北","辽宁","江苏","福建","湖北","湖南","广东","重庆"}
    all_provs = sorted(comprehensive|phys_hist|{"河南","四川","山西","内蒙古","吉林","黑龙江","安徽","江西","广西","贵州","云南","西藏","陕西","甘肃","青海","宁夏","新疆"})
    
    province = st.selectbox("省份", all_provs)
    if province in comprehensive: cats, dc = ["综合"], "综合"
    elif province in phys_hist: cats, dc = ["物理类","历史类"], "物理类"
    else: cats, dc = ["理科","文科"], "理科"
    category = st.selectbox("科类", cats, index=cats.index(dc))
    
    c1, c2 = st.columns(2)
    with c1: score = st.number_input("分数", 0, 750, 580)
    with c2: rank = st.number_input("位次", 0, 9999999, 30000)
    
    with st.expander("📝 单科成绩 (可选)", expanded=False):
        st.caption("填写单科成绩可筛查院校单科要求")
        sc1, sc2 = st.columns(2)
        with sc1:
            subj_math = st.number_input("数学", 0, 150, 0, key="sub_math")
            subj_eng = st.number_input("英语", 0, 150, 0, key="sub_eng")
            subj_chinese = st.number_input("语文", 0, 150, 0, key="sub_chi")
        with sc2:
            subj_chem = st.number_input("化学", 0, 150, 0, key="sub_chem")
            subj_bio = st.number_input("生物", 0, 150, 0, key="sub_bio")
        subject_scores = {}
        for k, v in [("数学", subj_math), ("英语", subj_eng), ("语文", subj_chinese), ("化学", subj_chem), ("生物", subj_bio)]:
            if v > 0: subject_scores[k] = v
    if not any([subj_math, subj_eng, subj_chinese, subj_chem, subj_bio]):
        subject_scores = None
    
    major_cats = ["不限"] + get_major_categories()
    major_choice = st.selectbox("专业方向", major_cats)
    major_filter = None if major_choice == "不限" else major_choice
    
    st.caption("📊 2023-2026批次线 · 3329校 · 31省")
    search_btn = st.button("🔍 开始推荐", type="primary", use_container_width=True)

# ── 主区域 ──
if search_btn:
    with st.spinner("分析中..."):
        st.session_state.result = recommend(score, rank, province, category, major_filter, my_subject_scores=subject_scores)
        st.session_state.plan = None  # reset plan

if st.session_state.result:
    result = st.session_state.result
    top_n = 20
    
    if "error" in result:
        st.error(result["error"])
    else:
        info = result["my_info"]; s = result["summary"]
        
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("分数", f"{info['score']}分"); c2.metric("位次", f"{info['rank']:,}")
        c3.metric("批次", info['batch']); c4.metric("批次线", f"{info['batch_line']}分")
        c5.metric("线差", f"+{info['score']-info['batch_line']}分")
        
        mc1,mc2,mc3 = st.columns(3)
        mc1.metric("🔴 冲", f"{s['冲']}所"); mc2.metric("🔵 稳", f"{s['稳']}所"); mc3.metric("🟢 保", f"{s['保']}所")
        
        filtered = s.get("filtered_by_policy", 0)
        if filtered > 0:
            st.caption(f"⚠️ {filtered} 所院校因单科不达标被过滤")
        
        st.markdown("---")
        
        for tag, label in [("冲","🔴 冲刺"), ("稳","🔵 稳妥"), ("保","🟢 保底")]:
            data = result.get(tag, [])
            if not data: st.info(f"{label} 暂无"); continue
            st.markdown(f"### {label} ({len(data)}所)")
            rows = []
            for d in data[:top_n]:
                prob, _ = estimate_probability(d['composite'], info['batch'])
                policy = d.get("policy", {})
                rule = policy.get("admission_rule", "")
                rule_labels = {"分数清":"分数优先","专业级差":"级差录取","专业清":"专业优先"}
                rule_display = rule_labels.get(rule, rule)
                rule_badge = {"分数清":"📊","专业级差":"⚠️","专业清":"🔴"}.get(rule, "")
                risks = d.get("policy_risks", [])
                risk_tags = []
                for r in risks:
                    if r["level"] == "critical": risk_tags.append("🚫")
                    elif r["level"] == "high": risk_tags.append("⚠️")
                risk_str = " ".join(risk_tags) if risk_tags else ""
                subj_reqs = policy.get("subject_requirements", {})
                subj_str = ", ".join(f"{k}≥{v}" for k, v in subj_reqs.items()) if subj_reqs else "-"
                
                row = {"院校":d['name'],"层次":d['level'],"城市":d['city'],
                       "均分":f"{d['uni_avg_score']}","综合":f"{d['composite']:.0f}","概率":f"{prob}%",
                       "录取规则":f"{rule_badge} {rule_display}","单科要求": subj_str}
                if d.get("filtered_by_policy"): row["院校"] = f"🚫 {d['name']}"
                if major_filter: row["专业"] = "✅" if d.get("major_match") else "➖"
                row["🟢可报"] = ", ".join(d.get("majors_bao",[])) or "-"
                if risk_str: row["风险"] = risk_str
                rows.append(row)
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
            if len(data) > top_n:
                st.caption(f"显示前{top_n}所，共{len(data)}所")
        
        # 志愿方案
        st.markdown("---"); st.markdown("### 📋 志愿方案生成器")
        if st.button("🎯 生成我的志愿方案", type="secondary"):
            st.session_state.plan = generate_plan(result, info['province'], info['category'], info['score'])
        
        if st.session_state.plan:
            plan = st.session_state.plan
            a = plan.get("analysis", {})
            st.info(f"📊 方案分析: {a.get('strategy','')} · 平均录取概率{a.get('avg_probability','')}% · {a.get('tip','')}")
            for col, tag, emoji in zip(st.columns(3), ["冲","稳","保"], ["🔴","🔵","🟢"]):
                with col:
                    st.markdown(f"**{emoji} {tag}**")
                    for s in plan[tag]:
                        with st.expander(f"{s['name']} ({s['level']})"):
                            st.markdown(f"📍 {s['city']} · {s['type']}")
                            st.markdown(f"📊 均分{s['score']} · 综合{s['composite']:.0f} · 概率{s['probability']}%")
                            st.markdown(f"📈 {s['rank_desc']} · 分差{s['score_gap']:+d}")
                            if s.get('majors'): st.markdown(f"🎯 推荐: {', '.join(s['majors'])}")
                            if s.get('policy'):
                                p = s['policy']
                                rule_map = {"分数清":"📊 分数优先 — 高分考生先挑专业，最安全的模式",
                                            "专业级差":f"⚠️ 级差录取 — 每轮志愿递减{p.get('grade_diff','?')}分，前两个专业最关键",
                                            "专业清":"🔴 专业优先 — 第一志愿不录取就可能调剂，填报需谨慎"}
                                st.caption(rule_map.get(p.get('admission_rule',''), p.get('admission_rule','')))
                                if p.get('subject_requirements'): st.caption(f"📝 单科要求: {', '.join(f'{k}≥{v}' for k,v in p['subject_requirements'].items())}")
                                if p.get('special_plans'): st.caption(f"🎫 {' · '.join(p['special_plans'])}")
            
            pdf_path = os.path.join(os.path.dirname(__file__), f"志愿方案_{info['province']}_{info['score']}分.pdf")
            try:
                generate_pdf_report(plan, info, pdf_path)
                with open(pdf_path, "rb") as f:
                    st.download_button("📥 下载PDF报告", f, file_name=os.path.basename(pdf_path))
            except Exception as ex:
                st.error(f"PDF生成失败: {ex}")
        
        # 院校对比
        st.markdown("---"); st.markdown("### 🔍 院校对比")
        all_names = [s['name'] for s in (result.get('冲',[])+result.get('稳',[])+result.get('保',[]))[:50]]
        picks = st.multiselect("选2-3所对比", all_names, max_selections=3, key="compare")
        if picks:
            details, summary = compare_schools(picks)
            if summary: st.success(f"📊 {summary['comparison_text']}")
            if details:
                cols = st.columns(len(details))
                for i, d in enumerate(details):
                    with cols[i]:
                        st.markdown(f"### {d['name']}"); st.caption(" · ".join(d['tags']))
                        st.markdown(f"📍 {d['city']} | 竞争力: {d['competitiveness']}")
                        if d.get('trend'):
                            st.markdown("**📈 录取趋势:**")
                            for y, t in sorted(d['trend'].items(), reverse=True):
                                st.caption(f"  {y}: {t['avg_score']}分 / {t['avg_rank']:,}位" if t['avg_score'] else f"  {y}: -")
                        if d['majors']:
                            st.markdown("**🎯 优势专业:**")
                            for m in d['majors'][:5]:
                                st.caption(f"  {m['name']} 就业{m['employment_score']}分 ¥{m['avg_salary']:,}")
        
        st.markdown("---")
        st.warning("⚠️ 以上推荐基于历史数据估算，仅供参考。请以各省教育考试院官方发布为准。")

elif not search_btn:
    st.info("👈 左侧输入分数和位次，点击「开始推荐」")
    st.markdown("""
### 🧠 算法说明
**位次法**(权重60%): 比较全省位次与院校录取位次 · **线差法**(权重40%): 比较分数-批次线差值

### 🎓 完全免费 · 无需登录
所有功能直接使用：每档20所院校 · 专业详情 · 位次对比 · PDF报告 · 不限次数
    """)

# ── ICP备案 ──
st.markdown('<div style="text-align:center;padding:30px;color:#bbb;font-size:12px">豫ICP备2026027300号</div>', unsafe_allow_html=True)
