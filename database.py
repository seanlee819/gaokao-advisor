"""
高考志愿填报 - 数据库层
SQLite存储: 省份批次线、院校录取线、院校信息
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "gaokao.db")


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表结构"""
    conn = get_db()
    cur = conn.cursor()

    # 省份批次线
    cur.execute("""
        CREATE TABLE IF NOT EXISTS province_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            province TEXT NOT NULL,        -- 省份
            year INTEGER NOT NULL,         -- 年份
            category TEXT NOT NULL,        -- 科类: 理科/物理类, 文科/历史类
            batch TEXT NOT NULL,           -- 批次: 本科一批/本科二批/专科批
            score INTEGER NOT NULL,        -- 批次线分数
            rank INTEGER,                  -- 对应位次(如有)
            UNIQUE(province, year, category, batch)
        )
    """)

    # 院校信息
    cur.execute("""
        CREATE TABLE IF NOT EXISTS universities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,     -- 院校名称
            code TEXT,                     -- 院校代码
            city TEXT,                     -- 所在城市
            level TEXT,                    -- 层次: 985/211/双一流/普通本科/专科
            type TEXT,                     -- 类型: 综合/理工/师范/医学/财经等
            is_public INTEGER DEFAULT 1    -- 是否公办
        )
    """)

    # 院校录取分数线（分省分科类）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admission_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            university_id INTEGER NOT NULL,
            province TEXT NOT NULL,
            year INTEGER NOT NULL,
            category TEXT NOT NULL,        -- 理科/物理类, 文科/历史类
            batch TEXT NOT NULL,           -- 批次
            min_score INTEGER NOT NULL,    -- 最低录取分
            avg_score INTEGER,             -- 平均录取分
            max_score INTEGER,             -- 最高录取分
            min_rank INTEGER,              -- 最低分位次
            UNIQUE(university_id, province, year, category, batch),
            FOREIGN KEY(university_id) REFERENCES universities(id)
        )
    """)

    # 专业信息(简化)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS majors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,            -- 专业名称
            category TEXT,                 -- 学科门类: 工学/理学/医学/经济学等
            employment_score REAL,         -- 就业评分 1-10
            avg_salary INTEGER,            -- 平均薪资(元)
            difficulty_offset INTEGER DEFAULT 0,  -- 录取难度偏移(相对院校均分), 负=容易 正=热门难进
            description TEXT               -- 专业简介
        )
    """)

    # 院校-专业关联(哪些院校开设哪些优势专业)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS uni_majors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            university_id INTEGER NOT NULL,
            major_id INTEGER NOT NULL,
            is_advantage INTEGER DEFAULT 0,  -- 是否优势/特色专业
            UNIQUE(university_id, major_id),
            FOREIGN KEY(university_id) REFERENCES universities(id),
            FOREIGN KEY(major_id) REFERENCES majors(id)
        )
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully.")


if __name__ == "__main__":
    init_db()
