"""
全量种子 — 31省 + 3075校 + 专业全覆盖
"""
import sys, os, json, random
sys.path.insert(0, os.path.dirname(__file__))
from database import init_db, get_db
from real_ranks import estimate_rank_for_seed

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# ============================================================
# Tier offset map — 基于2024河南理科真实录取数据反推
# 格式: (理科偏移范围min, 理科偏移范围max, 文科偏移范围min, 文科偏移范围max)
# 偏移值 = 录取分 - 一本线(511)
# 原固定偏移 → 现改为范围, seed时随机取, 自动产生院校间分数梯度
TIER_OFFSET_MAP = {
    # tier:       (理科min, 理科max, 文科min, 文科max)
    "C9":         (162, 187, 152, 168),     # 真实: 673-698 → 偏移162-187
    "top985":     (124, 157, 118, 140),     # 真实: 635-668
    "mid985":     (94, 115, 88, 105),       # 真实: 605-626 (原122偏高10-20分)
    "other985":   (67, 87, 62, 78),         # 真实: 578-598
    "top211":     (79, 122, 72, 100),       # 真实: 590-633
    "mid211":     (49, 90, 45, 78),         # 真实: 560-601
    "other211":   (19, 54, 18, 48),         # 真实: 530-565
    "prov_key":   (29, 81, 25, 68),         # 真实: 540-592 (原40太集中)
    "pub_ug":     (15, 38, 12, 32),         # 公办普本: 526-549(一本)/ 二本另行处理
    "priv_ug":    (2, 15, 0, 12),           # 民办: 本科线附近
    "pub_voc":    (-80, -20, -85, -25),     # 公办专科
    "priv_voc":   (-120, -80, -130, -85),   # 民办专科
}

