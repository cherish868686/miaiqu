"""配件时价数据库模块"""
import sqlite3
import os
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "history.db")

CONSUMER_CPU_BRANDS = ["Intel", "AMD"]
CONSUMER_GPU_BRANDS = ["NVIDIA", "AMD", "Intel"]
CONSUMER_MEMORY_BRANDS = ["江波龙", "朗科", "金士顿", "海力士", "金百达", "冰火岛", "镁光", "雷克沙", "三星"]
CONSUMER_MEMORY_SPECS = [
    "DDR4 3200MHz 16G", "DDR4 3200MHz 32G",
    "DDR5 4800MHz 16G", "DDR5 4800MHz 32G",
    "DDR5 5600MHz 16G", "DDR5 5600MHz 32G",
    "DDR5 6000MHz 16G", "DDR5 6000MHz 32G"
]
CONSUMER_STORAGE_BRANDS = ["江波龙", "朗科", "金士顿", "海力士", "金百达", "冰火岛", "镁光", "雷克沙", "三星"]
CONSUMER_STORAGE_SPECS = ["M.2 NVMe 512G", "M.2 NVMe 1T"]

INDUSTRIAL_CPU_BRANDS = ["Intel", "AMD"]
INDUSTRIAL_GPU_BRANDS = ["NVIDIA", "AMD", "Intel"]
INDUSTRIAL_MEMORY_BRANDS = ["江波龙", "朗科", "金士顿", "海力士", "镁光", "雷克沙"]
INDUSTRIAL_MEMORY_SPECS = [
    "DDR4 3200MHz 32G", "DDR4 3200MHz 64G",
    "DDR5 4800MHz 32G", "DDR5 4800MHz 64G",
    "DDR5 5600MHz 32G", "DDR5 5600MHz 64G"
]
INDUSTRIAL_STORAGE_BRANDS = ["江波龙", "朗科", "金士顿", "海力士", "金百达", "冰火岛", "镁光", "雷克沙", "三星"]
INDUSTRIAL_STORAGE_SPECS = [
    "SATA SSD 480G", "SATA SSD 960G", "SATA SSD 1.92T", "SATA SSD 3.84T", "SATA SSD 7.68T",
    "U.2 NVMe SSD 480G", "U.2 NVMe SSD 960G", "U.2 NVMe SSD 1.92T", "U.2 NVMe SSD 3.84T", "U.2 NVMe SSD 7.68T",
    "M.2 NVMe SSD 480G", "M.2 NVMe SSD 960G", "M.2 NVMe SSD 1.92T", "M.2 NVMe SSD 3.84T", "M.2 NVMe SSD 7.68T"
]

CRAWL_SOURCES = [
    {"name": "淘宝", "base_url": "https://s.taobao.com/search?q={keyword}"},
    {"name": "京东", "base_url": "https://search.jd.com/Search?keyword={keyword}"},
    {"name": "天猫", "base_url": "https://list.tmall.com/search_product.htm?q={keyword}"},
    {"name": "拼多多", "base_url": "https://mobile.yangkeduo.com/search_result.html?search_key={keyword}"},
    {"name": "苏宁易购", "base_url": "https://search.suning.com/{keyword}/"},
    {"name": "国美", "base_url": "https://search.gome.com.cn/search?question={keyword}"},
    {"name": "当当网", "base_url": "http://search.dangdang.com/?key={keyword}"},
    {"name": "1号店", "base_url": "https://search.yhd.com/c0-0/k{keyword}"},
    {"name": "亚马逊中国", "base_url": "https://www.amazon.cn/s?k={keyword}"},
    {"name": "中关村在线", "base_url": "https://search.zol.com.cn/s.php?word={keyword}"},
    {"name": "太平洋电脑网", "base_url": "https://search.pconline.com.cn/?q={keyword}"},
    {"name": "天猫超市", "base_url": "https://list.tmall.com/search_product.htm?q={keyword}&type=chaoshi"},
]


