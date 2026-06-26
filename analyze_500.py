import sys
sys.path.insert(0,'/opt/gaokao_advisor')
from engine import recommend

r = recommend(500, 240000, '河南', '理科', top_n=20)

# 统计分布
from collections import Counter
composites = []
for cat in ['冲','稳','保']:
    for item in r.get(cat, []):
        composites.append(item['composite'])
        if item['level']:
            pass

composites.sort()
print(f"Composite范围: {min(composites):.1f} - {max(composites):.1f}")
print(f"总数: {len(composites)}")

# 分档统计
buckets = Counter()
for c in composites:
    bucket = int(c // 10) * 10
    buckets[bucket] += 1
for k in sorted(buckets):
    print(f"  {k}-{k+9}: {buckets[k]}所")

# 按层次统计
level_count = Counter()
for cat in ['冲','稳','保']:
    for item in r.get(cat, []):
        lv = item['level'] or '无标签'
        key = f"{cat}/{lv}/{item['is_public']}"
        level_count[key] += 1

print("\n按层次+公办:")
for k in sorted(set(k.split('/')[0] for k in level_count)):
    for full in sorted(level_count):
        if full.startswith(k+'/'):
            print(f"  {full}: {level_count[full]}")
