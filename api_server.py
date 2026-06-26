"""
高考志愿推荐 — REST API 服务
启动: python api_server.py --port 8000
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from engine import recommend, get_major_categories

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

app = FastAPI(
    title="高考志愿推荐 API",
    description="基于位次法+线差法的志愿填报推荐服务",
    version="1.0.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── 数据模型 ──

class RecommendRequest(BaseModel):
    score: int = Query(..., ge=0, le=750, description="高考分数")
    rank: int = Query(..., ge=0, description="全省位次")
    province: str = Query(..., description="省份, 如: 河南/广东/北京")
    category: str = Query("理科", description="科类: 理科/文科/物理类/历史类/综合")
    major_category: Optional[str] = Query(None, description="专业门类: 工学/医学/经济学等, 不传=不限")
    top_n: int = Query(8, ge=1, le=50, description="每档返回数量")

class SchoolInfo(BaseModel):
    name: str
    level: str
    city: str
    composite: float
    category: str  # 冲/稳/保
    uni_avg_score: int
    uni_avg_rank: Optional[int]
    advantage_majors: list[str]
    majors_bao: list[str]
    majors_wen: list[str]
    majors_chong: list[str]

class RecommendResponse(BaseModel):
    my_info: dict
    summary: dict
    冲: list[dict]
    稳: list[dict]
    保: list[dict]

# ── 路由 ──

@app.get("/")
def root():
    return {
        "service": "高考志愿推荐 API",
        "version": "1.0.0",
        "endpoints": [
            "GET  /health",
            "GET  /provinces",
            "GET  /categories",
            "GET  /major_categories",
            "POST /recommend",
            "GET  /recommend?score=580&rank=30000&province=河南&category=理科",
        ]
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/provinces")
def list_provinces():
    return {"provinces": [
        "北京","天津","河北","山西","内蒙古","辽宁","吉林","黑龙江",
        "上海","江苏","浙江","安徽","福建","江西","山东","河南",
        "湖北","湖南","广东","广西","海南","重庆","四川","贵州",
        "云南","西藏","陕西","甘肃","青海","宁夏","新疆"
    ]}

@app.get("/categories")
def list_categories():
    return {
        "传统高考": ["理科","文科"],
        "新高考(物理/历史)": ["物理类","历史类"],
        "新高考(综合)": ["综合"],
        "适用省份": {
            "理科/文科": "河南,四川,山西,内蒙古,吉林,黑龙江,安徽,江西,广西,贵州,云南,西藏,陕西,甘肃,青海,宁夏,新疆",
            "物理类/历史类": "河北,辽宁,江苏,福建,湖北,湖南,广东,重庆",
            "综合": "北京,天津,上海,浙江,山东,海南",
        }
    }

@app.get("/major_categories")
def list_major_categories():
    return {"major_categories": get_major_categories()}

@app.post("/recommend", response_model=RecommendResponse)
@app.get("/recommend")
def get_recommend(
    score: int = Query(..., ge=0, le=750),
    rank: int = Query(..., ge=0),
    province: str = Query(...),
    category: str = Query("理科"),
    major_category: Optional[str] = Query(None),
    top_n: int = Query(8, ge=1, le=50),
):
    result = recommend(score, rank, province, category, major_category, top_n)
    if "error" in result:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=result["error"])
    
    # Trim to top_n per category
    result["冲"] = result["冲"][:top_n]
    result["稳"] = result["稳"][:top_n]
    result["保"] = result["保"][:top_n]
    
    return result

# ── 启动 ──
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--host", default="0.0.0.0")
    args = p.parse_args()
    
    print(f"🚀 API Server: http://{args.host}:{args.port}")
    print(f"📖 Docs: http://{args.host}:{args.port}/docs")
    uvicorn.run(app, host=args.host, port=args.port)
