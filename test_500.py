import sys
sys.path.insert(0,'/opt/gaokao_advisor')
from engine import recommend

r = recommend(500, 240000, '河南', '理科', top_n=3)
info = r.get('my_info', {})
print(f"批次: {info.get('batch')}, 批次线: {info.get('batch_line')}")
s = r.get('summary', {})
print(f"总数: {s.get('total')} | 冲:{s.get('冲')} 稳:{s.get('稳')} 保:{s.get('保')}")
print()

for cat in ['冲','稳','保']:
    items = r.get(cat, [])
    print(f'=== {cat} ({len(items)}所) ===')
    for item in items[:5]:
        print(f"  {item['name']:14s} {item['level'] or '-':6s} {item['city']:4s} 均分{item['uni_avg_score']} 综合{item['composite']}")
