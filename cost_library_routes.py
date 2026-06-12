"""成本库 - API路由"""
import logging
from flask import Blueprint, request, jsonify
from cost_library_db import CostLibraryDB

logger = logging.getLogger(__name__)
cl_bp = Blueprint("cost_library", __name__)
cl_db = CostLibraryDB()


@cl_bp.route("/api/cl/servers", methods=["GET"])
def get_servers():
    """获取设备服务器列表"""
    try:
        category = request.args.get("category")
        data = cl_db.get_servers(category)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        logger.exception("获取设备服务器列表失败")
        return jsonify({"status": "error", "message": str(e)})


@cl_bp.route("/api/cl/servers/<int:server_id>", methods=["GET"])
def get_server(server_id):
    """获取设备服务器详情"""
    try:
        data = cl_db.get_server(server_id)
        if not data:
            return jsonify({"status": "error", "message": "服务器不存在"}), 404
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        logger.exception("获取设备服务器详情失败")
        return jsonify({"status": "error", "message": str(e)})


@cl_bp.route("/api/cl/servers", methods=["POST"])
def create_server():
    """创建设备服务器"""
    try:
        data = request.get_json()
        name = data.get("name", "未命名服务器")
        category = data.get("category", "gpu_server")
        brand = data.get("brand", "")
        model = data.get("model", "")
        description = data.get("description", "")
        sid = cl_db.create_server(name, category, brand, model, description)
        # 如果有细项，批量保存
        items = data.get("items", [])
        if items:
            cl_db.batch_save_items(sid, items)
        return jsonify({"status": "success", "data": {"id": sid}})
    except Exception as e:
        logger.exception("创建设备服务器失败")
        return jsonify({"status": "error", "message": str(e)})


@cl_bp.route("/api/cl/servers/<int:server_id>", methods=["PUT"])
def update_server(server_id):
    """更新设备服务器"""
    try:
        data = request.get_json()
        name = data.get("name")
        category = data.get("category")
        brand = data.get("brand")
        model = data.get("model")
        description = data.get("description")
        status = data.get("status")
        items = data.get("items")
        cl_db.update_server(server_id, name=name, category=category, brand=brand,
                            model=model, description=description, status=status)
        if items is not None:
            cl_db.batch_save_items(server_id, items)
        return jsonify({"status": "success"})
    except Exception as e:
        logger.exception("更新设备服务器失败")
        return jsonify({"status": "error", "message": str(e)})


@cl_bp.route("/api/cl/servers/<int:server_id>", methods=["DELETE"])
def delete_server(server_id):
    """删除设备服务器"""
    try:
        cl_db.delete_server(server_id)
        return jsonify({"status": "success"})
    except Exception as e:
        logger.exception("删除设备服务器失败")
        return jsonify({"status": "error", "message": str(e)})


@cl_bp.route("/api/cl/servers/<int:server_id>/duplicate", methods=["POST"])
def duplicate_server(server_id):
    """复制设备服务器"""
    try:
        new_id = cl_db.duplicate_server(server_id)
        if new_id is None:
            return jsonify({"status": "error", "message": "服务器不存在"}), 404
        return jsonify({"status": "success", "data": {"id": new_id}})
    except Exception as e:
        logger.exception("复制设备服务器失败")
        return jsonify({"status": "error", "message": str(e)})


@cl_bp.route("/api/cl/servers/<int:server_id>/confirm", methods=["POST"])
def confirm_server(server_id):
    """确认设备服务器成本"""
    try:
        cl_db.update_server(server_id, status="confirmed")
        return jsonify({"status": "success", "message": "成本已确认"})
    except Exception as e:
        logger.exception("确认设备服务器失败")
        return jsonify({"status": "error", "message": str(e)})


# ==================== 成本细项操作 ====================

@cl_bp.route("/api/cl/servers/<int:server_id>/items", methods=["GET"])
def get_items(server_id):
    """获取服务器成本细项"""
    try:
        server = cl_db.get_server(server_id)
        if not server:
            return jsonify({"status": "error", "message": "服务器不存在"}), 404
        return jsonify({"status": "success", "data": server.get("items", [])})
    except Exception as e:
        logger.exception("获取成本细项失败")
        return jsonify({"status": "error", "message": str(e)})


@cl_bp.route("/api/cl/servers/<int:server_id>/items", methods=["POST"])
def add_item(server_id):
    """添加成本细项"""
    try:
        data = request.get_json()
        item_id = cl_db.add_item(
            server_id,
            item_type=data.get("item_type", ""),
            item_name=data.get("item_name", ""),
            brand=data.get("brand", ""),
            spec=data.get("spec", ""),
            unit_price=data.get("unit_price", 0),
            quantity=data.get("quantity", 1),
            subtotal=data.get("subtotal", 0),
            remark=data.get("remark", ""),
            sort_order=data.get("sort_order", 0)
        )
        return jsonify({"status": "success", "data": {"id": item_id}})
    except Exception as e:
        logger.exception("添加成本细项失败")
        return jsonify({"status": "error", "message": str(e)})


@cl_bp.route("/api/cl/items/<int:item_id>", methods=["PUT"])
def update_item(item_id):
    """更新成本细项"""
    try:
        data = request.get_json()
        cl_db.update_item(
            item_id,
            item_type=data.get("item_type"),
            item_name=data.get("item_name"),
            brand=data.get("brand"),
            spec=data.get("spec"),
            unit_price=data.get("unit_price"),
            quantity=data.get("quantity"),
            subtotal=data.get("subtotal"),
            remark=data.get("remark"),
            sort_order=data.get("sort_order")
        )
        return jsonify({"status": "success"})
    except Exception as e:
        logger.exception("更新成本细项失败")
        return jsonify({"status": "error", "message": str(e)})


@cl_bp.route("/api/cl/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    """删除成本细项"""
    try:
        cl_db.delete_item(item_id)
        return jsonify({"status": "success"})
    except Exception as e:
        logger.exception("删除成本细项失败")
        return jsonify({"status": "error", "message": str(e)})


@cl_bp.route("/api/cl/categories", methods=["GET"])
def get_categories():
    """获取服务器类别列表"""
    categories = [
        {"key": "gpu_server", "label": "GPU服务器", "icon": "bi-gpu-card"},
        {"key": "compute_server", "label": "通算服务器", "icon": "bi-hdd-stack"},
        {"key": "storage_server", "label": "存储服务器", "icon": "bi-hdd"},
        {"key": "network_device", "label": "网络设备", "icon": "bi-ethernet"},
        {"key": "other", "label": "其他设备", "icon": "bi-box"}
    ]
    return jsonify({"status": "success", "data": categories})


@cl_bp.route("/api/cl/item-types", methods=["GET"])
def get_item_types():
    """获取细项类型列表"""
    item_types = [
        {"key": "cpu", "label": "CPU"},
        {"key": "gpu", "label": "GPU"},
        {"key": "memory", "label": "内存"},
        {"key": "storage", "label": "硬盘"},
        {"key": "network", "label": "网卡"},
        {"key": "mainboard", "label": "主板"},
        {"key": "power", "label": "电源"},
        {"key": "chassis", "label": "机箱"},
        {"key": "radiator", "label": "散热器"},
        {"key": "software", "label": "软件"},
        {"key": "warranty", "label": "维保"},
        {"key": "integration", "label": "集成服务"},
        {"key": "other", "label": "其他"}
    ]
    return jsonify({"status": "success", "data": item_types})