# ============================================================
# 省份配置: 科类 + 批次定义
# ============================================================
PROVINCE_CONFIGS = {
    # ===== 传统高考 (理科/文科) — 基准: 2024年官方数据 =====
    "河南":{"cats":["理科","文科"],"batches":{"理科":[("本科一批",511),("本科二批",396),("专科批",185)],"文科":[("本科一批",521),("本科二批",428),("专科批",185)]}},
    "四川":{"cats":["理科","文科"],"batches":{"理科":[("本科一批",539),("本科二批",459),("专科批",150)],"文科":[("本科一批",529),("本科二批",457),("专科批",150)]}},
    "山西":{"cats":["理科","文科"],"batches":{"理科":[("本科一批",506),("本科二批",418),("专科批",180)],"文科":[("本科一批",516),("本科二批",446),("专科批",180)]}},
    "内蒙古":{"cats":["理科","文科"],"batches":{"理科":[("本科一批",471),("本科二批",360),("专科批",180)],"文科":[("本科一批",478),("本科二批",381),("专科批",180)]}},
    "吉林":{"cats":["理科","文科"],"batches":{"理科":[("本科一批",485),("本科二批",371),("专科批",180)],"文科":[("本科一批",485),("本科二批",371),("专科批",180)]}},
    "黑龙江":{"cats":["理科","文科"],"batches":{"理科":[("本科一批",468),("本科二批",360),("专科批",160)],"文科":[("本科一批",485),("本科二批",395),("专科批",160)]}},
    "安徽":{"cats":["理科","文科"],"batches":{"理科":[("本科一批",514),("本科二批",462),("专科批",200)],"文科":[("本科一批",524),("本科二批",478),("专科批",200)]}},
    "江西":{"cats":["理科","文科"],"batches":{"理科":[("本科一批",520),("本科二批",448),("专科批",180)],"文科":[("本科一批",525),("本科二批",465),("专科批",180)]}},
    "广西":{"cats":["理科","文科"],"batches":{"理科":[("本科一批",501),("本科二批",371),("专科批",180)],"文科":[("本科一批",520),("本科二批",400),("专科批",180)]}},
    "贵州":{"cats":["理科","文科"],"batches":{"理科":[("本科一批",482),("本科二批",380),("专科批",180)],"文科":[("本科一批",532),("本科二批",442),("专科批",180)]}},
    "云南":{"cats":["理科","文科"],"batches":{"理科":[("本科一批",505),("本科二批",420),("专科批",200)],"文科":[("本科一批",550),("本科二批",480),("专科批",200)]}},
    "西藏":{"cats":["理科","文科"],"batches":{"理科":[("本科一批",400),("本科二批",305),("专科批",190)],"文科":[("本科一批",410),("本科二批",315),("专科批",190)]}},
    "陕西":{"cats":["理科","文科"],"batches":{"理科":[("本科一批",475),("本科二批",372),("专科批",150)],"文科":[("本科一批",488),("本科二批",397),("专科批",150)]}},
    "甘肃":{"cats":["理科","文科"],"batches":{"理科":[("本科一批",470),("本科二批",370),("专科批",160)],"文科":[("本科一批",502),("本科二批",421),("专科批",160)]}},
    "青海":{"cats":["理科","文科"],"batches":{"理科":[("本科一批",398),("本科二批",325),("专科批",180)],"文科":[("本科一批",440),("本科二批",370),("专科批",180)]}},
    "宁夏":{"cats":["理科","文科"],"batches":{"理科":[("本科一批",432),("本科二批",371),("专科批",200)],"文科":[("本科一批",496),("本科二批",419),("专科批",200)]}},
    "新疆":{"cats":["理科","文科"],"batches":{"理科":[("本科一批",432),("本科二批",337),("专科批",170)],"文科":[("本科一批",458),("本科二批",367),("专科批",170)]}},
    # ===== 新高考 物理/历史 — 基准: 2024年官方 =====
    "河北":{"cats":["物理类","历史类"],"batches":{"物理类":[("本科批",448),("专科批",200)],"历史类":[("本科批",449),("专科批",200)]}},
    "辽宁":{"cats":["物理类","历史类"],"batches":{"物理类":[("本科批",368),("专科批",150)],"历史类":[("本科批",400),("专科批",150)]}},
    "江苏":{"cats":["物理类","历史类"],"batches":{"物理类":[("本科批",462),("专科批",220)],"历史类":[("本科批",478),("专科批",220)]}},
    "福建":{"cats":["物理类","历史类"],"batches":{"物理类":[("本科批",449),("专科批",220)],"历史类":[("本科批",431),("专科批",220)]}},
    "湖北":{"cats":["物理类","历史类"],"batches":{"物理类":[("本科批",437),("专科批",200)],"历史类":[("本科批",432),("专科批",200)]}},
    "湖南":{"cats":["物理类","历史类"],"batches":{"物理类":[("本科批",422),("专科批",200)],"历史类":[("本科批",438),("专科批",200)]}},
    "广东":{"cats":["物理类","历史类"],"batches":{"物理类":[("本科批",442),("专科批",200)],"历史类":[("本科批",428),("专科批",200)]}},
    "重庆":{"cats":["物理类","历史类"],"batches":{"物理类":[("本科批",427),("专科批",180)],"历史类":[("本科批",428),("专科批",180)]}},
    # ===== 新高考 综合(3+3) — 基准: 2024年官方 =====
    "北京":{"cats":["综合"],"batches":{"综合":[("本科批",434),("专科批",120)]}},
    "天津":{"cats":["综合"],"batches":{"综合":[("本科批",475),("专科批",180)]}},
    "上海":{"cats":["综合"],"batches":{"综合":[("本科批",403),("专科批",120)]}},
    "浙江":{"cats":["综合"],"batches":{"综合":[("本科批",492),("专科批",269)]}},
    "山东":{"cats":["综合"],"batches":{"综合":[("一段线",444),("二段线",150)]}},
    "海南":{"cats":["综合"],"batches":{"综合":[("本科批",483),("专科批",255)]}},
}

