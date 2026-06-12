"""资源池配置 - 数据库模块"""
import sqlite3
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "history.db")

DEFAULT_CONFIG = {
    "gpu_options": {
        "support_kvm": False,
        "strong_management": False,
        "project_control": False,
        "extreme_cost": False
    },
    "compute_options": {
        "special_business": False,
        "default_config": True,
        "add_devices": False,
        "devices": []
    },
    "network_options": {
        "strong_management": False,
        "inband_management_switch": False,
        "management_convergence_switch": False,
        "compute_convergence_switch": False,
        "edge_exit_switch": False,
        "dedicated_line_switch": False,
        "devices": []
    },
    "cost_options": {
        "add_warranty": False,
        "warranty_rate": 0.15,
        "add_software": False,
        "software_items": [],
        "add_integration": False,
        "integration_rate": 0.08
    }
}

# 系统预设模板
SYSTEM_TEMPLATES = [
    {
        "name": "标准GPU资源池",
        "description": "适用于通用GPU计算场景",
        "config": {
            "gpu_options": {
                "support_kvm": True,
                "strong_management": True,
                "project_control": False,
                "extreme_cost": False
            },
            "compute_options": {
                "special_business": False,
                "default_config": True,
                "add_devices": False,
                "devices": [
                    {"name": "GPU服务器", "spec": "NVIDIA A100 80GB x4", "quantity": 2, "unit_price": 350000, "auto_fill": True},
                    {"name": "GPU服务器", "spec": "NVIDIA A30 24GB x8", "quantity": 4, "unit_price": 180000, "auto_fill": True}
                ]
            },
            "network_options": {
                "strong_management": True,
                "inband_management_switch": True,
                "management_convergence_switch": True,
                "compute_convergence_switch": True,
                "edge_exit_switch": False,
                "dedicated_line_switch": False,
                "devices": [
                    {"name": "带内管理交换机", "spec": "48端口万兆", "quantity": 2, "unit_price": 28000, "auto_fill": True},
                    {"name": "管理汇聚交换机", "spec": "40G x4", "quantity": 1, "unit_price": 65000, "auto_fill": True},
                    {"name": "算力汇聚交换机", "spec": "100G x8", "quantity": 1, "unit_price": 120000, "auto_fill": True}
                ]
            },
            "cost_options": {
                "add_warranty": True,
                "warranty_rate": 0.15,
                "add_software": False,
                "software_items": [],
                "add_integration": True,
                "integration_rate": 0.08
            }
        }
    },
    {
        "name": "极致成本GPU资源池",
        "description": "最低成本GPU方案",
        "config": {
            "gpu_options": {
                "support_kvm": False,
                "strong_management": False,
                "project_control": False,
                "extreme_cost": True
            },
            "compute_options": {
                "special_business": False,
                "default_config": True,
                "add_devices": False,
                "devices": [
                    {"name": "GPU服务器", "spec": "NVIDIA A30 24GB x4", "quantity": 2, "unit_price": 120000, "auto_fill": True}
                ]
            },
            "network_options": {
                "strong_management": False,
                "inband_management_switch": True,
                "management_convergence_switch": False,
                "compute_convergence_switch": False,
                "edge_exit_switch": False,
                "dedicated_line_switch": False,
                "devices": [
                    {"name": "带内管理交换机", "spec": "24端口千兆", "quantity": 1, "unit_price": 5000, "auto_fill": True}
                ]
            },
            "cost_options": {
                "add_warranty": False,
                "warranty_rate": 0.15,
                "add_software": False,
                "software_items": [],
                "add_integration": False,
                "integration_rate": 0.08
            }
        }
    },
    {
        "name": "通算资源池",
        "description": "通用计算服务器方案",
        "config": {
            "gpu_options": {
                "support_kvm": False,
                "strong_management": False,
                "project_control": False,
                "extreme_cost": False
            },
            "compute_options": {
                "special_business": False,
                "default_config": True,
                "add_devices": True,
                "devices": [
                    {"name": "通算服务器", "spec": "Intel Xeon 64核 256G内存", "quantity": 4, "unit_price": 85000, "auto_fill": True},
                    {"name": "通算服务器", "spec": "Intel Xeon 32核 128G内存", "quantity": 8, "unit_price": 45000, "auto_fill": True}
                ]
            },
            "network_options": {
                "strong_management": True,
                "inband_management_switch": True,
                "management_convergence_switch": True,
                "compute_convergence_switch": True,
                "edge_exit_switch": True,
                "dedicated_line_switch": False,
                "devices": [
                    {"name": "带内管理交换机", "spec": "48端口万兆", "quantity": 2, "unit_price": 28000, "auto_fill": True},
                    {"name": "管理汇聚交换机", "spec": "40G x4", "quantity": 1, "unit_price": 65000, "auto_fill": True},
                    {"name": "算力汇聚交换机", "spec": "25G x48", "quantity": 1, "unit_price": 55000, "auto_fill": True},
                    {"name": "边缘出口交换机", "spec": "10G x24", "quantity": 1, "unit_price": 35000, "auto_fill": True}
                ]
            },
            "cost_options": {
                "add_warranty": True,
                "warranty_rate": 0.15,
                "add_software": True,
                "software_items": [
                    {"name": "操作系统", "cost": 5000},
                    {"name": "虚拟化平台", "cost": 30000}
                ],
                "add_integration": True,
                "integration_rate": 0.08
            }
        }
    }
]


