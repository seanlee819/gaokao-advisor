"""
回测: 用已知院校的录取分/位次模拟考生，验证推荐算法是否合理
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(__file__))
from engine import recommend
from database import get_db
from real_ranks import get_real_rank

def backtest(province, category, n_cases=50):
    """随机抽取n_cases个已知录取记录作为"考生"，跑推荐，统计命中率"""
    conn = get_db()
    
    # 拉取该省该科类所有院校的历史录取数据
    rows = conn.execute("""
        SELECT u.name, u.level, a.min_score, a.min_rank, a.batch, a.year
        FROM admission_scores a
        JOIN universities u ON u.id = a.university_id
        WHERE a.province=? AND a.category=?
          AND a.year IN (2023, 2024, 2025)
          AND a.min_rank IS NOT NULL
    """, (province, category)).fetchall()
    conn.close()
    
    # 按 (院校, 年份) 分组取平均
    school_years = {}
    for r in rows:
        key = (r["name"], r["year"])
        if key not in school_years:
            school_years[key] = {"level": r["level"], "scores": [], "ranks": []}
        school_years[key]["scores"].append(r["min_score"])
        school_years[key]["ranks"].append(r["min_rank"])
    
    # 取最近一年的数据作为"考生"模拟
    candidates = [(name, yr, d["level"],
                   int(sum(d["scores"])/len(d["scores"])),
                   int(sum(d["ranks"])/len(d["ranks"])))
                  for (name, yr), d in school_years.items() if yr == 2024]
    
    if len(candidates) < n_cases:
        n_cases = len(candidates)
    
    sampled = random.Random(42).sample(candidates, n_cases)
    
    results = {"冲命中": 0, "稳命中": 0, "保命中": 0, "总数": 0, "总校数": 0}
    
    for name, year, level, score, rank in sampled:
        rec = recommend(score, rank, province, category, top_n=30)
        if "error" in rec:
            continue
        
        results["总数"] += 1
        for tier, key in [("冲", "冲"), ("稳", "稳"), ("保", "保")]:
            schools_in_tier = [s["name"] for s in rec.get(tier, [])]
            results["总校数"] += len(schools_in_tier)
            if name in schools_in_tier:
                results[f"{key}命中"] += 1
    
    return results


if __name__ == "__main__":
    print("=" * 55)
    print("位次修复后回测 — 以2024录取分为考生模拟")
    print("(用自己的分数报自己，看是否落入正确的冲/稳/保档)")
    print("=" * 55)
    
    for prov, cat in [("河南","理科"), ("四川","理科"), ("广东","物理类"), ("北京","综合")]:
        r = backtest(prov, cat, 50)
        print(f"\n{prov} {cat} ({r['总数']}个考生):")
        print(f"  冲命中: {r['冲命中']}/{r['总数']} ({r['冲命中']/r['总数']*100:.0f}%)")
        print(f"  稳命中: {r['稳命中']}/{r['总数']} ({r['稳命中']/r['总数']*100:.0f}%)")
        print(f"  保命中: {r['保命中']}/{r['总数']} ({r['保命中']/r['总数']*100:.0f}%)")
        total_hit = r['冲命中'] + r['稳命中'] + r['保命中']
        print(f"  总命中: {total_hit}/{r['总数']} ({total_hit/r['总数']*100:.0f}%)")
