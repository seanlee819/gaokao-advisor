"""
fix_subject_categories.py — 修正河南等8省从理科/文科→物理类/历史类
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from database import get_db
import random
random.seed(2026)

# 8 provinces that transitioned: 5th batch (2025 first exam)
FIX_PROVINCES = ["河南","四川","山西","内蒙古","云南","陕西","青海","宁夏"]

CAT_MAP = {"理科": "物理类", "文科": "历史类"}

def fix():
    conn = get_db()
    conn.execute("PRAGMA journal_mode=WAL")
    
    # ===== 1. Update category names in province_lines =====
    for prov in FIX_PROVINCES:
        for old, new in CAT_MAP.items():
            conn.execute("""
                UPDATE province_lines SET category=? 
                WHERE province=? AND category=? AND year>=2025
            """, (new, prov, old))
        print(f"  {prov}: category renamed")
    conn.commit()
    
    # ===== 2. Update category in admission_scores =====
    for prov in FIX_PROVINCES:
        for old, new in CAT_MAP.items():
            conn.execute("""
                UPDATE admission_scores SET category=?
                WHERE province=? AND category=? AND year>=2025
            """, (new, prov, old))
    
    # ===== 3. Merge 本科一批+本科二批 → 本科批 for 2025-2026 =====
    # For 物理类, take 本科一批 as 本科批 (it's the higher line)
    for prov in FIX_PROVINCES:
        for new_cat in ["物理类", "历史类"]:
            # Get the batch line score (use 本科一批 for 2025, or estimate for 2026)
            for year in [2025, 2026]:
                row = conn.execute("""
                    SELECT score FROM province_lines 
                    WHERE province=? AND category=? AND batch='本科一批' AND year=?
                """, (prov, new_cat, year)).fetchone()
                
                if row:
                    new_score = row['score']
                    # Delete old batch lines
                    conn.execute("""
                        DELETE FROM province_lines 
                        WHERE province=? AND category=? AND batch IN ('本科一批','本科二批') AND year=?
                    """, (prov, new_cat, year))
                    # Insert unified batch line
                    conn.execute("""
                        INSERT OR REPLACE INTO province_lines (province, category, batch, year, score, rank)
                        VALUES (?, ?, '本科批', ?, ?, 0)
                    """, (prov, new_cat, year, new_score))
    
    conn.commit()
    
    # ===== 4. Update admission_scores batch names =====
    for prov in FIX_PROVINCES:
        for new_cat in ["物理类", "历史类"]:
            conn.execute("""
                UPDATE admission_scores SET batch='本科批'
                WHERE province=? AND category=? AND batch IN ('本科一批','本科二批') AND year>=2025
            """, (prov, new_cat))
    conn.commit()
    
    # ===== 5. Verify =====
    print("\n=== 验证 ===")
    for prov in FIX_PROVINCES:
        rows = conn.execute("""
            SELECT DISTINCT year, category, batch, score 
            FROM province_lines
            WHERE province=? AND year>=2025 AND batch LIKE '%本科%'
            ORDER BY year, category
        """, (prov,)).fetchall()
        for r in rows:
            print(f"  {prov} {r['year']} {r['category']} {r['batch']}: {r['score']}分")
    
    conn.close()
    print("\n✅ 分类修正完成")

if __name__ == '__main__':
    fix()
