"""成本库 - 数据库模块"""
import sqlite3
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "history.db")


class CostLibraryDB:
    """成本库数据库"""

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
            # 设备服务器成本主表
            conn.execute("""CREATE TABLE IF NOT EXISTS cost_server (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'gpu_server',
                brand TEXT,
                model TEXT,
                description TEXT DEFAULT '',
                total_cost REAL DEFAULT 0,
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
            # 成本细项表
            conn.execute("""CREATE TABLE IF NOT EXISTS cost_item (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER NOT NULL,
                item_type TEXT NOT NULL,
                item_name TEXT NOT NULL,
                brand TEXT,
                spec TEXT,
                unit_price REAL DEFAULT 0,
                quantity INTEGER DEFAULT 1,
                subtotal REAL DEFAULT 0,
                remark TEXT DEFAULT '',
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (server_id) REFERENCES cost_server(id) ON DELETE CASCADE)""")
            conn.execute("""CREATE INDEX IF NOT EXISTS idx_cost_item_server ON cost_item(server_id)""")
            conn.execute("""CREATE INDEX IF NOT EXISTS idx_cost_server_category ON cost_server(category)""")
            conn.commit()
        finally:
            conn.close()

    # ==================== 设备服务器操作 ====================

    def get_servers(self, category=None):
        """获取设备服务器列表"""
        conn = self._get_conn()
        try:
            if category:
                rows = conn.execute(
                    "SELECT * FROM cost_server WHERE category=? ORDER BY updated_at DESC",
                    (category,)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM cost_server ORDER BY updated_at DESC").fetchall()
            result = []
            for r in rows:
                server = dict(r)
                server["items"] = self._get_items(conn, server["id"])
                result.append(server)
            return result
        finally:
            conn.close()

    def get_server(self, server_id):
        """获取单个设备服务器详情"""
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM cost_server WHERE id=?", (server_id,)).fetchone()
            if not row:
                return None
            server = dict(row)
            server["items"] = self._get_items(conn, server_id)
            return server
        finally:
            conn.close()

    def create_server(self, name, category="gpu_server", brand="", model="", description=""):
        """创建设备服务器"""
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO cost_server (name, category, brand, model, description) VALUES (?,?,?,?,?)",
                (name, category, brand, model, description))
            conn.commit()
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        finally:
            conn.close()

    def update_server(self, server_id, name=None, category=None, brand=None, model=None,
                      description=None, status=None, total_cost=None):
        """更新设备服务器"""
        conn = self._get_conn()
        try:
            fields = []
            params = []
            if name is not None:
                fields.append("name=?")
                params.append(name)
            if category is not None:
                fields.append("category=?")
                params.append(category)
            if brand is not None:
                fields.append("brand=?")
                params.append(brand)
            if model is not None:
                fields.append("model=?")
                params.append(model)
            if description is not None:
                fields.append("description=?")
                params.append(description)
            if status is not None:
                fields.append("status=?")
                params.append(status)
            if total_cost is not None:
                fields.append("total_cost=?")
                params.append(total_cost)
            fields.append("updated_at=CURRENT_TIMESTAMP")
            params.append(server_id)
            conn.execute("UPDATE cost_server SET " + ",".join(fields) + " WHERE id=?", params)
            conn.commit()
        finally:
            conn.close()

    def delete_server(self, server_id):
        """删除设备服务器及其细项"""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM cost_item WHERE server_id=?", (server_id,))
            conn.execute("DELETE FROM cost_server WHERE id=?", (server_id,))
            conn.commit()
        finally:
            conn.close()

    def duplicate_server(self, server_id):
        """复制设备服务器"""
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM cost_server WHERE id=?", (server_id,)).fetchone()
            if not row:
                return None
            new_name = row["name"] + " (副本)"
            conn.execute(
                "INSERT INTO cost_server (name, category, brand, model, description, total_cost, status) VALUES (?,?,?,?,?,?,?)",
                (new_name, row["category"], row["brand"], row["model"], row["description"],
                 row["total_cost"], "draft"))
            new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            items = conn.execute("SELECT * FROM cost_item WHERE server_id=?", (server_id,)).fetchall()
            for item in items:
                conn.execute(
                    "INSERT INTO cost_item (server_id, item_type, item_name, brand, spec, unit_price, quantity, subtotal, remark, sort_order) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (new_id, item["item_type"], item["item_name"], item["brand"], item["spec"],
                     item["unit_price"], item["quantity"], item["subtotal"], item["remark"], item["sort_order"]))
            conn.commit()
            return new_id
        finally:
            conn.close()

    # ==================== 成本细项操作 ====================

    def _get_items(self, conn, server_id):
        """获取服务器的成本细项"""
        rows = conn.execute(
            "SELECT * FROM cost_item WHERE server_id=? ORDER BY sort_order, id",
            (server_id,)).fetchall()
        return [dict(r) for r in rows]

    def add_item(self, server_id, item_type, item_name, brand="", spec="",
                 unit_price=0, quantity=1, subtotal=0, remark="", sort_order=0):
        """添加成本细项"""
        conn = self._get_conn()
        try:
            if subtotal == 0 and unit_price > 0 and quantity > 0:
                subtotal = unit_price * quantity
            conn.execute(
                "INSERT INTO cost_item (server_id, item_type, item_name, brand, spec, unit_price, quantity, subtotal, remark, sort_order) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (server_id, item_type, item_name, brand, spec, unit_price, quantity, subtotal, remark, sort_order))
            conn.commit()
            item_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            self._recalc_server_total(server_id)
            return item_id
        finally:
            conn.close()

    def update_item(self, item_id, item_type=None, item_name=None, brand=None, spec=None,
                    unit_price=None, quantity=None, subtotal=None, remark=None, sort_order=None):
        """更新成本细项"""
        conn = self._get_conn()
        try:
            fields = []
            params = []
            if item_type is not None:
                fields.append("item_type=?")
                params.append(item_type)
            if item_name is not None:
                fields.append("item_name=?")
                params.append(item_name)
            if brand is not None:
                fields.append("brand=?")
                params.append(brand)
            if spec is not None:
                fields.append("spec=?")
                params.append(spec)
            if unit_price is not None:
                fields.append("unit_price=?")
                params.append(unit_price)
            if quantity is not None:
                fields.append("quantity=?")
                params.append(quantity)
            if subtotal is not None:
                fields.append("subtotal=?")
                params.append(subtotal)
            if remark is not None:
                fields.append("remark=?")
                params.append(remark)
            if sort_order is not None:
                fields.append("sort_order=?")
                params.append(sort_order)
            params.append(item_id)
            conn.execute("UPDATE cost_item SET " + ",".join(fields) + " WHERE id=?", params)
            conn.commit()
            # 获取server_id并重算总价
            row = conn.execute("SELECT server_id FROM cost_item WHERE id=?", (item_id,)).fetchone()
            if row:
                self._recalc_server_total(row["server_id"])
        finally:
            conn.close()

    def delete_item(self, item_id):
        """删除成本细项"""
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT server_id FROM cost_item WHERE id=?", (item_id,)).fetchone()
            conn.execute("DELETE FROM cost_item WHERE id=?", (item_id,))
            conn.commit()
            if row:
                self._recalc_server_total(row["server_id"])
        finally:
            conn.close()

    def batch_save_items(self, server_id, items):
        """批量保存成本细项（先删后增）"""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM cost_item WHERE server_id=?", (server_id,))
            for i, item in enumerate(items):
                unit_price = float(item.get("unit_price", 0))
                quantity = int(item.get("quantity", 1))
                subtotal = float(item.get("subtotal", 0))
                if subtotal == 0 and unit_price > 0 and quantity > 0:
                    subtotal = unit_price * quantity
                conn.execute(
                    "INSERT INTO cost_item (server_id, item_type, item_name, brand, spec, unit_price, quantity, subtotal, remark, sort_order) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (server_id, item.get("item_type", ""), item.get("item_name", ""),
                     item.get("brand", ""), item.get("spec", ""),
                     unit_price, quantity, subtotal,
                     item.get("remark", ""), i))
            conn.commit()
            self._recalc_server_total(server_id)
        finally:
            conn.close()

    def _recalc_server_total(self, server_id):
        """重算服务器总价"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT COALESCE(SUM(subtotal),0) as total FROM cost_item WHERE server_id=?",
                (server_id,)).fetchone()
            conn.execute("UPDATE cost_server SET total_cost=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                         (row["total"], server_id))
            conn.commit()
        finally:
            conn.close()

    # ==================== 统计 ====================

    def get_statistics(self):
        """获取成本库统计"""
        conn = self._get_conn()
        try:
            total_servers = conn.execute("SELECT COUNT(*) FROM cost_server").fetchone()[0]
            total_cost = conn.execute("SELECT COALESCE(SUM(total_cost),0) FROM cost_server").fetchone()[0]
            gpu_count = conn.execute("SELECT COUNT(*) FROM cost_server WHERE category='gpu_server'").fetchone()[0]
            compute_count = conn.execute("SELECT COUNT(*) FROM cost_server WHERE category='compute_server'").fetchone()[0]
            storage_count = conn.execute("SELECT COUNT(*) FROM cost_server WHERE category='storage_server'").fetchone()[0]
            other_count = conn.execute("SELECT COUNT(*) FROM cost_server WHERE category='other_server'").fetchone()[0]
            return {
                "total_servers": total_servers,
                "total_cost": round(total_cost, 2),
                "gpu_count": gpu_count,
                "compute_count": compute_count,
                "storage_count": storage_count,
                "other_count": other_count
            }
        finally:
            conn.close()
