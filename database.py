import sqlite3
import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'history.db')
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化数据库表"""
        conn = self._get_conn()
        try:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS operator_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT,
                    date TEXT,
                    source TEXT,
                    summary TEXT,
                    keyword TEXT,
                    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS competitor_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT,
                    date TEXT,
                    summary TEXT,
                    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS hardware_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT,
                    price TEXT,
                    trend TEXT,
                    url TEXT,
                    summary TEXT,
                    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS task_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT,
                    data_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS config_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_key TEXT NOT NULL,
                    config_value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS crawl_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_key TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    source_url TEXT,
                    task_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT,
                    found_count INTEGER DEFAULT 0,
                    saved_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # 创建去重索引
            try:
                conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_operator_title ON operator_reports(title)')
            except Exception:
                pass
            try:
                conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_competitor_title ON competitor_reports(name, title)')
            except Exception:
                pass
            try:
                conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_hardware_name ON hardware_reports(name)')
            except Exception:
                pass
            conn.commit()
            logger.info("数据库初始化完成")
        finally:
            conn.close()

    def save_operator_data(self, data: List[Dict]) -> int:
        """保存运营商爬取数据（自动去重，重复标题跳过）"""
        conn = self._get_conn()
        saved = 0
        skipped = 0
        try:
            for item in data:
                try:
                    title = item.get('title', '')
                    if not title:
                        continue
                    # 检查是否已存在
                    existing = conn.execute(
                        "SELECT id FROM operator_reports WHERE title = ?", (title,)
                    ).fetchone()
                    if existing:
                        skipped += 1
                        continue
                    conn.execute(
                        "INSERT INTO operator_reports (title, url, date, source, summary, keyword) VALUES (?, ?, ?, ?, ?, ?)",
                        (title, item.get('url', ''), item.get('date', ''),
                         item.get('source', ''), item.get('summary', ''), item.get('keyword', ''))
                    )
                    saved += 1
                except Exception as e:
                    logger.warning(f"保存运营商数据跳过: {e}")
            conn.commit()
            logger.info(f"运营商数据: 保存{saved}条, 跳过重复{skipped}条")
            return saved
        finally:
            conn.close()

    def save_competitor_data(self, data: List[Dict]) -> int:
        """保存友商动态数据（自动去重，重复name+title跳过）"""
        conn = self._get_conn()
        saved = 0
        skipped = 0
        try:
            for item in data:
                try:
                    name = item.get('name', '')
                    title = item.get('title', '')
                    if not title:
                        continue
                    existing = conn.execute(
                        "SELECT id FROM competitor_reports WHERE name = ? AND title = ?", (name, title)
                    ).fetchone()
                    if existing:
                        skipped += 1
                        continue
                    conn.execute(
                        "INSERT INTO competitor_reports (name, title, url, date, summary) VALUES (?, ?, ?, ?, ?)",
                        (name, title, item.get('url', ''),
                         item.get('date', ''), item.get('summary', ''))
                    )
                    saved += 1
                except Exception as e:
                    logger.warning(f"保存友商数据跳过: {e}")
            conn.commit()
            logger.info(f"友商数据: 保存{saved}条, 跳过重复{skipped}条")
            return saved
        finally:
            conn.close()

    def save_hardware_data(self, data: List[Dict]) -> int:
        """保存硬件市场数据（自动去重，重复name跳过）"""
        conn = self._get_conn()
        saved = 0
        skipped = 0
        try:
            for item in data:
                try:
                    name = item.get('name', '')
                    if not name:
                        continue
                    existing = conn.execute(
                        "SELECT id FROM hardware_reports WHERE name = ?", (name,)
                    ).fetchone()
                    if existing:
                        skipped += 1
                        continue
                    conn.execute(
                        "INSERT INTO hardware_reports (name, category, price, trend, url, summary) VALUES (?, ?, ?, ?, ?, ?)",
                        (name, item.get('category', ''), item.get('price', ''),
                         item.get('trend', ''), item.get('url', ''), item.get('summary', ''))
                    )
                    saved += 1
                except Exception as e:
                    logger.warning(f"保存硬件数据跳过: {e}")
            conn.commit()
            logger.info(f"硬件数据: 保存{saved}条, 跳过重复{skipped}条")
            return saved
        finally:
            conn.close()

    def save_task_log(self, task_type: str, status: str, message: str = '', data_count: int = 0):
        """保存任务执行日志"""
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO task_logs (task_type, status, message, data_count) VALUES (?, ?, ?, ?)",
                (task_type, status, message, data_count)
            )
            conn.commit()
        finally:
            conn.close()

    def get_operator_history(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """获取运营商历史数据"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM operator_reports ORDER BY crawled_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_competitor_history(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """获取友商历史数据"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM competitor_reports ORDER BY crawled_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_hardware_history(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """获取硬件历史数据"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM hardware_reports ORDER BY crawled_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_task_logs(self, limit: int = 100) -> List[Dict]:
        """获取任务执行日志"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM task_logs ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        conn = self._get_conn()
        try:
            operator_count = conn.execute("SELECT COUNT(*) FROM operator_reports").fetchone()[0]
            competitor_count = conn.execute("SELECT COUNT(*) FROM competitor_reports").fetchone()[0]
            hardware_count = conn.execute("SELECT COUNT(*) FROM hardware_reports").fetchone()[0]
            task_count = conn.execute("SELECT COUNT(*) FROM task_logs").fetchone()[0]
            today_tasks = conn.execute(
                "SELECT COUNT(*) FROM task_logs WHERE DATE(created_at) = DATE('now')"
            ).fetchone()[0]
            return {
                'operator_count': operator_count,
                'competitor_count': competitor_count,
                'hardware_count': hardware_count,
                'task_count': task_count,
                'today_tasks': today_tasks
            }
        finally:
            conn.close()

    def get_app_logs(self, limit: int = 200) -> List[Dict]:
        """读取应用日志文件"""
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.log')
        logs = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                for line in lines[-limit:]:
                    line = line.strip()
                    if line:
                        parts = line.split(' - ', 3)
                        log_entry = {
                            'time': parts[0] if len(parts) > 0 else '',
                            'name': parts[1] if len(parts) > 1 else '',
                            'level': parts[2] if len(parts) > 2 else '',
                            'message': parts[3] if len(parts) > 3 else line
                        }
                        logs.append(log_entry)
            except Exception as e:
                logger.error(f"读取日志文件失败: {str(e)}")
        return logs

    def delete_operator(self, record_id: int) -> bool:
        """删除单条运营商数据"""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM operator_reports WHERE id = ?", (record_id,))
            conn.commit()
            logger.info(f"已删除运营商数据 id={record_id}")
            return True
        finally:
            conn.close()

    def delete_competitor(self, record_id: int) -> bool:
        """删除单条友商数据"""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM competitor_reports WHERE id = ?", (record_id,))
            conn.commit()
            logger.info(f"已删除友商数据 id={record_id}")
            return True
        finally:
            conn.close()

    def delete_hardware(self, record_id: int) -> bool:
        """删除单条硬件数据"""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM hardware_reports WHERE id = ?", (record_id,))
            conn.commit()
            logger.info(f"已删除硬件数据 id={record_id}")
            return True
        finally:
            conn.close()

    def delete_old_data(self, days: int = 30):
        """删除指定天数前的旧数据"""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM operator_reports WHERE crawled_at < datetime('now', ?)", (f'-{days} days',))
            conn.execute("DELETE FROM competitor_reports WHERE crawled_at < datetime('now', ?)", (f'-{days} days',))
            conn.execute("DELETE FROM hardware_reports WHERE crawled_at < datetime('now', ?)", (f'-{days} days',))
            conn.execute("DELETE FROM task_logs WHERE created_at < datetime('now', ?)", (f'-{days} days',))
            conn.commit()
            logger.info(f"已清理{days}天前的旧数据")
        finally:
            conn.close()

    def search_operator(self, keyword: str = '', date_from: str = '', date_to: str = '',
                        limit: int = 50, offset: int = 0) -> List[Dict]:
        """搜索运营商数据"""
        conn = self._get_conn()
        try:
            query = "SELECT * FROM operator_reports WHERE 1=1"
            params = []
            if keyword:
                query += " AND (title LIKE ? OR source LIKE ? OR keyword LIKE ? OR summary LIKE ?)"
                kw = f'%{keyword}%'
                params.extend([kw, kw, kw, kw])
            if date_from:
                query += " AND date >= ?"
                params.append(date_from)
            if date_to:
                query += " AND date <= ?"
                params.append(date_to)
            query += " ORDER BY crawled_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def search_competitor(self, keyword: str = '', date_from: str = '', date_to: str = '',
                          limit: int = 50, offset: int = 0) -> List[Dict]:
        """搜索友商数据"""
        conn = self._get_conn()
        try:
            query = "SELECT * FROM competitor_reports WHERE 1=1"
            params = []
            if keyword:
                query += " AND (name LIKE ? OR title LIKE ? OR summary LIKE ?)"
                kw = f'%{keyword}%'
                params.extend([kw, kw, kw])
            if date_from:
                query += " AND date >= ?"
                params.append(date_from)
            if date_to:
                query += " AND date <= ?"
                params.append(date_to)
            query += " ORDER BY crawled_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def search_hardware(self, keyword: str = '', date_from: str = '', date_to: str = '',
                        limit: int = 50, offset: int = 0) -> List[Dict]:
        """搜索硬件数据"""
        conn = self._get_conn()
        try:
            query = "SELECT * FROM hardware_reports WHERE 1=1"
            params = []
            if keyword:
                query += " AND (name LIKE ? OR category LIKE ? OR price LIKE ?)"
                kw = f'%{keyword}%'
                params.extend([kw, kw, kw])
            if date_from:
                query += " AND crawled_at >= ?"
                params.append(date_from)
            if date_to:
                query += " AND crawled_at <= ?"
                params.append(date_to)
            query += " ORDER BY crawled_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_trend_data(self, days: int = 7) -> Dict:
        """获取趋势数据"""
        conn = self._get_conn()
        try:
            operator_trend = []
            rows = conn.execute(
                """SELECT DATE(crawled_at) as date, COUNT(*) as count 
                   FROM operator_reports 
                   WHERE crawled_at >= datetime('now', ?) 
                   GROUP BY DATE(crawled_at) ORDER BY date""",
                (f'-{days} days',)
            ).fetchall()
            operator_trend = [{'date': row[0], 'count': row[1]} for row in rows]

            competitor_trend = []
            rows = conn.execute(
                """SELECT DATE(crawled_at) as date, COUNT(*) as count 
                   FROM competitor_reports 
                   WHERE crawled_at >= datetime('now', ?) 
                   GROUP BY DATE(crawled_at) ORDER BY date""",
                (f'-{days} days',)
            ).fetchall()
            competitor_trend = [{'date': row[0], 'count': row[1]} for row in rows]

            hardware_trend = []
            rows = conn.execute(
                """SELECT DATE(crawled_at) as date, COUNT(*) as count 
                   FROM hardware_reports 
                   WHERE crawled_at >= datetime('now', ?) 
                   GROUP BY DATE(crawled_at) ORDER BY date""",
                (f'-{days} days',)
            ).fetchall()
            hardware_trend = [{'date': row[0], 'count': row[1]} for row in rows]

            # 关键词分布
            keyword_dist = []
            rows = conn.execute(
                """SELECT keyword, COUNT(*) as count FROM operator_reports 
                   WHERE keyword IS NOT NULL AND keyword != '' 
                   GROUP BY keyword ORDER BY count DESC LIMIT 10"""
            ).fetchall()
            keyword_dist = [{'keyword': row[0], 'count': row[1]} for row in rows]

            # 友商分布
            competitor_dist = []
            rows = conn.execute(
                """SELECT name, COUNT(*) as count FROM competitor_reports 
                   WHERE name IS NOT NULL AND name != '' 
                   GROUP BY name ORDER BY count DESC LIMIT 10"""
            ).fetchall()
            competitor_dist = [{'name': row[0], 'count': row[1]} for row in rows]

            return {
                'operator_trend': operator_trend,
                'competitor_trend': competitor_trend,
                'hardware_trend': hardware_trend,
                'keyword_distribution': keyword_dist,
                'competitor_distribution': competitor_dist
            }
        finally:
            conn.close()

    def save_crawl_log(self, source_key: str, source_name: str, source_url: str, task_type: str,
                       status: str, message: str = '', found_count: int = 0, saved_count: int = 0):
        """保存单次爬取源的详细记录"""
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO crawl_logs (source_key, source_name, source_url, task_type, status, message, found_count, saved_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (source_key, source_name, source_url, task_type, status, message, found_count, saved_count)
            )
            conn.commit()
        finally:
            conn.close()

    def get_crawl_logs(self, limit: int = 50, task_type: str = '') -> List[Dict]:
        """获取爬取详细日志"""
        conn = self._get_conn()
        try:
            if task_type:
                rows = conn.execute(
                    "SELECT * FROM crawl_logs WHERE task_type=? ORDER BY created_at DESC LIMIT ?",
                    (task_type, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM crawl_logs ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