class PartsPriceDB:
    """配件时价数据库"""

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self._init_tables()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        conn = self._get_conn()
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS parts_price (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                level TEXT NOT NULL,
                part_type TEXT NOT NULL,
                brand TEXT NOT NULL,
                model TEXT NOT NULL,
                spec TEXT,
                price REAL,
                source TEXT,
                source_url TEXT,
                price_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
            conn.execute("""CREATE INDEX IF NOT EXISTS idx_parts_category ON parts_price(category, level, part_type)""")
            conn.execute("""CREATE INDEX IF NOT EXISTS idx_parts_date ON parts_price(price_date)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS parts_price_task (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT NOT NULL,
                level TEXT NOT NULL,
                part_type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                started_at TIMESTAMP,
                finished_at TIMESTAMP,
                items_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
            conn.commit()
        finally:
            conn.close()

    def save_prices(self, prices):
        conn = self._get_conn()
        try:
            for p in prices:
                conn.execute(
                    "INSERT INTO parts_price (category, level, part_type, brand, model, spec, price, source, source_url, price_date) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (p.get("category"), p.get("level"), p.get("part_type"),
                     p.get("brand"), p.get("model"), p.get("spec"),
                     p.get("price"), p.get("source"), p.get("source_url"),
                     p.get("price_date", datetime.now().strftime("%Y-%m-%d"))))
            conn.commit()
        finally:
            conn.close()

    def get_latest_prices(self, level, part_type, brand=None, spec=None, days=7):
        conn = self._get_conn()
        try:
            since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            sql = "SELECT * FROM parts_price WHERE level=? AND part_type=? AND price_date>=?"
            params = [level, part_type, since]
            if brand:
                sql += " AND brand=?"
                params.append(brand)
            if spec:
                sql += " AND spec=?"
                params.append(spec)
            sql += " ORDER BY price_date DESC, brand, model"
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_price_summary(self, level, part_type):
        conn = self._get_conn()
        try:
            sql = """SELECT p.* FROM parts_price p
                     INNER JOIN (
                         SELECT brand, spec, model, MAX(price_date) as max_date
                         FROM parts_price
                         WHERE level=? AND part_type=?
                         GROUP BY brand, spec, model
                     ) latest ON p.brand=latest.brand AND p.spec=latest.spec
                              AND p.model=latest.model AND p.price_date=latest.max_date
                     WHERE p.level=? AND p.part_type=?
                     ORDER BY p.brand, p.spec, p.model"""
            rows = conn.execute(sql, (level, part_type, level, part_type)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_price_history(self, level, part_type, brand=None, spec=None, days=30):
        conn = self._get_conn()
        try:
            since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            sql = "SELECT price_date, brand, model, spec, AVG(price) as avg_price, MIN(price) as min_price, MAX(price) as max_price FROM parts_price WHERE level=? AND part_type=? AND price_date>=?"
            params = [level, part_type, since]
            if brand:
                sql += " AND brand=?"
                params.append(brand)
            if spec:
                sql += " AND spec=?"
                params.append(spec)
            sql += " GROUP BY price_date, brand, model, spec ORDER BY price_date"
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_brands(self, level, part_type):
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT DISTINCT brand FROM parts_price WHERE level=? AND part_type=? ORDER BY brand",
                (level, part_type)).fetchall()
            return [r["brand"] for r in rows]
        finally:
            conn.close()

    def get_specs(self, level, part_type):
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT DISTINCT spec FROM parts_price WHERE level=? AND part_type=? AND spec IS NOT NULL ORDER BY spec",
                (level, part_type)).fetchall()
            return [r["spec"] for r in rows]
        finally:
            conn.close()

    def create_task(self, task_name, level, part_type):
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO parts_price_task (task_name, level, part_type) VALUES (?,?,?)",
                (task_name, level, part_type))
            conn.commit()
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        finally:
            conn.close()

    def update_task(self, task_id, status=None, items_count=None):
        conn = self._get_conn()
        try:
            now = datetime.now().isoformat()
            if status == "running":
                conn.execute("UPDATE parts_price_task SET status=?, started_at=? WHERE id=?",
                             (status, now, task_id))
            elif status in ("done", "failed"):
                conn.execute("UPDATE parts_price_task SET status=?, finished_at=?, items_count=? WHERE id=?",
                             (status, now, items_count or 0, task_id))
            conn.commit()
        finally:
            conn.close()

    def get_tasks(self, limit=20):
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM parts_price_task ORDER BY created_at DESC LIMIT ?",
                (limit,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_latest_date(self, level, part_type):
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT MAX(price_date) as latest FROM parts_price WHERE level=? AND part_type=?",
                (level, part_type)).fetchone()
            return row["latest"] if row else None
        finally:
            conn.close()

    def has_today_data(self, level, part_type):
        today = datetime.now().strftime("%Y-%m-%d")
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM parts_price WHERE level=? AND part_type=? AND price_date=?",
                (level, part_type, today)).fetchone()
            return row["cnt"] > 0
        finally:
            conn.close()
