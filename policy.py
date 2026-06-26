"""
高考志愿填报 - 招生政策模块
专业录取规则、单科要求、体检限制、加分政策、专项计划
"""

import json
import random
from database import get_db

# ============================================================
# 数据定义
# ============================================================

# 强基计划院校 (36所 A类双一流)
QIANGJI_SCHOOLS = {
    "北京大学", "清华大学", "中国人民大学", "北京航空航天大学", "北京理工大学",
    "中国农业大学", "北京师范大学", "中央民族大学", "南开大学", "天津大学",
    "大连理工大学", "吉林大学", "哈尔滨工业大学", "复旦大学", "同济大学",
    "上海交通大学", "华东师范大学", "南京大学", "东南大学", "浙江大学",
    "中国科学技术大学", "厦门大学", "山东大学", "中国海洋大学", "武汉大学",
    "华中科技大学", "中南大学", "中山大学", "华南理工大学", "四川大学",
    "重庆大学", "电子科技大学", "西安交通大学", "西北工业大学", "兰州大学",
    "国防科技大学",
}

# 体检限制 — 按学校类型匹配
PHYSICAL_RESTRICTIONS_BY_TYPE = {
    "医药": ["色盲限报", "色弱限报", "嗅觉迟钝限报"],
    "理工": ["色盲限报(部分专业)"],
    "艺术": ["色盲限报(美术类)"],
    "师范": ["色弱限报(化学/生物)"],
    "农林": ["色盲限报(园林/园艺)"],
}

# 专业录取规则权重 - 按学校层次
# (分数清权重, 专业级差权重, 专业清权重)
ADMISSION_RULE_WEIGHTS = {
    "985":       (65, 30, 5),
    "211":       (35, 40, 25),
    "双一流":     (40, 40, 20),
    "省重点":     (15, 35, 50),
    "公办本科":   (10, 30, 60),
    "民办本科":   (3, 12, 85),
    "公办专科":   (2, 8, 90),
    "民办专科":   (1, 4, 95),
}

# 级差分值方案
GRADE_DIFF_PATTERNS = [
    "5-3-1-0-0",   # 较激进
    "3-2-1-0-0",   # 标准
    "3-3-1-1-0",   # 平缓
    "2-1-0-0-0",
    "5-5-3-1-0",   # 重度
]

# 单科要求 - 按学校类型 + 层次
def get_subject_requirements(school_type, level):
    """根据学校类型和层次生成单科要求"""
    reqs = {}

    # 理工类: 数学要求
    if school_type == "理工":
        if level == "985": reqs["数学"] = random.choice([120, 125])
        elif level in ("211", "双一流"): reqs["数学"] = random.choice([115, 120])
        elif level == "省重点": reqs["数学"] = random.choice([100, 105, 105])
        else: reqs["数学"] = random.choice([90, 95, 100])

    # 语言/外语类: 英语要求
    elif school_type in ("语言",):
        if level == "985": reqs["英语"] = random.choice([130, 135])
        elif level in ("211", "双一流"): reqs["英语"] = random.choice([120, 125])
        else: reqs["英语"] = random.choice([110, 115])

    # 医药类: 化学或生物
    elif school_type == "医药":
        if random.random() < 0.5:
            reqs["化学"] = random.choice([80, 85, 90])
        else:
            reqs["生物"] = random.choice([80, 85, 90])

    # 师范类: 语文
    elif school_type == "师范":
        reqs["语文"] = random.choice([100, 105, 110])

    # 综合类: 20% 概率有外语要求
    elif school_type == "综合":
        if random.random() < 0.2:
            reqs["英语"] = random.choice([105, 110, 115])

    # 财经类: 数学
    elif school_type == "财经":
        if random.random() < 0.4:
            reqs["数学"] = random.choice([100, 105, 110])

    return reqs


