"""
高考志愿填报 - 核心匹配引擎
算法: 位次法 + 线差法 综合评分
"""

from database import get_db


def get_province_lines(province, year, category):
    """获取某省某年某科类的批次线"""
    conn = get_db()
    rows = conn.execute(
        """SELECT batch, score, rank FROM province_lines
           WHERE province=? AND year=? AND category=?
           ORDER BY score DESC""",
        (province, year, category)
    ).fetchall()
    conn.close()
    return {r["batch"]: {"score": r["score"], "rank": r["rank"]} for r in rows}


def get_available_years():
    """获取数据库中可用的年份列表"""
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT year FROM province_lines ORDER BY year DESC").fetchall()
    conn.close()
    return [r["year"] for r in rows]


def get_major_categories():
    """获取所有专业门类"""
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT category FROM majors ORDER BY category").fetchall()
    conn.close()
    return [r["category"] for r in rows]


def get_uni_advantage_majors(uni_id):
    """获取某院校的优势专业列表(含难度偏移)"""
    conn = get_db()
    rows = conn.execute(
        """SELECT m.name, m.category, m.employment_score, m.avg_salary, m.difficulty_offset
           FROM uni_majors um
           JOIN majors m ON um.major_id = m.id
           WHERE um.university_id=? AND um.is_advantage=1
           ORDER BY m.employment_score DESC""",
        (uni_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_university_admissions(university_id, province, category, years=3):
    """获取某院校在某省近N年的录取数据"""
    conn = get_db()
    available_years = get_available_years()
    target_years = available_years[:years]

    rows = conn.execute(
        f"""SELECT year, batch, min_score, avg_score, min_rank
            FROM admission_scores
            WHERE university_id=? AND province=? AND category=?
            AND year IN ({','.join('?'*len(target_years))})
            ORDER BY year DESC""",
        (university_id, province, category, *target_years)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def calculate_rank_score(my_rank, uni_avg_rank):
    """位次法评分: 0-100, 越高越稳。平滑版本避免极端聚集"""
    if not uni_avg_rank:
        return 50
    if my_rank <= uni_avg_rank:
        # 考生位次更靠前: 用比值梯度给分，系数50避免过早封顶100
        ratio = my_rank / uni_avg_rank
        return min(100, 50 + (1 - ratio) * 50)
    else:
        # 考生位次更靠后: 用倒数比值
        ratio = uni_avg_rank / my_rank
        return max(0, 50 * ratio)


def calculate_diff_score(my_score, batch_line, uni_avg_score):
    """线差法评分: 0-100, 越高越稳。平滑版本"""
    if not batch_line or not uni_avg_score:
        return 50
    my_diff = my_score - batch_line
    uni_diff = uni_avg_score - batch_line
    diff_gap = my_diff - uni_diff
    if diff_gap >= 0:
        return min(100, 50 + diff_gap * 3)  # 每超1分+3，系数从5降到3
    else:
        return max(0, 50 + diff_gap * 3)    # 每低1分-3


def recommend(my_score, my_rank, province, category, major_category=None, top_n=20):
    """
    核心推荐函数
    参数:
        my_score: 我的分数
        my_rank: 我的位次
        province: 省份
        category: 科类
        major_category: 偏好的专业门类(可选)，如"工学"/"医学"/"经济学"
        top_n: 返回前N个推荐
    返回: 冲/稳/保 三类推荐列表，每校附优势专业
    """
    conn = get_db()
    available_years = get_available_years()
    if not available_years:
        conn.close()
        return {"error": "数据库无数据，请先导入数据"}

    latest_year = available_years[0]

    lines = get_province_lines(province, latest_year, category)
    if not lines:
        conn.close()
        return {"error": f"无{province} {latest_year}年{category}批次线数据"}

    sorted_batches = sorted(lines.items(), key=lambda x: x[1]["score"], reverse=True)
    my_batch = None
    for batch_name, batch_info in sorted_batches:
        if my_score >= batch_info["score"]:
            my_batch = batch_name
            break

    if not my_batch:
        conn.close()
        return {"error": "分数未达到任何批次线"}

    batch_line_score = lines[my_batch]["score"]

    # 获取所有在该省该批次招生的院校
    rows = conn.execute(
        """SELECT DISTINCT u.id, u.name, u.level, u.type, u.city, u.is_public,
                  a.batch
           FROM admission_scores a
           JOIN universities u ON a.university_id = u.id
           WHERE a.province=? AND a.category=? AND a.batch=?
           ORDER BY u.level, a.min_score DESC""",
        (province, category, my_batch)
    ).fetchall()

    results = []
    for r in rows:
        uid = r["id"]

        # 如果有专业偏好，检查该院校是否有该门类的优势专业
        advantage_majors = get_uni_advantage_majors(uid)
        if major_category and advantage_majors:
            # 有专业数据时才过滤：必须至少有一个匹配门类的优势专业
            matched = [m for m in advantage_majors if m["category"] == major_category]
            if not matched:
                continue  # 该院校在此门类无优势专业，跳过
        # 如果院校无专业数据(advantage_majors为空)，不过滤，全部显示

        hist = get_university_admissions(uid, province, category, years=3)
        if not hist:
            continue

        avg_scores = [h["min_score"] for h in hist if h["min_score"]]
        avg_ranks = [h["min_rank"] for h in hist if h["min_rank"]]

        if not avg_scores:
            continue

        uni_avg_score = sum(avg_scores) / len(avg_scores)
        uni_avg_rank = sum(avg_ranks) / len(avg_ranks) if avg_ranks else None

        rank_score = calculate_rank_score(my_rank, uni_avg_rank) if my_rank else 50
        diff_score = calculate_diff_score(my_score, batch_line_score, uni_avg_score)
        composite = round(rank_score * 0.6 + diff_score * 0.4, 1)

        # 专业匹配加分
        if major_category and any(m["category"] == major_category for m in advantage_majors):
            composite = min(100, composite + 5)

        # 非一本批次挑战因子
        if my_batch == "本科二批":
            composite = round(composite - 12, 1)
        elif "专科" in my_batch or my_batch == "二段线":
            composite = round(composite - 10, 1)

        # 高分上限 + 低下限
        composite = max(5, min(92, composite))

        # 批次自适应阈值: 留5分过渡带, 边界学校由强制多样化处理
        if my_batch in ("本科一批", "本科批", "一段线"):
            bao_threshold = 70
            wen_threshold = 35   # 原40, 与冲拉开5分gap
        elif my_batch == "本科二批":
            bao_threshold = 60
            wen_threshold = 25   # 原30
        else:  # 专科/二段线
            bao_threshold = 55
            wen_threshold = 20   # 原25

        if composite >= bao_threshold:
            category_label = "保"
        elif composite >= wen_threshold:
            category_label = "稳"
        else:
            category_label = "冲"

        results.append({
            "university_id": uid,
            "name": r["name"],
            "level": r["level"],
            "type": r["type"],
            "city": r["city"],
            "is_public": bool(r["is_public"]),
            "batch": r["batch"],
            "uni_avg_score": round(uni_avg_score),
            "uni_avg_rank": round(uni_avg_rank) if uni_avg_rank else None,
            "my_diff": my_score - batch_line_score,
            "uni_diff": round(uni_avg_score - batch_line_score),
            "rank_score": round(rank_score, 1),
            "diff_score": round(diff_score, 1),
            "composite": composite,
            "category": category_label,
            "advantage_majors": [m["name"] for m in advantage_majors],
            # 具体专业推荐: 冲/稳/保 三个档位
            "majors_bao": [
                f"{m['name']}(估{m['difficulty_offset']:+d})"
                for m in advantage_majors
                if my_score - (round(uni_avg_score) + m["difficulty_offset"]) >= 5
            ],
            "majors_wen": [
                f"{m['name']}(估{m['difficulty_offset']:+d})"
                for m in advantage_majors
                if -5 <= my_score - (round(uni_avg_score) + m["difficulty_offset"]) < 5
            ],
            "majors_chong": [
                f"{m['name']}(估{m['difficulty_offset']:+d})"
                for m in advantage_majors
                if my_score - (round(uni_avg_score) + m["difficulty_offset"]) < -5
            ],
        })

    conn.close()
    # 排序: 综合评分降序 (高=安全)
    results.sort(key=lambda x: x["composite"], reverse=True)

    chong = [r for r in results if r["category"] == "冲"]
    wen = [r for r in results if r["category"] == "稳"]
    bao = [r for r in results if r["category"] == "保"]

    # 强制多样化: 如果某档为空且总数≥10
    # 核心原则: 低composite=难进→冲, 中composite→稳, 高composite=安全→保
    total_results = len(results)
    if total_results >= 10:
        if not chong:
            # 冲 = 最难进的 = composite最低的 → 从列表尾部取
            n_chong = min(8, total_results // 5)
            for i in range(n_chong):
                results[-(i+1)]["category"] = "冲"
        if not wen:
            # 稳 = 中段 → 取composite最接近均值的
            n_wen = min(8, total_results // 4)
            avg_comp = sum(r["composite"] for r in results) / total_results
            candidates = [r for r in results if r["category"] not in ("稳",)]
            candidates.sort(key=lambda x: abs(x["composite"] - avg_comp))
            for i in range(min(n_wen, len(candidates))):
                candidates[i]["category"] = "稳"
        if not bao:
            # 保 = 最安全的 = composite最高的 → 从列表头部取
            n_bao = min(8, total_results // 5)
            for i in range(n_bao):
                results[i]["category"] = "保"

    # 重新分组后，各组内按composite降序排列
    chong = sorted([r for r in results if r["category"] == "冲"], key=lambda x: x["composite"], reverse=True)
    wen = sorted([r for r in results if r["category"] == "稳"], key=lambda x: x["composite"], reverse=True)
    bao = sorted([r for r in results if r["category"] == "保"], key=lambda x: x["composite"], reverse=True)

    return {
        "my_info": {
            "score": my_score,
            "rank": my_rank,
            "province": province,
            "category": category,
            "batch": my_batch,
            "batch_line": batch_line_score,
            "year": latest_year,
        },
        "summary": {
            "total": len(results),
            "冲": len(chong),
            "稳": len(wen),
            "保": len(bao),
        },
        "冲": chong[:50],
        "稳": wen[:50],
        "保": bao[:50],
    }
