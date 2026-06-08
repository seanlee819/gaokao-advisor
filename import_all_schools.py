"""
全量高校数据导入 — 基于生成的 3075 所院校列表
导入 universities 表 + 生成 admission_scores
"""

import sys, os, json, random
sys.path.insert(0, os.path.dirname(__file__))
from database import init_db, get_db

SCHOOLS_FILE = os.path.join(os.path.dirname(__file__), "data", "all_schools.json")

# Tier-based score offsets relative to first-tier line
TIER_OFFSET_MAP = {
    # (理科/物理类偏移, 文科/历史类偏移)
    "C9":       (170, 150),
    "top985":   (148, 135),
    "mid985":   (122, 108),
    "other985": (95, 88),
    "top211":   (105, 92),
    "mid211":   (80, 70),
    "other211": (55, 48),
    "prov_key": (40, 35),
    "pub_ug":   (22, 18),
    "priv_ug":  (8, 5),
    "pub_voc":  (-50, -55),
    "priv_voc": (-90, -100),
}

# Province batch lines for 2025 (for reference)
PROVINCE_BATCHES = {
    "河南": {"理科": [("本科一批", 511), ("本科二批", 409), ("专科批", 185)],
             "文科": [("本科一批", 521), ("本科二批", 428), ("专科批", 185)]},
    "广东": {"物理类": [("本科批", 445), ("专科批", 200)],
             "历史类": [("本科批", 437), ("专科批", 200)]},
    "四川": {"理科": [("本科一批", 520), ("本科二批", 459), ("专科批", 150)],
             "文科": [("本科一批", 529), ("本科二批", 466), ("专科批", 150)]},
    "山东": {"综合": [("一段线", 444), ("二段线", 150)]},
    "江苏": {"物理类": [("本科批", 458), ("专科批", 220)],
             "历史类": [("本科批", 474), ("专科批", 220)]},
    "湖北": {"物理类": [("本科批", 437), ("专科批", 200)],
             "历史类": [("本科批", 432), ("专科批", 200)]},
    "湖南": {"物理类": [("本科批", 435), ("专科批", 200)],
             "历史类": [("本科批", 442), ("专科批", 200)]},
    "北京": {"综合": [("本科批", 423), ("专科批", 120)]},
}

CATEGORY_MAP = {
    "理科": "理科", "文科": "文科",
    "物理类": "物理类", "历史类": "历史类",
    "综合": "综合",
}

# Province neighboring groups for recruitment scope
PROVINCE_GROUPS = {
    "北京": ["北京","天津","河北","山东","河南"],
    "天津": ["天津","北京","河北","山东"],
    "河北": ["河北","北京","天津","山西","河南","山东"],
    "山西": ["山西","河北","河南","陕西","内蒙古"],
    "内蒙古": ["内蒙古","山西","河北","辽宁","吉林","宁夏"],
    "辽宁": ["辽宁","吉林","黑龙江","内蒙古","河北","山东"],
    "吉林": ["吉林","辽宁","黑龙江","内蒙古"],
    "黑龙江": ["黑龙江","吉林","辽宁","内蒙古"],
    "上海": ["上海","江苏","浙江","安徽"],
    "江苏": ["江苏","上海","浙江","安徽","山东","河南"],
    "浙江": ["浙江","上海","江苏","安徽","福建","江西"],
    "安徽": ["安徽","江苏","浙江","河南","湖北","江西"],
    "福建": ["福建","浙江","江西","广东"],
    "江西": ["江西","湖北","湖南","广东","福建","安徽","浙江"],
    "山东": ["山东","北京","天津","河北","河南","江苏","辽宁"],
    "河南": ["河南","北京","天津","河北","山西","山东","江苏","安徽","湖北","陕西"],
    "湖北": ["湖北","湖南","河南","江西","安徽","重庆","四川"],
    "湖南": ["湖南","湖北","广东","广西","江西","贵州","重庆"],
    "广东": ["广东","广西","湖南","江西","福建","海南"],
    "广西": ["广西","广东","湖南","贵州","云南","海南"],
    "海南": ["海南","广东","广西"],
    "重庆": ["重庆","四川","贵州","湖北","湖南"],
    "四川": ["四川","重庆","贵州","云南","陕西","甘肃","湖北"],
    "贵州": ["贵州","四川","重庆","云南","湖南","广西"],
    "云南": ["云南","四川","贵州","广西"],
    "西藏": ["西藏","四川","青海","新疆"],
    "陕西": ["陕西","甘肃","宁夏","山西","河南","四川","重庆","内蒙古"],
    "甘肃": ["甘肃","陕西","宁夏","青海","新疆","四川"],
    "青海": ["青海","甘肃","新疆","西藏","四川"],
    "宁夏": ["宁夏","陕西","甘肃","内蒙古"],
    "新疆": ["新疆","甘肃","青海","陕西","西藏"],
}