# ============================================================
# 招生范围
# ============================================================
PROVINCE_GROUPS = {
    "北京":["北京","天津","河北","山西","内蒙古","辽宁","吉林","黑龙江","上海","江苏","浙江","安徽","福建","江西","山东","河南","湖北","湖南","广东","广西","海南","重庆","四川","贵州","云南","西藏","陕西","甘肃","青海","宁夏","新疆"],
    "天津":["天津","北京","河北","山西","内蒙古","辽宁","山东","河南"],
    "河北":["河北","北京","天津","山西","内蒙古","辽宁","山东","河南","陕西"],
    "山西":["山西","河北","内蒙古","河南","陕西","北京","天津","山东"],
    "内蒙古":["内蒙古","北京","天津","河北","山西","辽宁","吉林","黑龙江","宁夏","陕西","甘肃"],
    "辽宁":["辽宁","吉林","黑龙江","内蒙古","河北","北京","天津","山东"],
    "吉林":["吉林","辽宁","黑龙江","内蒙古","北京","天津","山东"],
    "黑龙江":["黑龙江","吉林","辽宁","内蒙古","北京","天津","山东"],
    "上海":["上海","江苏","浙江","安徽","北京","天津","福建","江西","山东","河南","湖北","湖南","广东","重庆","四川"],
    "江苏":["江苏","上海","浙江","安徽","山东","河南","北京","天津","福建","江西","湖北","湖南","广东","重庆"],
    "浙江":["浙江","上海","江苏","安徽","福建","江西","北京","天津","山东","河南","湖北","湖南","广东"],
    "安徽":["安徽","江苏","浙江","上海","河南","湖北","江西","山东","北京","天津","福建","湖南","广东","重庆"],
    "福建":["福建","浙江","江西","广东","上海","江苏","安徽","湖南","湖北"],
    "江西":["江西","广东","福建","浙江","安徽","湖北","湖南","上海","江苏","河南"],
    "山东":["山东","北京","天津","河北","山西","辽宁","吉林","黑龙江","上海","江苏","浙江","安徽","河南","湖北","湖南","重庆","四川","陕西"],
    "河南":["河南","北京","天津","河北","山西","辽宁","吉林","黑龙江","上海","江苏","浙江","安徽","福建","江西","山东","湖北","湖南","广东","重庆","四川","陕西","甘肃"],
    "湖北":["湖北","湖南","河南","江西","安徽","重庆","四川","北京","天津","上海","江苏","浙江","福建","广东","山东","陕西"],
    "湖南":["湖南","湖北","广东","广西","江西","贵州","重庆","四川","河南","安徽","福建","江苏","浙江","上海","云南","海南"],
    "广东":["广东","广西","湖南","江西","福建","海南","湖北","河南","四川","重庆","贵州","云南","浙江","江苏","上海","安徽","北京","天津"],
    "广西":["广西","广东","湖南","贵州","云南","海南","湖北","江西","福建","重庆","四川"],
    "海南":["海南","广东","广西","福建","江西","湖南","湖北","四川","重庆","云南"],
    "重庆":["重庆","四川","贵州","湖北","湖南","云南","陕西","北京","天津","上海","江苏","浙江","安徽","福建","江西","山东","河南","广东","广西"],
    "四川":["四川","重庆","贵州","云南","陕西","甘肃","湖北","湖南","西藏","青海","新疆","宁夏","北京","天津","上海","江苏","浙江","广东"],
    "贵州":["贵州","四川","重庆","云南","湖南","广西","湖北","广东","陕西"],
    "云南":["云南","四川","贵州","广西","重庆","湖北","湖南","广东","陕西","西藏"],
    "西藏":["西藏","四川","青海","甘肃","陕西","重庆","云南","新疆","宁夏"],
    "陕西":["陕西","甘肃","宁夏","青海","新疆","山西","河南","四川","重庆","湖北","内蒙古","北京","天津","河北","山东","江苏"],
    "甘肃":["甘肃","陕西","宁夏","青海","新疆","四川","内蒙古","山西","河南","重庆","西藏"],
    "青海":["青海","甘肃","陕西","新疆","西藏","四川","宁夏","内蒙古"],
    "宁夏":["宁夏","陕西","甘肃","内蒙古","山西","河南","青海","新疆","四川"],
    "新疆":["新疆","甘肃","陕西","青海","宁夏","四川","西藏","内蒙古","河南"],
}

CITY_PROVINCE_FILE = os.path.join(DATA_DIR, "city_province.json")
with open(CITY_PROVINCE_FILE, "r", encoding="utf-8") as f:
    CITY_TO_PROVINCE = json.load(f)


def get_city_province(city):
    return CITY_TO_PROVINCE.get(city)


def school_recruits_in(school_prov, school_tier, target_province):
    if not school_prov:
        return False
    if school_prov == target_province:
        return True
    if school_tier in ("C9","top985","mid985","other985"):
        return True  # 985 全国招生
    if school_tier in ("top211","mid211","other211"):
        return True  # 211 全国招生
    if school_tier == "prov_key":
        neighbors = PROVINCE_GROUPS.get(school_prov, [])
        return target_province in neighbors[:12]  # 省重点: 周边12省 (原8)
    if school_tier == "pub_ug":
        neighbors = PROVINCE_GROUPS.get(school_prov, [])
        return target_province in neighbors[:6]   # 公办本科: 周边6省 (原4)
    # 民办/专科: 仅本省
    return False