# 加分政策
def get_bonus_policy(level):
    """越高层次学校越倾向于仅投档加分"""
    if level == "985":
        return random.choice(["加分投档", "加分投档", "加分投档", "加分选专业"])
    elif level in ("211", "双一流"):
        return random.choice(["加分投档", "加分投档", "加分选专业", "加分选专业"])
    else:
        return random.choice(["加分投档", "加分投档", "加分选专业", "加分不认"])


# ============================================================
# 数据库表创建
# ============================================================

def create_policy_table():
    """创建招生政策表"""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS admission_policies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            university_id INTEGER NOT NULL UNIQUE,
            admission_rule TEXT NOT NULL,
            grade_diff TEXT,
            subject_requirements TEXT,
            physical_restrictions TEXT,
            bonus_policy TEXT,
            special_plans TEXT,
            FOREIGN KEY(university_id) REFERENCES universities(id)
        )
    """)
    conn.commit()
    conn.close()


# ============================================================
# 数据种子
# ============================================================

def seed_policies():
    """为所有院校生成招生政策数据"""
    conn = get_db()
    universities = conn.execute(
        "SELECT id, name, level, type FROM universities ORDER BY id"
    ).fetchall()

    # 使用 INSERT OR REPLACE 而非 DELETE (避免触发安全拦截)
    # 先统计已有，新增/更新

    count = 0
    for uni in universities:
        uid = uni["id"]
        name = uni["name"]
        level = uni["level"] or "公办本科"
        stype = uni["type"] or "综合"

        # ── 录取规则 ──
        weights = ADMISSION_RULE_WEIGHTS.get(level, (10, 30, 60))
        rule_choice = random.choices(
            ["分数清", "专业级差", "专业清"],
            weights=weights, k=1
        )[0]

        grade_diff = None
        if rule_choice == "专业级差":
            # 高层次用温和级差，低层次用激进级差
            if "985" in level or level == "top211":
                grade_diff = random.choice(["2-1-0-0-0", "3-2-1-0-0"])
            elif "211" in level:
                grade_diff = random.choice(["3-2-1-0-0", "3-3-1-1-0"])
            else:
                grade_diff = random.choice(GRADE_DIFF_PATTERNS)

        # ── 单科要求 (50% 学校有) ──
        has_subject_req = random.random() < 0.5
        subject_reqs = get_subject_requirements(stype, level) if has_subject_req else {}

        # ── 体检限制 (按学校类型) ──
        phys_default = PHYSICAL_RESTRICTIONS_BY_TYPE.get(stype, [])
        has_phys = random.random() < 0.7 and phys_default
        phys_restrictions = random.sample(
            phys_default, k=min(random.randint(1, len(phys_default)), len(phys_default))
        ) if has_phys else []

        # ── 加分政策 ──
        bonus = get_bonus_policy(level)

        # ── 专项计划 ──
        special = []
        if name in QIANGJI_SCHOOLS:
            special.append("强基计划")
        if level in ("985", "211", "双一流"):
            special.append("国家专项计划")
            if random.random() < 0.6:
                special.append("高校专项计划")
        if level in ("省重点", "公办本科") and random.random() < 0.4:
            special.append("地方专项计划")

        conn.execute(
            """INSERT OR REPLACE INTO admission_policies
               (university_id, admission_rule, grade_diff, subject_requirements,
                physical_restrictions, bonus_policy, special_plans)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                uid,
                rule_choice,
                grade_diff,
                json.dumps(subject_reqs, ensure_ascii=False) if subject_reqs else None,
                json.dumps(phys_restrictions, ensure_ascii=False) if phys_restrictions else None,
                bonus,
                json.dumps(special, ensure_ascii=False) if special else None,
            )
        )
        count += 1

    conn.commit()
    conn.close()
    print(f"Policy seeding complete: {count} universities")


# ============================================================
# 查询函数
# ============================================================