def school_recruits_in(school_city, school_tier, target_province):
    """Determine if a school recruits in a given province"""
    # Find which province the school is in
    school_prov = None
    for prov, cities in PROVINCE_GROUPS.items():
        for city_part in cities:
            if city_part in school_city or school_city in city_part:
                # Check if school city matches - rough matching
                pass
    
    # Find the school's home province by matching its city
    for prov in PROVINCE_GROUPS:
        if prov in school_city or school_city in prov:
            school_prov = prov
            break
    
    if not school_prov:
        return False
    
    if school_prov == target_province:
        return True  # Always recruit in home province
    
    # Elite schools recruit nationally
    if school_tier in ("C9", "top985", "mid985", "other985"):
        return True
    if school_tier in ("top211", "mid211"):
        return True  # 211 also recruit widely
    
    # Provincial key: home + neighboring provinces
    if school_tier == "prov_key":
        neighbors = PROVINCE_GROUPS.get(school_prov, [])
        return target_province in neighbors[:6]  # limited to 6 including home
    
    # Public UG: home province + maybe 1-2 neighbors
    if school_tier == "pub_ug":
        neighbors = PROVINCE_GROUPS.get(school_prov, [])
        return target_province in neighbors[:3]
    
    # Private UG / vocational: home province only
    if school_tier in ("priv_ug", "pub_voc", "priv_voc"):
        return target_province == school_prov
    
    return False


def get_city_province(city):
    """Map city to province"""
    city = city.replace("市","").replace("地区","").replace("州","").replace("盟","")
    for prov, cities in PROVINCE_GROUPS.items():
        prov_short = prov.replace("省","").replace("市","").replace("自治区","").replace("壮族","").replace("回族","").replace("维吾尔","")
        for c in cities:
            c_short = c.replace("市","")
            if city == c_short or c_short.startswith(city[:2]) or city.startswith(c_short[:2]):
                return prov
    return None


def import_all():
    print("Loading school list...")
    with open(SCHOOLS_FILE, "r", encoding="utf-8") as f:
        schools = json.load(f)
    print(f"  {len(schools)} schools loaded")

    # Re-init DB
    init_db()
    conn = get_db()
    cur = conn.cursor()

    # Insert universities
    print("\nInserting universities...")
    uni_id_map = {}
    for name, code, city, level, utype, tier in schools:
        cur.execute(
            """INSERT INTO universities (name, code, city, level, type, is_public)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name, code, city, level, utype, 0 if "民办" in level else 1)
        )
        uni_id_map[name] = cur.lastrowid
    conn.commit()
    print(f"  Inserted {len(uni_id_map)} universities")

    # Generate admission scores
    print("\nGenerating admission scores...")
    years = [2023, 2024, 2025]
    rng = random.Random(42)
    batch_inserts = 0

    for name, code, city, level, utype, tier in schools:
        uid = uni_id_map[name]
        school_prov = get_city_province(city)
        if not school_prov:
            continue

        offset = TIER_OFFSET_MAP.get(tier, (0, 0))
        sci_off, arts_off = offset

        for target_prov in PROVINCE_GROUPS:
            if not school_recruits_in(city, tier, target_prov):
                continue

            if target_prov not in PROVINCE_BATCHES:
                continue

            for cat_key in PROVINCE_BATCHES[target_prov]:
                batches = PROVINCE_BATCHES[target_prov][cat_key]
                
                # Determine if school is UG or vocational
                is_voc = "专科" in level
                
                for year in years:
                    year_jitter = rng.randint(-5, 8)
                    
                    for batch_name, batch_score in batches:
                        # UG schools only generate for UG batches
                        batch_is_ug = "专科" not in batch_name and "二段" not in batch_name
                        batch_is_voc = "专科" in batch_name or "二段" in batch_name
                        
                        if is_voc and batch_is_ug:
                            continue  # Vocational schools don't have UG batch data
                        if not is_voc and batch_is_voc:
                            continue  # UG schools don't need vocational batch data
                        
                        # For vocational batches, offset is relative to the batch score
                        if is_voc:
                            off = sci_off if cat_key in ("理科","物理类","综合") else arts_off
                        else:
                            # Only generate for the highest UG batch
                            if batch_name not in ("本科一批","本科批","一段线") and batch_is_ug:
                                continue
                            off = sci_off if cat_key in ("理科","物理类","综合") else arts_off
                        
                        min_score = batch_score + off + year_jitter
                        if min_score < 100:
                            min_score = 100 + rng.randint(0, 50)
                        if min_score > 750:
                            min_score = 740
                        
                        avg_score = min_score + rng.randint(2, 10)
                        max_score = min_score + rng.randint(8, 25)
                        
                        # Rank estimation
                        rank_coef = 300
                        if target_prov in ("河南","广东","山东","四川"):
                            rank_coef = 380
                        elif target_prov in ("北京","上海"):
                            rank_coef = 50
                        elif target_prov in ("江苏","湖北","湖南"):
                            rank_coef = 200
                        
                        min_rank = max(1, int((750 - min_score) * rank_coef))
                        
                        cur.execute(
                            """INSERT OR REPLACE INTO admission_scores
                               (university_id, province, year, category, batch,
                                min_score, avg_score, max_score, min_rank)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (uid, target_prov, year, cat_key, batch_name,
                             min_score, avg_score, max_score, min_rank)
                        )
                        batch_inserts += 1

    conn.commit()
    print(f"  Inserted {batch_inserts} admission score records")
    
    # Also re-seed majors (keep existing data)
    # ... (handled by seed_data.py)
    
    conn.close()
    print("\n Done! Full university database ready.")


if __name__ == "__main__":
    import_all()
