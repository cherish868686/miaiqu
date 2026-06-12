"""资源池配置 - API路由"""
import os
import json
import logging
from flask import Blueprint, request, jsonify, Response, send_file
from resource_pool import ResourcePoolDB, DEFAULT_CONFIG
from resource_pool_export import export_to_excel, export_to_word

logger = logging.getLogger(__name__)
rp_bp = Blueprint("resource_pool", __name__)
rp_db = ResourcePoolDB()


@rp_bp.route("/api/rp/templates", methods=["GET"])
def get_templates():
    try:
        templates = rp_db.get_templates()
        for t in templates:
            t["config"] = json.loads(t["config_json"])
        return jsonify({"status": "success", "data": templates})
    except Exception as e:
        logger.exception("获取模板列表失败")
        return jsonify({"status": "error", "message": str(e)})


@rp_bp.route("/api/rp/templates/<int:tid>", methods=["GET"])
def get_template(tid):
    try:
        t = rp_db.get_template(tid)
        if not t:
            return jsonify({"status": "error", "message": "模板不存在"}), 404
        return jsonify({"status": "success", "data": t})
    except Exception as e:
        logger.exception("获取模板详情失败")
        return jsonify({"status": "error", "message": str(e)})


@rp_bp.route("/api/rp/templates", methods=["POST"])
def create_template():
    try:
        data = request.get_json()
        name = data.get("name", "未命名模板")
        description = data.get("description", "")
        config = data.get("config", DEFAULT_CONFIG)
        tid = rp_db.create_template(name, description, config)
        return jsonify({"status": "success", "data": {"id": tid}})
    except Exception as e:
        logger.exception("创建模板失败")
        return jsonify({"status": "error", "message": str(e)})


@rp_bp.route("/api/rp/templates/<int:tid>", methods=["DELETE"])
def delete_template(tid):
    try:
        ok = rp_db.delete_template(tid)
        if not ok:
            return jsonify({"status": "error", "message": "系统模板不可删除"}), 403
        return jsonify({"status": "success"})
    except Exception as e:
        logger.exception("删除模板失败")
        return jsonify({"status": "error", "message": str(e)})


@rp_bp.route("/api/rp/templates/upload", methods=["POST"])
def upload_template():
    try:
        if "file" not in request.files:
            return jsonify({"status": "error", "message": "请上传文件"}), 400
        f = request.files["file"]
        content = f.read().decode("utf-8")
        json_data = json.loads(content)
        tid = rp_db.import_template_from_json(json_data)
        return jsonify({"status": "success", "data": {"id": tid}})
    except json.JSONDecodeError:
        return jsonify({"status": "error", "message": "文件格式错误，请上传JSON文件"}), 400
    except Exception as e:
        logger.exception("上传模板失败")
        return jsonify({"status": "error", "message": str(e)})


@rp_bp.route("/api/rp/default-config", methods=["GET"])
def get_default_config():
    return jsonify({"status": "success", "data": DEFAULT_CONFIG})


@rp_bp.route("/api/rp/configs", methods=["GET"])
def get_configs():
    try:
        configs = rp_db.get_configs()
        for c in configs:
            c["config"] = json.loads(c["config_json"])
        return jsonify({"status": "success", "data": configs})
    except Exception as e:
        logger.exception("获取配置列表失败")
        return jsonify({"status": "error", "message": str(e)})


@rp_bp.route("/api/rp/configs/<int:cid>", methods=["GET"])
def get_config(cid):
    try:
        c = rp_db.get_config(cid)
        if not c:
            return jsonify({"status": "error", "message": "配置不存在"}), 404
        return jsonify({"status": "success", "data": c})
    except Exception as e:
        logger.exception("获取配置详情失败")
        return jsonify({"status": "error", "message": str(e)})


@rp_bp.route("/api/rp/configs", methods=["POST"])
def save_config():
    try:
        data = request.get_json()
        name = data.get("name", "未命名配置")
        config = data.get("config", DEFAULT_CONFIG)
        template_id = data.get("template_id")
        status = data.get("status", "draft")
        cid = rp_db.save_config(name, config, template_id, status)
        return jsonify({"status": "success", "data": {"id": cid}})
    except Exception as e:
        logger.exception("保存配置失败")
        return jsonify({"status": "error", "message": str(e)})


@rp_bp.route("/api/rp/configs/<int:cid>", methods=["PUT"])
def update_config(cid):
    try:
        data = request.get_json()
        name = data.get("name")
        config = data.get("config")
        status = data.get("status")
        rp_db.update_config(cid, name=name, config=config, status=status)
        return jsonify({"status": "success"})
    except Exception as e:
        logger.exception("更新配置失败")
        return jsonify({"status": "error", "message": str(e)})


@rp_bp.route("/api/rp/configs/<int:cid>", methods=["DELETE"])
def delete_config(cid):
    try:
        rp_db.delete_config(cid)
        return jsonify({"status": "success"})
    except Exception as e:
        logger.exception("删除配置失败")
        return jsonify({"status": "error", "message": str(e)})


@rp_bp.route("/api/rp/configs/<int:cid>/confirm", methods=["POST"])
def confirm_config(cid):
    try:
        rp_db.update_config(cid, status="confirmed")
        return jsonify({"status": "success", "message": "配置已确认"})
    except Exception as e:
        logger.exception("确认配置失败")
        return jsonify({"status": "error", "message": str(e)})


@rp_bp.route("/api/rp/configs/<int:cid>/export", methods=["GET"])
def export_config(cid):
    try:
        c = rp_db.get_config(cid)
        if not c:
            return jsonify({"status": "error", "message": "配置不存在"}), 404
        fmt = request.args.get("format", "excel")
        config = c["config"]
        name = c["name"]
        if fmt == "word":
            data = export_to_word(config, name)
            mimetype = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ext = "docx"
        else:
            data = export_to_excel(config, name)
            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ext = "xlsx"
        from io import BytesIO
        buf = BytesIO(data)
        return send_file(buf, as_attachment=True, download_name=f"{name}.{ext}", mimetype=mimetype)
    except Exception as e:
        logger.exception("导出配置失败")
        return jsonify({"status": "error", "message": str(e)})