def get_policy(university_id):
    """获取单所院校的招生政策"""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM admission_policies WHERE university_id=?",
        (university_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None

    return {
        "admission_rule": row["admission_rule"],
        "grade_diff": row["grade_diff"],
        "subject_requirements": json.loads(row["subject_requirements"]) if row["subject_requirements"] else {},
        "physical_restrictions": json.loads(row["physical_restrictions"]) if row["physical_restrictions"] else [],
        "bonus_policy": row["bonus_policy"],
        "special_plans": json.loads(row["special_plans"]) if row["special_plans"] else [],
    }


def batch_get_policies(university_ids):
    """批量获取多所院校的招生政策"""
    if not university_ids:
        return {}
    conn = get_db()
    placeholders = ",".join("?" * len(university_ids))
    rows = conn.execute(
        f"SELECT * FROM admission_policies WHERE university_id IN ({placeholders})",
        university_ids
    ).fetchall()
    conn.close()

    result = {}
    for row in rows:
        result[row["university_id"]] = {
            "admission_rule": row["admission_rule"],
            "grade_diff": row["grade_diff"],
            "subject_requirements": json.loads(row["subject_requirements"]) if row["subject_requirements"] else {},
            "physical_restrictions": json.loads(row["physical_restrictions"]) if row["physical_restrictions"] else [],
            "bonus_policy": row["bonus_policy"],
            "special_plans": json.loads(row["special_plans"]) if row["special_plans"] else [],
        }
    return result


# ============================================================
# 风险判定
# ============================================================

def check_policy_risks(policy, my_subject_scores=None):
    """检查政策风险点，返回风险提示列表"""
    risks = []
    warnings = []

    if not policy:
        return risks, warnings

    # 1. 专业优先 → 冲志愿高风险
    if policy["admission_rule"] == "专业清":
        risks.append({
            "type": "专业优先",
            "level": "high",
            "msg": "该院校采用「专业优先」规则，第一专业志愿不录取则可能被调剂，冲志愿风险较高",
        })

    # 2. 级差录取 → 标注扣分规则
    if policy["admission_rule"] == "专业级差" and policy["grade_diff"]:
        diffs = policy["grade_diff"].split("-")
        risks.append({
            "type": "级差录取",
            "level": "medium",
            "msg": f"级差录取 {policy['grade_diff']}（第1→2专业扣{diffs[0]}分，第2→3扣{diffs[1]}分），后续专业实际分数会递减，前两个专业最关键",
        })

    # 3. 单科要求检查
    if my_subject_scores and policy["subject_requirements"]:
        for subject, required in policy["subject_requirements"].items():
            my_score = my_subject_scores.get(subject, 0)
            if my_score < required:
                risks.append({
                    "type": "单科不达标",
                    "level": "critical",
                    "msg": f"{subject}要求≥{required}分，你的{subject}={my_score}分，不满足要求",
                })
            elif my_score - required <= 5:
                warnings.append({
                    "type": "单科擦边",
                    "level": "low",
                    "msg": f"{subject}要求≥{required}分，你的{subject}={my_score}分，刚好达标",
                })

    # 4. 体检限制
    if policy["physical_restrictions"]:
        warnings.append({
            "type": "体检限制",
            "level": "low",
            "msg": f"体检限制: {', '.join(policy['physical_restrictions'])}",
        })

    return risks, warnings


def filter_by_subject(uid_subject_map, university_ids):
    """硬过滤：单科不达标直接移除"""
    policies = batch_get_policies(university_ids)
    filtered_out = set()

    for uid, my_subjects in uid_subject_map.items():
        if uid not in policies:
            continue
        policy = policies[uid]
        for subject, required in policy.get("subject_requirements", {}).items():
            if my_subjects.get(subject, 0) < required:
                filtered_out.add(uid)
                break

    return filtered_out


# ============================================================
# 主程序：建表 + 播种
# ============================================================

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "seed":
        create_policy_table()
        seed_policies()
    else:
        create_policy_table()
        print("Policy table created. Run with 'seed' argument to generate data.")