# ============================================================
# 专业数据
# ============================================================
MAJORS = [
    ("计算机科学与技术", "工学", 9.2, 18000, 10, "软件开发、算法、AI方向"),
    ("软件工程", "工学", 9.0, 17500, 8, "软件开发生命周期管理"),
    ("人工智能", "工学", 9.5, 22000, 12, "机器学习、深度学习、NLP/CV"),
    ("数据科学与大数据技术", "工学", 9.3, 20000, 10, "大数据分析、数据工程"),
    ("电子信息工程", "工学", 8.5, 15000, 6, "通信、嵌入式、信号处理"),
    ("通信工程", "工学", 8.3, 14500, 5, "5G/6G、光通信、卫星通信"),
    ("电气工程及其自动化", "工学", 8.0, 13000, 5, "国家电网/南方电网校招主力"),
    ("自动化", "工学", 8.2, 14000, 4, "工业控制、机器人、智能制造"),
    ("机械工程", "工学", 7.5, 12000, 0, "传统工科基石"),
    ("土木工程", "工学", 6.5, 10000, -3, "建筑/桥梁/隧道"),
    ("建筑学", "工学", 7.8, 14000, 3, "建筑设计、城市规划"),
    ("材料科学与工程", "工学", 7.0, 11000, -2, "半导体/新能源材料"),
    ("车辆工程", "工学", 7.8, 13000, 2, "新能源汽车、智能驾驶"),
    ("航空航天工程", "工学", 8.0, 15000, 3, "航天科技/科工集团"),
    ("生物医学工程", "工学", 7.5, 13000, 1, "医疗器械、医学影像"),
    ("数学与应用数学", "理学", 8.0, 14000, 2, "金融量化/算法/教育"),
    ("物理学", "理学", 7.0, 12000, -2, "半导体/光学/科研"),
    ("化学", "理学", 6.8, 10000, -3, "化工/制药/材料"),
    ("统计学", "理学", 8.5, 16000, 6, "数据分析/风控/精算"),
    ("临床医学", "医学", 9.0, 18000, 8, "医生核心专业"),
    ("口腔医学", "医学", 9.5, 25000, 12, "牙医，收入上限高"),
    ("药学", "医学", 7.5, 12000, 1, "药物研发/生产/注册"),
    ("金融学", "经济学", 8.0, 16000, 6, "银行/证券/基金/投行"),
    ("经济学", "经济学", 7.5, 14000, 4, "宏观/微观/计量"),
    ("国际经济与贸易", "经济学", 7.0, 12000, -1, "外贸/跨境电商"),
    ("会计学", "管理学", 8.0, 13000, 4, "四大/企业财务/审计"),
    ("工商管理", "管理学", 7.0, 12000, 0, "综合管理/MBA"),
    ("信息管理与信息系统", "管理学", 8.0, 14000, 2, "IT+管理复合"),
    ("法学", "法学", 7.5, 13000, 4, "律师/法务/公务员"),
    ("英语", "文学", 6.8, 10000, -2, "翻译/外贸/教育"),
    ("新闻传播学", "文学", 7.0, 11000, -1, "媒体/公关/运营"),
    ("汉语言文学", "文学", 6.5, 9000, -2, "教师/公务员/文案"),
    ("动物医学", "农学", 7.0, 11000, -2, "宠物医疗"),
    ("食品科学与工程", "农学", 7.0, 11000, -3, "食品研发/质检"),
    ("教育学", "教育学", 7.0, 10000, -2, "教师/教研/教育科技"),
]

