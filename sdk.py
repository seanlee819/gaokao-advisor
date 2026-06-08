"""
高考志愿推荐 — Python SDK / 调用示例
安装: 复制 sdk.py 到项目目录即可, 无外部依赖
"""

import json, urllib.request

class GaokaoAdvisor:
    """高考志愿推荐客户端"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
    
    def _get(self, path, params=None):
        if params:
            qs = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
            url = f"{self.base_url}{path}?{qs}"
        else:
            url = f"{self.base_url}{path}"
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.loads(resp.read())
    
    def health(self):
        """健康检查"""
        return self._get("/health")
    
    def provinces(self):
        """获取支持的省份列表"""
        return self._get("/provinces")["provinces"]
    
    def categories(self):
        """获取科类说明"""
        return self._get("/categories")
    
    def major_categories(self):
        """获取专业门类列表"""
        return self._get("/major_categories")["major_categories"]
    
    def recommend(self, score, rank, province, category="理科", major=None, top_n=8):
        """
        核心推荐接口
        
        参数:
            score: int — 高考分数 (0-750)
            rank: int — 全省位次
            province: str — 省份, 如 "河南"
            category: str — 科类, 默认"理科"
            major: str — 专业门类, 如"工学"/"医学", None=不限
            top_n: int — 每档返回数量, 默认8
        
        返回:
            {
                "my_info": {...},
                "summary": {"total": N, "冲": N, "稳": N, "保": N},
                "冲": [{school}, ...],
                "稳": [{school}, ...],
                "保": [{school}, ...],
            }
        """
        return self._get("/recommend", {
            "score": score, "rank": rank, "province": province,
            "category": category, "major_category": major, "top_n": top_n
        })


# ── 使用示例 ──
if __name__ == "__main__":
    advisor = GaokaoAdvisor("http://localhost:8000")
    
    # 1. 检查服务
    print("健康检查:", advisor.health())
    
    # 2. 获取专业门类
    print("\n专业门类:", advisor.major_categories())
    
    # 3. 推荐
    print("\n河南理科 580分/30000位:")
    r = advisor.recommend(580, 30000, "河南", "理科")
    print(f"  总计: {r['summary']['total']}所 (冲{r['summary']['冲']} 稳{r['summary']['稳']} 保{r['summary']['保']})")
    for tag in ["冲","稳","保"]:
        schools = r[tag][:3]
        names = [f"{s['name']}({s['composite']:.0f})" for s in schools]
        print(f"  {tag}: {', '.join(names)}")
