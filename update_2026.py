"""
update_2026.py — 生成2026年批次线和录取分数
策略: 2025→2026 批次线-2分, 录取分数同比例调整
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from database import get_db
from real_ranks import get_real_rank, estimate_rank_for_seed, REAL_RANK_TABLES
import random

random.seed(2026)

def update():
    conn = get_db()
    conn.execute("PRAGMA journal_mode=WAL")
    
    # ===== 1. 删除已有2026数据 (INSERT OR REPLACE模式) =====
    # 实际上直接INSERT OR REPLACE就可以
    
    # ===== 2. 2025批次线 → 2026 (-2分) =====
    print("生成2026批次线...")
    rows = conn.execute("SELECT province, category, batch, score, rank FROM province_lines WHERE year=2025").fetchall()
    count = 0
    for r in rows:
        new_score = r['score'] - 2
        # 估算2026位次 (粗略: 一分≈1000-2000人, 用省级系数)
        rank_2025 = r['rank']
        # 简单: rank变化约+3-5% (考生数微增)
        new_rank = int(rank_2025 * random.uniform(1.02, 1.05)) if rank_2025 else 0
        
        conn.execute("""
            INSERT OR REPLACE INTO province_lines (province, category, batch, year, score, rank)
            VALUES (?, ?, ?, 2026, ?, ?)
        """, (r['province'], r['category'], r['batch'], new_score, new_rank))
        count += 1
    print(f"  {count}条批次线")
    
    # ===== 3. 2025录取分 → 2026 (同幅度调整) =====
    print("生成2026录取分数...")
    
    # 为每个province/category/batch计算2025→2026线差
    batch_shifts = {}
    for r in conn.execute("""
        SELECT p25.province, p25.category, p25.batch, 
               p25.score as s25, p26.score as s26
        FROM province_lines p25 
        JOIN province_lines p26 ON p25.province=p26.province 
            AND p25.category=p26.category AND p25.batch=p26.batch
        WHERE p25.year=2025 AND p26.year=2026
    """).fetchall():
        key = (r['province'], r['category'], r['batch'])
        batch_shifts[key] = r['s26'] - r['s25']
    
    # 处理每条2025录取记录
    rows = conn.execute("SELECT * FROM admission_scores WHERE year=2025").fetchall()
    inserted = 0
    batch_size = 5000
    
    for i, r in enumerate(rows):
        key = (r['province'], r['category'], r['batch'])
        shift = batch_shifts.get(key, -2)
        
        new_score = r['min_score'] + shift
        new_avg = r['avg_score'] + shift
        new_max = r['max_score'] + shift
        
        # 粗略估算2026位次
        if r['min_rank'] and r['min_rank'] > 0:
            new_rank = int(r['min_rank'] * random.uniform(1.01, 1.04))
        else:
            new_rank = 0
        
        conn.execute("""
            INSERT OR REPLACE INTO admission_scores 
            (university_id, province, category, batch, year, min_score, avg_score, max_score, min_rank)
            VALUES (?, ?, ?, ?, 2026, ?, ?, ?, ?)
        """, (r['university_id'], r['province'], r['category'], r['batch'],
              new_score, new_avg, new_max, new_rank))
        inserted += 1
        
        if inserted % 20000 == 0:
            conn.commit()
            print(f"  {inserted}/{len(rows)}...")
    
    conn.commit()
    print(f"  {inserted}条录取记录")
    
    # ===== 4. 验证 =====
    verify(conn)
    conn.close()
    print("\n✅ 2026数据生成完成")

def verify(conn):
    print("\n=== 验证 ===")
    rows = conn.execute("SELECT year, COUNT(*) FROM province_lines GROUP BY year ORDER BY year").fetchall()
    for r in rows:
        print(f"  批次线 {r[0]}: {r[1]}条")
    
    rows = conn.execute("SELECT year, COUNT(*) FROM admission_scores GROUP BY year ORDER BY year").fetchall()
    for r in rows:
        print(f"  录取分 {r[0]}: {r[1]:,}条")
    
    # 2026样本
    print("\n  2026批次线样本:")
    for prov, cat in [('河南','理科'), ('北京','综合'), ('广东','物理类')]:
        row = conn.execute("""
            SELECT batch, score FROM province_lines 
            WHERE province=? AND category=? AND year=2026 AND batch LIKE '%本科%'
            ORDER BY batch
        """, (prov, cat)).fetchall()
        for r in row:
            print(f"    {prov} {cat} {r[0]}: {r[1]}分")

if __name__ == '__main__':
    # 备份
    import shutil
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'gaokao.db')
    bak_path = db_path + '.bak3'
    shutil.copy(db_path, bak_path)
    print(f"备份: {bak_path}\n")
    update()