# ============================================================
# 主流程
# ============================================================
def seed_all():
    init_db()
    conn = get_db()
    cur = conn.cursor()
    rng = random.Random(42)

    # 1. Province lines
    print("1/6 Province lines...")
    for year in [2023, 2024, 2025]:
        year_delta = (2024 - year) * 2  # 2023:+2, 2024:0, 2025:-2
        for prov, cfg in PROVINCE_CONFIGS.items():
            for cat in cfg["cats"]:
                for batch_name, batch_score in cfg["batches"][cat]:
                    score = batch_score + year_delta
                    if "专科" in batch_name or "二段" in batch_name:
                        score = batch_score  # 专科线年间基本不变
                    cur.execute(
                        "INSERT OR REPLACE INTO province_lines (province,year,category,batch,score,rank) VALUES (?,?,?,?,?,?)",
                        (prov, year, cat, batch_name, score, None))
    total_lines = sum(len(cfg["cats"]) * len(cfg["batches"][cfg["cats"][0]]) for cfg in PROVINCE_CONFIGS.values()) * 3
    conn.commit()
    print(f"   ~{total_lines} records for 31 provinces")

    # 2. Universities
    print("2/6 Universities...")
    with open(os.path.join(DATA_DIR, "real_universities.json"), "r", encoding="utf-8") as f:
        schools = json.load(f)
    uni_id_map = {}
    for name, code, city, level, utype, tier in schools:
        cur.execute(
            "INSERT INTO universities (name,code,city,level,type,is_public) VALUES (?,?,?,?,?,?)",
            (name, code, city, level, utype, 0 if "民办" in level else 1))
        uni_id_map[name] = cur.lastrowid
    conn.commit()
    print(f"   {len(uni_id_map)} universities")

    # 3. Majors
    print("3/6 Majors...")
    for item in MAJORS:
        cur.execute(
            "INSERT OR REPLACE INTO majors (name,category,employment_score,avg_salary,difficulty_offset,description) VALUES (?,?,?,?,?,?)",
            item)
    conn.commit()
    print(f"   {len(MAJORS)} majors")

    # 4. Major links
    print("4/6 Major links...")
    with open(os.path.join(DATA_DIR, "all_major_links.json"), "r", encoding="utf-8") as f:
        major_links = json.load(f)
    # Get major name->id map
    major_id_map = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM majors").fetchall()}
    link_count = 0
    for uni_name, major_names in major_links.items():
        uid = uni_id_map.get(uni_name)
        if not uid:
            continue
        for mn in major_names:
            mid = major_id_map.get(mn)
            if mid:
                cur.execute(
                    "INSERT OR REPLACE INTO uni_majors (university_id,major_id,is_advantage) VALUES (?,?,1)",
                    (uid, mid))
                link_count += 1
    conn.commit()
    print(f"   {link_count} links for {len(major_links)} schools")

    # 5. Admission scores
    print("5/6 Admission scores...")
    years = [2023, 2024, 2025]
    batch_inserts = 0

    # Determine UG batch names
    UG_BATCHES = {"本科一批", "本科批", "一段线"}

    for name, code, city, level, utype, tier in schools:
        uid = uni_id_map[name]
        school_prov = get_city_province(city)
        if not school_prov:
            continue

        # 从层次偏移范围中随机取值, 产生院校间分数梯度
        offsets = TIER_OFFSET_MAP.get(tier, (0, 0, 0, 0))
        sci_off = rng.randint(offsets[0], offsets[1])
        arts_off = rng.randint(offsets[2], offsets[3])
        is_voc = "专科" in level

        for target_prov in PROVINCE_CONFIGS:
            if not school_recruits_in(school_prov, tier, target_prov):
                continue

            cfg = PROVINCE_CONFIGS[target_prov]
            for cat_key in cfg["cats"]:
                batches = cfg["batches"][cat_key]
                for year in years:
                    year_jitter = rng.randint(-5, 8)
                    for batch_name, batch_score in batches:
                        batch_is_voc = "专科" in batch_name or "二段" in batch_name
                        if is_voc != batch_is_voc:
                            continue
                        # 985/211 不在二本招生
                        if tier in ("C9","top985","mid985","other985","top211","mid211","other211"):
                            if batch_name == "本科二批":
                                continue
                        
                        off = sci_off if cat_key in ("理科","物理类","综合") else arts_off
                        if batch_name == "本科二批":
                            off = off - 50

                        min_score = max(100, min(750, batch_score + off + year_jitter))
                        avg_score = min(min_score + rng.randint(2, 10), 750)
                        max_score = min(avg_score + rng.randint(8, 25), 750)

                        min_rank = estimate_rank_for_seed(target_prov, cat_key, min_score)

                        cur.execute(
                            """INSERT OR REPLACE INTO admission_scores
                               (university_id,province,year,category,batch,min_score,avg_score,max_score,min_rank)
                               VALUES (?,?,?,?,?,?,?,?,?)""",
                            (uid, target_prov, year, cat_key, batch_name, min_score, avg_score, max_score, min_rank))
                        batch_inserts += 1

    conn.commit()
    print(f"   {batch_inserts} admission records")

    # 6. Stats
    print("6/6 Stats...")
    uni_c = cur.execute("SELECT COUNT(*) FROM universities").fetchone()[0]
    score_c = cur.execute("SELECT COUNT(*) FROM admission_scores").fetchone()[0]
    major_c = cur.execute("SELECT COUNT(*) FROM majors").fetchone()[0]
    link_c = cur.execute("SELECT COUNT(*) FROM uni_majors").fetchone()[0]
    prov_c = cur.execute("SELECT COUNT(DISTINCT province) FROM province_lines").fetchone()[0]
    conn.close()

    print(f"\n=== FINAL ===")
    print(f"  Provinces: {prov_c}")
    print(f"  Universities: {uni_c}")
    print(f"  Majors: {major_c}")
    print(f"  Major links: {link_c}")
    print(f"  Admission records: {score_c}")


if __name__ == "__main__":
    seed_all()
