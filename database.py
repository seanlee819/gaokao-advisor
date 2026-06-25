"""
高考志愿填报 - 数据库层
SQLite WAL模式 + 大缓存
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "gaokao.db")

# 模块加载时配置WAL + 缓存（持久化生效）
def _init_pragmas():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")      # 64MB
    conn.execute("PRAGMA mmap_size=268435456")    # 256MB
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.close()

_init_pragmas()


def get_db():
    """每次连接复用WAL模式（PRAGMA持久化，打开即生效）"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表结构"""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS province_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            province TEXT NOT NULL,
            year INTEGER NOT NULL,
            category TEXT NOT NULL,
            batch TEXT NOT NULL,
            score INTEGER NOT NULL,
            rank INTEGER,
            UNIQUE(province, year, category, batch)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS universities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            code TEXT,
            city TEXT,
            level TEXT,
            type TEXT,
            is_public INTEGER DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS admission_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            university_id INTEGER NOT NULL,
            province TEXT NOT NULL,
            year INTEGER NOT NULL,
            category TEXT NOT NULL,
            batch TEXT NOT NULL,
            min_score INTEGER NOT NULL,
            avg_score INTEGER,
            max_score INTEGER,
            min_rank INTEGER,
            UNIQUE(university_id, province, year, category, batch),
            FOREIGN KEY(university_id) REFERENCES universities(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS majors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            employment_score REAL,
            avg_salary INTEGER,
            difficulty_offset INTEGER DEFAULT 0,
            description TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS uni_majors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            university_id INTEGER NOT NULL,
            major_id INTEGER NOT NULL,
            is_advantage INTEGER DEFAULT 0,
            UNIQUE(university_id, major_id),
            FOREIGN KEY(university_id) REFERENCES universities(id),
            FOREIGN KEY(major_id) REFERENCES majors(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS admission_policies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            university_id INTEGER NOT NULL UNIQUE,
            admission_rule TEXT NOT NULL,
            grade_diff TEXT,
            subject_requirements TEXT,
            physical_restrictions TEXT,
            bonus_policy TEXT,
            special_plans TEXT,
            FOREIGN KEY(university_id) REFERENCES universities(id)
        )
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully.")


if __name__ == "__main__":
    init_db()
