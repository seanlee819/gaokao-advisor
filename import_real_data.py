"""
从GitHub开源数据集导入真实高考数据
1. 一分一段表: sdgedfegw/Gaokao-score-distribution (21MB, 1996-2024)
2. 录取分数线: xlwang1188/2024_Shanghai_Gaokao_Admissions_Data (上海2024)
"""
import sys, os, csv, io, sqlite3, urllib.request, json
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from database import get_db

# ============================================================
# Part 1: Download and parse 一分一段表
# ============================================================
def download_rank_csv():
    """Download the 21MB CSV file"""
    url = "https://raw.githubusercontent.com/sdgedfegw/Gaokao-score-distribution/main/1996-2024%E5%B9%B4%E5%85%A8%E5%9B%BD%E9%AB%98%E8%80%83%E5%88%86%E6%AE%B5%E8%A1%A8.csv"
    
    cache_path = os.path.join(os.path.dirname(__file__), "data", "rank_table.csv")
    
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 1000000:
        print(f"Using cached: {cache_path} ({os.path.getsize(cache_path)//1024}KB)")
        return cache_path
    
    print(f"Downloading 21MB rank table...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=120)
    
    total = 0
    with open(cache_path, "wb") as f:
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
            if total % (5*1024*1024) == 0:
                print(f"  {total//1024}KB...")
    
    print(f"Downloaded: {total//1024}KB")
    return cache_path


def parse_rank_table(csv_path):
    """
    Parse the CSV and extract score→rank mappings.
    CSV format: 最高分,最低分,人数,累计,省级行政区,综合,年份,总分(裸分),模式
    
    We want: province, category, year → [(score, cumulative_rank), ...]
    Skip years before 2020 to keep data manageable.
    """
    print("Parsing rank table...")
    
    rank_data = defaultdict(lambda: defaultdict(list))  # (province, cat) → {year: [(score, rank)]}
    
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            try:
                year = int(row["年份"])
                if year < 2020:  # Only use recent years
                    continue
                
                province = row["省级行政区"].strip()
                category = row["综合"].strip()
                score = int(row["最低分"])  # Use 最低分 as the score point
                cum_rank = int(row["累计"])  # 累计 = cumulative rank at this score
                
                key = (province, category)
                rank_data[key][year].append((score, cum_rank))
                count += 1
                if count % 500000 == 0:
                    print(f"  {count} rows...")
            except (ValueError, KeyError):
                continue
    
    # Sort each year's data by score descending
    for key in rank_data:
        for year in rank_data[key]:
            rank_data[key][year] = sorted(rank_data[key][year], key=lambda x: x[0], reverse=True)
    
    # Count
    total_rows = sum(sum(len(v) for v in rank_data[k].values()) for k in rank_data)
    print(f"Parsed {total_rows} rows, {len(rank_data)} province-category combos")
    
    # Show sample
    sample_keys = list(rank_data.keys())[:5]
    for key in sample_keys:
        years = sorted(rank_data[key].keys())
        latest = years[-1] if years else None
        if latest:
            points = rank_data[key][latest][:3]
            print(f"  {key}: {len(years)} years, latest={latest}, top3={points}")
    
    return rank_data


def generate_real_ranks_py(rank_data, output_path):
    """Generate updated real_ranks.py with data from CSV"""
    
    # Build the REAL_RANK_TABLES dict
    tables_lines = []
    for (province, category), year_data in sorted(rank_data.items()):
        # Use latest year's data for the rank table
        latest_year = max(year_data.keys())
        data_points = year_data[latest_year]
        
        # Sample every 10 points for compact storage (too many points otherwise)
        sampled = data_points[::10]
        if len(sampled) < 5:
            sampled = data_points
        
        # Format as Python list of tuples
        entries = ", ".join(f"({s},{r})" for s, r in sampled[:50])  # max 50 entries
        
        tables_lines.append(f'    "{province}": {{"{category}": [{entries}]}},')
    
    tables_str = "\n".join(tables_lines)
    
    # Province population coefficients for nonlinear fallback
    # Count total test-takers from the data (max cumulative across years)
    pop_coefs = {}
    for (province, cat), year_data in rank_data.items():
        if 2024 in year_data and year_data[2024]:
            max_rank = year_data[2024][-1][1]  # Last entry = highest rank = total test-takers
            # Scale to reasonable coefficients
            coef = max(30, int(max_rank / 3))
            if province not in pop_coefs or coef > pop_coefs[province]:
                pop_coefs[province] = coef
    
    pop_lines = []
    for prov, coef in sorted(pop_coefs.items()):
        pop_lines.append(f'    "{prov}": {coef},')
    pop_str = "\n".join(pop_lines)
    
    content = f'''"""
真实一分一段数据 — 从 GitHub 开源数据集导入
来源: sdgedfegw/Gaokao-score-distribution (1996-2024)
覆盖: 全31省, 2024年数据
"""
import random

REAL_RANK_TABLES = {{
{tables_str}
}}

PROVINCE_POP_COEF = {{
{pop_str}
}}


def get_real_rank(province, category, score):
    """从真实一分一段表中插值获取位次"""
    table = REAL_RANK_TABLES.get(province, {{}}).get(category)
    if not table:
        return None, False

    if score >= table[0][0]:
        return table[0][1], True
    if score < table[-1][0]:
        last_s, last_r = table[-1]
        if len(table) >= 2:
            second_s, second_r = table[-2]
            slope = (second_r - last_r) / (second_s - last_s) if second_s != last_s else 0
        else:
            slope = 50
        rank = int(last_r + (score - last_s) * slope)
        return max(1, rank), False

    for i in range(len(table) - 1):
        s1, r1 = table[i]
        s2, r2 = table[i + 1]
        if s2 <= score <= s1:
            if s1 == s2:
                return r1, True
            ratio = (score - s2) / (s1 - s2) if s1 != s2 else 0
            rank = int(r2 + (r1 - r2) * ratio)
            return rank, True

    return table[-1][1], False


def estimate_rank_for_seed(province, category, score):
    """为种子数据生成位次：优先用真实数据"""
    rank, is_real = get_real_rank(province, category, score)
    if is_real:
        return rank
    
    # 非线性备用公式
    coef = PROVINCE_POP_COEF.get(province, 1200)
    rank = max(1, int(((750 - score) / 100) ** 1.6 * coef))
    rng = random.Random(hash((province, category, score)) % 2**32)
    jitter = rng.uniform(0.9, 1.1)
    return max(1, int(rank * jitter))
'''
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Generated: {output_path} ({len(content)} bytes)")


# ============================================================
# Part 2: Download and import Shanghai admission data
# ============================================================
def import_shanghai_scores():
    """Import real Shanghai 2024 admission scores into the database"""
    url = "https://raw.githubusercontent.com/xlwang1188/2024_Shanghai_Gaokao_Admissions_Data/main/admissions_2024.csv"
    
    print("\nDownloading Shanghai admission data...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=60)
    content = resp.read().decode('utf-8-sig')
    
    reader = csv.DictReader(io.StringIO(content))
    
    conn = get_db()
    cur = conn.cursor()
    
    # Get university ID map
    uni_map = {}
    for row in cur.execute("SELECT id, name FROM universities").fetchall():
        uni_map[row["name"]] = row["id"]
    
    inserted = 0
    updated = 0
    not_found = set()
    
    for row in reader:
        try:
            uni_name = row["university_name"].strip()
            lowest_score = int(row["lowest_score"])
            lowest_rank = int(row["lowest_rank"]) if row["lowest_rank"] else None
            batch = row["batch"].strip()
            
            uid = uni_map.get(uni_name)
            if not uid:
                # Try fuzzy match
                for name, nid in uni_map.items():
                    if uni_name in name or name in uni_name:
                        uid = nid
                        break
            
            if not uid:
                not_found.add(uni_name)
                continue
            
            # Map batch names
            batch_map = {
                "综合评价录取": "本科批",
                "本科普通批": "本科批",
                "本科提前批": "本科批",
                "本科艺体批": "本科批",
            }
            mapped_batch = batch_map.get(batch, "本科批")
            
            # Map subject to category
            subject_req = row.get("subject_requirements", "").strip()
            if "物理" in subject_req or "物" in subject_req:
                cat = "综合"  # Shanghai uses 综合 for 3+3
            elif "不限" in subject_req:
                cat = "综合"
            else:
                cat = "综合"
            
            # Check if record exists
            existing = cur.execute(
                "SELECT id FROM admission_scores WHERE university_id=? AND province='上海' AND category=? AND year=2024 AND batch=?",
                (uid, cat, mapped_batch)
            ).fetchone()
            
            if existing:
                cur.execute(
                    """UPDATE admission_scores 
                       SET min_score=?, min_rank=?, avg_score=?, max_score=?
                       WHERE id=?""",
                    (lowest_score, lowest_rank, 
                     int(row["average_score"]) if row["average_score"] else lowest_score,
                     int(row["highest_score"]) if row["highest_score"] else lowest_score,
                     existing["id"])
                )
                updated += 1
            else:
                cur.execute(
                    """INSERT INTO admission_scores
                       (university_id, province, year, category, batch, min_score, avg_score, max_score, min_rank)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (uid, "上海", 2024, cat, mapped_batch, 
                     lowest_score,
                     int(row["average_score"]) if row["average_score"] else lowest_score,
                     int(row["highest_score"]) if row["highest_score"] else lowest_score,
                     lowest_rank)
                )
                inserted += 1
            
        except (ValueError, KeyError) as e:
            continue
    
    conn.commit()
    conn.close()
    
    print(f"Shanghai: {inserted} inserted, {updated} updated, {len(not_found)} schools not found")
    if not_found:
        print(f"  Not found (sample): {list(not_found)[:10]}")


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    # Step 1: 一分一段表
    csv_path = download_rank_csv()
    rank_data = parse_rank_table(csv_path)
    
    output_path = os.path.join(os.path.dirname(__file__), "real_ranks.py")
    generate_real_ranks_py(rank_data, output_path)
    
    # Step 2: 上海录取数据
    import_shanghai_scores()
    
    print("\n=== DONE ===")
    print("Next: run master_seed.py to rebuild with real rank data")