class ResourcePoolDB:
    """资源池配置数据库"""

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self._init_tables()
        self._ensure_system_templates()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        conn = self._get_conn()
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS rp_template (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                config_json TEXT NOT NULL,
                is_system INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS rp_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                config_json TEXT NOT NULL,
                template_id INTEGER,
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
            conn.commit()
        finally:
            conn.close()

    def _ensure_system_templates(self):
        """确保系统预设模板存在"""
        conn = self._get_conn()
        try:
            count = conn.execute("SELECT COUNT(*) FROM rp_template WHERE is_system=1").fetchone()[0]
            if count == 0:
                for tpl in SYSTEM_TEMPLATES:
                    conn.execute(
                        "INSERT INTO rp_template (name, description, config_json, is_system) VALUES (?,?,?,1)",
                        (tpl["name"], tpl["description"], json.dumps(tpl["config"], ensure_ascii=False))
                    )
                conn.commit()
        finally:
            conn.close()

    # ==================== 模板操作 ====================

    def get_templates(self):
        """获取所有模板列表"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT id, name, description, config_json, is_system, created_at, updated_at FROM rp_template ORDER BY is_system DESC, id"
            ).fetchall()
            result = []
            for r in rows:
                result.append({
                    "id": r["id"],
                    "name": r["name"],
                    "description": r["description"],
                    "config_json": r["config_json"],
                    "is_system": bool(r["is_system"]),
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"]
                })
            return result
        finally:
            conn.close()

    def get_template(self, tid):
        """获取单个模板详情"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT id, name, description, config_json, is_system, created_at, updated_at FROM rp_template WHERE id=?",
                (tid,)
            ).fetchone()
            if not row:
                return None
            config = json.loads(row["config_json"])
            return {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "config": config,
                "is_system": bool(row["is_system"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }
        finally:
            conn.close()

    def create_template(self, name, description="", config=None):
        """创建新模板"""
        if config is None:
            config = DEFAULT_CONFIG
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "INSERT INTO rp_template (name, description, config_json, is_system) VALUES (?,?,?,0)",
                (name, description, json.dumps(config, ensure_ascii=False))
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def delete_template(self, tid):
        """删除模板（系统模板不可删除）"""
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT is_system FROM rp_template WHERE id=?", (tid,)).fetchone()
            if not row:
                return False
            if row["is_system"]:
                return False
            conn.execute("DELETE FROM rp_template WHERE id=?", (tid,))
            conn.commit()
            return True
        finally:
            conn.close()

    def import_template_from_json(self, json_data):
        """从JSON数据导入模板"""
        name = json_data.get("name", "导入模板")
        description = json_data.get("description", "从文件导入")
        config = json_data.get("config", DEFAULT_CONFIG)
        return self.create_template(name, description, config)

    # ==================== 配置操作 ====================

    def get_configs(self):
        """获取所有已保存配置列表"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT id, name, config_json, template_id, status, created_at, updated_at FROM rp_config ORDER BY updated_at DESC"
            ).fetchall()
            result = []
            for r in rows:
                result.append({
                    "id": r["id"],
                    "name": r["name"],
                    "config_json": r["config_json"],
                    "template_id": r["template_id"],
                    "status": r["status"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"]
                })
            return result
        finally:
            conn.close()

    def get_config(self, cid):
        """获取单个配置详情"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT id, name, config_json, template_id, status, created_at, updated_at FROM rp_config WHERE id=?",
                (cid,)
            ).fetchone()
            if not row:
                return None
            config = json.loads(row["config_json"])
            return {
                "id": row["id"],
                "name": row["name"],
                "config": config,
                "template_id": row["template_id"],
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }
        finally:
            conn.close()

    def save_config(self, name, config=None, template_id=None, status="draft"):
        """保存新配置"""
        if config is None:
            config = DEFAULT_CONFIG
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "INSERT INTO rp_config (name, config_json, template_id, status) VALUES (?,?,?,?)",
                (name, json.dumps(config, ensure_ascii=False), template_id, status)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def update_config(self, cid, name=None, config=None, status=None):
        """更新配置"""
        conn = self._get_conn()
        try:
            sets = []
            params = []
            if name is not None:
                sets.append("name=?")
                params.append(name)
            if config is not None:
                sets.append("config_json=?")
                params.append(json.dumps(config, ensure_ascii=False))
            if status is not None:
                sets.append("status=?")
                params.append(status)
            if not sets:
                return
            sets.append("updated_at=CURRENT_TIMESTAMP")
            params.append(cid)
            conn.execute(
                "UPDATE rp_config SET " + ",".join(sets) + " WHERE id=?",
                params
            )
            conn.commit()
        finally:
            conn.close()

    def delete_config(self, cid):
        """删除配置"""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM rp_config WHERE id=?", (cid,))
            conn.commit()
        finally:
            conn.close()
