"""
用户认证系统 — 注册/登录/会员等级
SQLite存储, 密码哈希
"""
import sqlite3, hashlib, os, time
from database import get_db

def init_auth_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nickname TEXT,
            tier TEXT DEFAULT 'free',
            created_at REAL,
            last_login REAL,
            query_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def hash_password(password):
    salt = os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}${h.hex()}"

def verify_password(password, stored):
    salt, h = stored.split('$')
    computed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return computed.hex() == h

def register_user(email, password, nickname=None):
    conn = get_db()
    cur = conn.cursor()
    existing = cur.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if existing:
        conn.close()
        return None, "该邮箱已注册"
    now = time.time()
    cur.execute(
        "INSERT INTO users (email, password_hash, nickname, tier, created_at, last_login) VALUES (?,?,?,?,?,?)",
        (email, hash_password(password), nickname or email.split('@')[0], 'free', now, now)
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return {"id": user_id, "email": email, "tier": "free", "query_count": 0}, None

def login_user(email, password):
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not row:
        conn.close()
        return None, "账号不存在"
    if not verify_password(password, row['password_hash']):
        conn.close()
        return None, "密码错误"
    conn.execute("UPDATE users SET last_login=? WHERE id=?", (time.time(), row['id']))
    conn.commit()
    result = {
        "id": row['id'], "email": row['email'], "nickname": row['nickname'],
        "tier": row['tier'], "query_count": row['query_count']
    }
    conn.close()
    return result, None

def get_user(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if row:
        result = {"id": row['id'], "email": row['email'], "nickname": row['nickname'],
                "tier": row['tier'], "query_count": row['query_count']}
        conn.close()
        return result
    conn.close()
    return None

def increment_query(user_id):
    conn = get_db()
    conn.execute("UPDATE users SET query_count = query_count + 1 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

def get_tier_limits(tier):
    tiers = {
        "free": {"name": "免费版", "top_n": 3, "show_majors": False, "show_rank": False, "export": False, "max_queries": 3, "price": "¥0", "color": "#888"},
        "enhanced": {"name": "增强版", "top_n": 10, "show_majors": True, "show_rank": True, "export": False, "max_queries": 30, "price": "¥9.9", "color": "#1a73e8"},
        "complete": {"name": "完全版", "top_n": 20, "show_majors": True, "show_rank": True, "export": True, "max_queries": 9999, "price": "¥29.9", "color": "#ff8c00"},
    }
    return tiers.get(tier, tiers["free"])

def upgrade_tier(user_id, new_tier):
    if new_tier not in ("enhanced", "complete"):
        return False, "无效的等级"
    conn = get_db()
    conn.execute("UPDATE users SET tier=?, query_count=0 WHERE id=?", (new_tier, user_id))
    conn.commit()
    conn.close()
    return True, None

init_auth_db()
