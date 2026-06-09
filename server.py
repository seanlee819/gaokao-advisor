"""
生产级 API 服务 — 网页版 + 微信小程序 共用后端
启动: python server.py --port 8000
"""
import sys, os, time, hashlib, hmac, json
sys.path.insert(0, os.path.dirname(__file__))
from engine import recommend, get_major_categories
from auth import register_user, login_user, get_user, increment_query, get_tier_limits, upgrade_tier
from database import get_db

from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn

app = FastAPI(title="高考志愿推荐 API", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── 简易 API Key (生产环境替换为 JWT) ──
API_SECRET = "gaokao2026_secret_key_change_in_production"

def make_token(user_id):
    payload = f"{user_id}:{int(time.time())}"
    sig = hmac.new(API_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{payload}:{sig}"

def verify_token(token):
    try:
        parts = token.split(":")
        if len(parts) != 3: return None
        uid, ts, sig = parts
        expected = hmac.new(API_SECRET.encode(), f"{uid}:{ts}".encode(), hashlib.sha256).hexdigest()[:16]
        return int(uid) if sig == expected else None
    except:
        return None

# ── 数据模型 ──
class LoginRequest(BaseModel):
    email: str; password: str

class RegisterRequest(BaseModel):
    email: str; password: str; nickname: Optional[str] = None

class RecommendQuery(BaseModel):
    score: int; rank: int; province: str; category: str = "理科"
    major_category: Optional[str] = None; top_n: int = 8

# ── 路由 ──
@app.get("/")
def root():
    return {"service": "高考志愿推荐 API v2.0", "docs": "/docs"}

@app.get("/health")
def health(): return {"status": "ok", "time": time.time()}

@app.post("/api/register")
def api_register(req: RegisterRequest):
    user, err = register_user(req.email, req.password, req.nickname)
    if err: raise HTTPException(400, err)
    return {"token": make_token(user['id']), "user": user}

@app.post("/api/login")
def api_login(req: LoginRequest):
    user, err = login_user(req.email, req.password)
    if err: raise HTTPException(401, err)
    return {"token": make_token(user['id']), "user": user}

@app.get("/api/me")
def api_me(token: str = Query(...)):
    uid = verify_token(token)
    if not uid: raise HTTPException(401, "invalid token")
    user = get_user(uid)
    if not user: raise HTTPException(404, "user not found")
    limits = get_tier_limits(user['tier'])
    return {"user": user, "limits": limits}

@app.post("/api/recommend")
def api_recommend(req: RecommendQuery, token: Optional[str] = Query(None)):
    # 可选认证: 有token就记录查询, 无token也允许基础推荐
    user = None
    if token:
        uid = verify_token(token)
        if uid: user = get_user(uid)
    
    limits = get_tier_limits(user['tier'] if user else 'free')
    
    if user and user['query_count'] >= limits['max_queries']:
        raise HTTPException(429, "查询次数已用完，请升级")
    
    result = recommend(req.score, req.rank, req.province, req.category, req.major_category, req.top_n)
    
    if user:
        increment_query(user['id'])
    
    if "error" in result:
        raise HTTPException(400, result["error"])
    
    # 裁剪到对应等级
    result["冲"] = result["冲"][:limits['top_n']]
    result["稳"] = result["稳"][:limits['top_n']]
    result["保"] = result["保"][:limits['top_n']]
    
    return result

@app.get("/api/provinces")
def api_provinces():
    return {"provinces": sorted([
        "北京","天津","河北","山西","内蒙古","辽宁","吉林","黑龙江",
        "上海","江苏","浙江","安徽","福建","江西","山东","河南",
        "湖北","湖南","广东","广西","海南","重庆","四川","贵州",
        "云南","西藏","陕西","甘肃","青海","宁夏","新疆"
    ])}

@app.get("/api/major_categories")
def api_major_cats():
    return {"categories": get_major_categories()}

# ── 小程序专用: 免登录快速推荐 (限制更严) ──
@app.get("/api/miniapp/quick")
def miniapp_quick(score: int, rank: int, province: str, category: str = "理科"):
    """微信小程序快速推荐: 无需登录, 免费版限制"""
    result = recommend(score, rank, province, category)
    if "error" in result: raise HTTPException(400, result["error"])
    result["冲"] = result["冲"][:3]; result["稳"] = result["稳"][:3]; result["保"] = result["保"][:3]
    return result

# ── 支付接口 (预留, 后续接入 xorpay/微信支付) ──
@app.post("/api/payment/create")
def create_payment(tier: str, token: str = Query(...)):
    """创建支付订单"""
    uid = verify_token(token)
    if not uid: raise HTTPException(401, "invalid token")
    if tier not in ("enhanced", "complete"): raise HTTPException(400, "invalid tier")

    prices = {"enhanced": 9.9, "complete": 29.9}
    order_id = f"GK{int(time.time())}{uid}"

    # TODO: 接入真实支付网关后替换为实际支付链接
    return {
        "order_id": order_id,
        "amount": prices[tier],
        "tier": tier,
        "status": "pending",
        "note": "支付功能即将上线, 请联系管理员手动开通"
    }

@app.post("/api/payment/callback")
async def payment_callback(request: Request):
    """支付回调 (xorpay/微信支付调用此接口)"""
    body = await request.json()
    # TODO: 验证签名, 更新用户等级
    # order_id = body.get("order_id")
    # uid = extract from order_id
    # upgrade_tier(uid, tier)
    return {"code": 0, "msg": "ok"}

# ── 院校详情 ──
@app.get("/api/school/{university_id}")
def school_detail(university_id: int, province: str = Query(...), category: str = Query("理科")):
    """获取院校详情 + 录取历史 + 专业列表"""
    conn = get_db()
    uni = conn.execute(
        "SELECT id, name, code, city, level, type, is_public FROM universities WHERE id=?",
        (university_id,)
    ).fetchone()
    if not uni:
        conn.close()
        raise HTTPException(404, "院校不存在")

    # 录取历史
    history = conn.execute(
        """SELECT year, batch, min_score, avg_score, max_score, min_rank
           FROM admission_scores
           WHERE university_id=? AND province=? AND category=?
           ORDER BY year DESC""",
        (university_id, province, category)
    ).fetchall()

    # 优势专业
    majors = conn.execute(
        """SELECT m.name, m.category, m.employment_score, m.avg_salary, m.difficulty_offset,
                  um.is_advantage
           FROM uni_majors um JOIN majors m ON um.major_id = m.id
           WHERE um.university_id=?
           ORDER BY um.is_advantage DESC, m.employment_score DESC
           LIMIT 15""",
        (university_id,)
    ).fetchall()
    conn.close()

    return {
        "university": dict(uni),
        "history": [dict(h) for h in history],
        "majors": [dict(m) for m in majors],
    }

# ── 管理后台 (admin key 验证) ──
ADMIN_KEY = "kanjinbang2026"

def check_admin(key: str):
    if key != ADMIN_KEY:
        raise HTTPException(403, "无管理权限")

@app.get("/api/admin/users")
def admin_list_users(key: str = Query(...)):
    """列出所有用户"""
    check_admin(key)
    conn = get_db()
    rows = conn.execute(
        "SELECT id, email, nickname, tier, query_count, created_at, last_login FROM users ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return {"users": [dict(r) for r in rows]}

@app.post("/api/admin/upgrade")
def admin_upgrade(email: str, tier: str, key: str = Query(...)):
    """管理员升级用户等级"""
    check_admin(key)
    if tier not in ("enhanced", "complete"):
        raise HTTPException(400, "等级只能是 enhanced 或 complete")
    conn = get_db()
    row = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "用户不存在")
    conn.execute("UPDATE users SET tier=?, query_count=0 WHERE id=?", (tier, row["id"]))
    conn.commit()
    conn.close()
    return {"ok": True, "msg": f"{email} 已升级为 {tier}"}

@app.post("/api/admin/reset")
def admin_reset(email: str, key: str = Query(...)):
    """重置用户查询次数"""
    check_admin(key)
    conn = get_db()
    row = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "用户不存在")
    conn.execute("UPDATE users SET query_count=0 WHERE id=?", (row["id"],))
    conn.commit()
    conn.close()
    return {"ok": True, "msg": f"{email} 查询次数已重置"}

# ── 启动 ──
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--host", default="0.0.0.0")
    args = p.parse_args()
    print(f"🚀 API: http://{args.host}:{args.port}")
    print(f"📖 Docs: http://{args.host}:{args.port}/docs")
    uvicorn.run(app, host=args.host, port=args.port)
