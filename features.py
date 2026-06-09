"""
增强功能模块: 录取概率 + 志愿方案生成 + 院校对比 + PDF报告
"""

import os, datetime
from database import get_db

# ============================================================
# 1. 录取概率估算
# ============================================================
def estimate_probability(composite, batch):
    """将综合评分映射为录取概率百分比"""
    if composite >= 90:
        return 95, "极高"
    elif composite >= 80:
        return 88, "很高"
    elif composite >= 70:
        return 75, "较高"
    elif composite >= 60:
        return 60, "中等"
    elif composite >= 50:
        return 45, "偏低"
    elif composite >= 40:
        return 30, "较低"
    elif composite >= 30:
        return 18, "很低"
    else:
        return 8, "极低"

# ============================================================
# 2. 志愿方案生成器（增强版）
# ============================================================
def generate_plan(result, province, category, score):
    """生成完整志愿方案，含专业级分析"""
    my_rank = result["my_info"].get("rank", 0)
    batch = result["my_info"]["batch"]
    batch_line = result["my_info"]["batch_line"]
    
    plan = {
        "province": province, "category": category, "score": score,
        "rank": my_rank, "batch": batch, "batch_line": batch_line,
        "line_diff": score - batch_line,
        "冲": [], "稳": [], "保": [], "total_schools": 0,
        "analysis": {},
    }
    
    def build_entry(s, tag):
        prob, label = estimate_probability(s["composite"], batch)
        rank_gap = (s.get("uni_avg_rank") or 0) - my_rank
        rank_desc = f"位次领先{abs(rank_gap):,}" if rank_gap > 0 else f"位次落后{abs(rank_gap):,}" if rank_gap < 0 else "位次持平"
        
        # 专业级分析
        all_majors = []
        for mlist, mtag in [(s.get("majors_bao",[]), "🟢"), (s.get("majors_wen",[]), "🔵"), (s.get("majors_chong",[]), "🔴")]:
            for m in mlist[:4]:
                all_majors.append(f"{mtag}{m}")
        
        return {
            "name": s["name"], "level": s["level"], "city": s["city"],
            "type": s.get("type",""), "is_public": s.get("is_public", True),
            "score": s["uni_avg_score"], "rank": s.get("uni_avg_rank"),
            "composite": s["composite"], "probability": prob, "prob_label": label,
            "rank_gap": rank_gap, "rank_desc": rank_desc,
            "score_gap": score - s["uni_avg_score"],
            "majors": s.get("majors_bao", [])[:3] if s.get("majors_bao") else [],
            "all_majors_analyzed": all_majors[:8],
            "advantage_majors": s.get("advantage_majors", [])[:5],
            "category_tag": tag,
        }
    
    # 冲: 综合分最低、最难、但最值得冲刺
    chong_sorted = sorted(result.get("冲", []), key=lambda x: x["composite"])
    for s in chong_sorted[:3]:
        plan["冲"].append(build_entry(s, "冲"))
    
    # 稳: 中间段
    wen_sorted = sorted(result.get("稳", []), key=lambda x: x["composite"])
    mid = max(0, len(wen_sorted)//2 - 2)
    for s in wen_sorted[mid:mid+5]:
        plan["稳"].append(build_entry(s, "稳"))
    
    # 保: 综合分最高
    bao_sorted = sorted(result.get("保", []), key=lambda x: x["composite"], reverse=True)
    for s in bao_sorted[:3]:
        plan["保"].append(build_entry(s, "保"))
    
    plan["total_schools"] = len(plan["冲"]) + len(plan["稳"]) + len(plan["保"])
    
    # 方案分析
    avg_prob = 0; count = 0
    for tag in ["冲","稳","保"]:
        for s in plan[tag]:
            avg_prob += s["probability"]; count += 1
    avg_prob = avg_prob / count if count > 0 else 0
    
    plan["analysis"] = {
        "avg_probability": round(avg_prob),
        "冲_count": len(plan["冲"]), "稳_count": len(plan["稳"]), "保_count": len(plan["保"]),
        "strategy": "激进型" if len(plan["冲"]) >= 5 else ("保守型" if len(plan["保"]) >= 5 else "均衡型"),
        "tip": "冲稳保分布合理，整体录取概率较高" if avg_prob >= 60 else "建议增加保底院校数量，降低风险",
    }
    
    return plan

# ============================================================
# 3. 院校对比数据（增强版）
# ============================================================
def get_school_detail(school_name):
    """获取院校详细信息"""
    conn = get_db()
    uni = conn.execute("SELECT * FROM universities WHERE name=?", (school_name,)).fetchone()
    if not uni:
        return None
    
    # 录取趋势 (3年)
    admissions = conn.execute("""
        SELECT province, year, category, batch, min_score, min_rank
        FROM admission_scores WHERE university_id=?
        ORDER BY year DESC, min_score DESC
    """, (uni['id'],)).fetchall()
    
    # 按年份聚合
    yearly = {}
    for a in admissions:
        y = a['year']
        if y not in yearly:
            yearly[y] = {"scores": [], "ranks": []}
        yearly[y]["scores"].append(a['min_score'])
        yearly[y]["ranks"].append(a['min_rank'])
    
    trend = {}
    for y in sorted(yearly.keys(), reverse=True)[:3]:
        sc = yearly[y]["scores"]
        rk = yearly[y]["ranks"]
        trend[y] = {
            "avg_score": round(sum(sc)/len(sc)) if sc else None,
            "avg_rank": round(sum(rk)/len(rk)) if rk else None,
        }
    
    # 优势专业 (全部)
    majors = conn.execute("""
        SELECT m.name, m.category, m.employment_score, m.avg_salary, m.difficulty_offset, m.description
        FROM uni_majors um JOIN majors m ON um.major_id=m.id
        WHERE um.university_id=? AND um.is_advantage=1
        ORDER BY m.employment_score DESC
    """, (uni['id'],)).fetchall()
    
    
    # 院校标签
    tags = []
    if uni['level'] == '985': tags.append("🏆985")
    if uni['level'] == '211': tags.append("📘211")
    if uni['level'] == '双一流': tags.append("⭐双一流")
    if uni['level'] == '省重点': tags.append("📌省重点")
    if uni['is_public']: tags.append("🏛公办")
    else: tags.append("🏢民办")
    
    # 竞争力指标 (近似)
    all_scores = [a['min_score'] for a in admissions if a['min_score']]
    competitiveness = "极高" if any(s >= 650 for s in all_scores) else \
                       "很高" if any(s >= 600 for s in all_scores) else \
                       "较高" if any(s >= 550 for s in all_scores) else \
                       "中等" if any(s >= 450 for s in all_scores) else "一般"
    
    return {
        "name": uni['name'], "level": uni['level'], "type": uni['type'],
        "city": uni['city'], "is_public": bool(uni['is_public']),
        "tags": tags, "competitiveness": competitiveness,
        "majors": [dict(m) for m in majors],
        "trend": trend,
    }

# ============================================================
# 对比摘要
# ============================================================
def compare_schools(school_names):
    """对比多所院校并生成摘要"""
    details = []
    for name in school_names:
        d = get_school_detail(name)
        if d: details.append(d)
    
    if len(details) < 2:
        return details, None
    
    # 找最容易进的
    easiest = max(details, key=lambda d: d['trend'].get(2024,{}).get('avg_rank',0) or 0)
    hardest = min(details, key=lambda d: d['trend'].get(2024,{}).get('avg_rank',0) or 9999999)
    
    # 就业最好
    best_employ = max(details, key=lambda d: max((m['employment_score'] for m in d['majors']), default=0))
    
    summary = {
        "easiest": easiest['name'],
        "hardest": hardest['name'],
        "best_employment": best_employ['name'],
        "comparison_text": f"最容易进: {easiest['name']} | 最难进: {hardest['name']} | 就业最优: {best_employ['name']}"
    }
    
    return details, summary

# ============================================================
# 4. PDF报告生成
# ============================================================
def generate_pdf_report(plan, user_info, output_path):
    """生成志愿填报方案PDF报告 (fpdf2)"""
    from fpdf import FPDF
    
    pdf = FPDF()
    pdf.add_page()
    
    # 注册中文字体 (使用系统字体)
    font_dir = "C:/Windows/Fonts"
    font_regular = os.path.join(font_dir, "msyh.ttc")
    font_bold = os.path.join(font_dir, "msyhbd.ttc")
    
    if os.path.exists(font_regular):
        pdf.add_font("CN", "", font_regular, uni=True)
        pdf.add_font("CN", "B", font_bold if os.path.exists(font_bold) else font_regular, uni=True)
    else:
        # Fallback: use built-in (no CJK) — will show as empty, add warning
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 10, "Font not found - report generated without Chinese chars", ln=True)
        pdf.output(output_path)
        return output_path
    
    date_str = datetime.date.today().strftime("%Y年%m月%d日")
    
    # ── 标题 ──
    pdf.set_font("CN", "B", 20)
    pdf.cell(0, 12, "高考志愿填报方案", ln=True, align="C")
    pdf.set_font("CN", "", 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, f"{plan['province']} · {plan['category']} · {plan['score']}分", ln=True, align="C")
    pdf.cell(0, 6, f"生成日期: {date_str}", ln=True, align="C")
    pdf.ln(6)
    
    # ── 免责 ──
    pdf.set_draw_color(255, 150, 0)
    pdf.set_fill_color(255, 248, 225)
    pdf.rect(10, pdf.get_y(), 190, 22, "DF")
    pdf.set_xy(12, pdf.get_y() + 2)
    pdf.set_font("CN", "B", 9)
    pdf.set_text_color(200, 80, 0)
    pdf.cell(0, 6, "⚠️ 重要提示：本报告基于历史数据提供参考性建议，不构成报考决策依据。", ln=True)
    pdf.set_x(12)
    pdf.cell(0, 6, "最终志愿填报请以各省教育考试院官方发布信息为准。", ln=True)
    pdf.ln(8)
    
    # ── 考生信息 ──
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("CN", "B", 14)
    pdf.cell(0, 10, "一、考生信息", ln=True)
    pdf.set_font("CN", "", 10)
    info = user_info
    items = [
        ("省份", info.get('province','')), ("科类", info.get('category','')),
        ("分数", f"{info.get('score','')}分"), ("位次", f"{info.get('rank',0):,}"),
        ("批次", info.get('batch','')), ("批次线", f"{info.get('batch_line','')}分"),
        ("线差", f"+{info.get('score',0) - info.get('batch_line',0)}分"),
    ]
    for label, value in items:
        pdf.cell(40, 7, f"  {label}:", ln=False)
        pdf.set_font("CN", "B", 10)
        pdf.cell(60, 7, value, ln=True)
        pdf.set_font("CN", "", 10)
    pdf.ln(4)
    
    # ── 推荐方案 ──
    for tag, emoji, desc in [("冲","🔴","录取概率较低，值得冲刺"),
                              ("稳","🔵","与你的位次匹配度较高"),
                              ("保","🟢","录取概率很高，确保有学上")]:
        pdf.set_font("CN", "B", 13)
        pdf.cell(0, 9, f"{emoji} 二.{'一二三'[['冲','稳','保'].index(tag)]} 冲刺院校" if tag=="冲" else f"{emoji} {'二三四'[['冲','稳','保'].index(tag)]}. {'冲刺' if tag=='冲' else '稳妥' if tag=='稳' else '保底'}院校", ln=True)
        pdf.set_font("CN", "", 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, desc, ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        
        if not plan.get(tag):
            pdf.cell(0, 7, "  （无推荐）", ln=True)
            continue
        
        # 表头
        pdf.set_fill_color(26, 115, 232)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("CN", "B", 8)
        col_widths = [48, 16, 20, 18, 16, 22, 46]
        headers = ["院校", "层次", "城市", "录取分", "综合分", "概率", "推荐专业"]
        for i, (h, w) in enumerate(zip(headers, col_widths)):
            pdf.cell(w, 7, h, border=1, fill=True, align="C")
        pdf.ln()
        pdf.set_text_color(0, 0, 0)
        
        # 数据行
        pdf.set_font("CN", "", 8)
        for s in plan[tag]:
            row = [
                s['name'][:12], s['level'][:6], s['city'][:6],
                str(s['score']), f"{s['composite']:.0f}",
                f"{s.get('probability','?')}%",
                (', '.join(s.get('majors',[])))[:30] if s.get('majors') else '-'
            ]
            for val, w in zip(row, col_widths):
                pdf.cell(w, 7, val, border=1, align="C")
            pdf.ln()
        pdf.ln(3)
    
    # ── 使用建议 ──
    pdf.set_font("CN", "B", 13)
    pdf.cell(0, 9, "五、使用建议", ln=True)
    pdf.set_font("CN", "", 9)
    tips = [
        "冲(2-3所): 选最喜欢的2-3所冲刺校，不要全填冲刺",
        "稳(3-5所): 选3-5所匹配校，这是最可能被录取的区间",
        "保(2-3所): 选2-3所保底校，确保万无一失",
        "最终志愿需结合专业兴趣、城市偏好、招生计划等因素综合决策",
    ]
    for tip in tips:
        pdf.cell(4, 6, "•", ln=False)
        pdf.cell(0, 6, tip, ln=True)
    
    # ── 页脚 ──
    pdf.ln(8)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("CN", "", 7)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, f"AI辅助生成 · {date_str} · 仅供参考，不构成报考建议", align="C", ln=True)
    
    pdf.output(output_path)
    return output_path
