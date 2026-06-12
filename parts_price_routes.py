
"""配件时价 - API路由"""
import logging
from flask import Blueprint, request, jsonify
from parts_price_db import PartsPriceDB
from parts_crawler import run_crawl_task, run_all_crawl_tasks

logger = logging.getLogger(__name__)
pp_bp = Blueprint("parts_price", __name__)
pp_db = PartsPriceDB()


@pp_bp.route("/api/pp/summary", methods=["GET"])
def get_price_summary():
    """获取最新价格汇总"""
    try:
        level = request.args.get("level", "consumer")
        part_type = request.args.get("part_type", "cpu")
        data = pp_db.get_price_summary(level, part_type)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        logger.exception("获取价格汇总失败")
        return jsonify({"status": "error", "message": str(e)})


@pp_bp.route("/api/pp/latest", methods=["GET"])
def get_latest_prices():
    """获取最新价格列表"""
    try:
        level = request.args.get("level", "consumer")
        part_type = request.args.get("part_type", "cpu")
        brand = request.args.get("brand")
        spec = request.args.get("spec")
        days = request.args.get("days", 7, type=int)
        data = pp_db.get_latest_prices(level, part_type, brand, spec, days)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        logger.exception("获取最新价格失败")
        return jsonify({"status": "error", "message": str(e)})


@pp_bp.route("/api/pp/history", methods=["GET"])
def get_price_history():
    """获取价格历史趋势"""
    try:
        level = request.args.get("level", "consumer")
        part_type = request.args.get("part_type", "cpu")
        brand = request.args.get("brand")
        spec = request.args.get("spec")
        days = request.args.get("days", 30, type=int)
        data = pp_db.get_price_history(level, part_type, brand, spec, days)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        logger.exception("获取价格历史失败")
        return jsonify({"status": "error", "message": str(e)})


@pp_bp.route("/api/pp/brands", methods=["GET"])
def get_brands():
    """获取品牌列表"""
    try:
        level = request.args.get("level", "consumer")
        part_type = request.args.get("part_type", "cpu")
        data = pp_db.get_brands(level, part_type)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        logger.exception("获取品牌列表失败")
        return jsonify({"status": "error", "message": str(e)})


@pp_bp.route("/api/pp/specs", methods=["GET"])
def get_specs():
    """获取规格列表"""
    try:
        level = request.args.get("level", "consumer")
        part_type = request.args.get("part_type", "memory")
        data = pp_db.get_specs(level, part_type)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        logger.exception("获取规格列表失败")
        return jsonify({"status": "error", "message": str(e)})


@pp_bp.route("/api/pp/latest-date", methods=["GET"])
def get_latest_date():
    """获取最新数据日期"""
    try:
        level = request.args.get("level", "consumer")
        part_type = request.args.get("part_type", "cpu")
        data = pp_db.get_latest_date(level, part_type)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        logger.exception("获取最新日期失败")
        return jsonify({"status": "error", "message": str(e)})


@pp_bp.route("/api/pp/has-today", methods=["GET"])
def has_today_data():
    """检查今天是否有数据"""
    try:
        level = request.args.get("level", "consumer")
        part_type = request.args.get("part_type", "cpu")
        data = pp_db.has_today_data(level, part_type)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        logger.exception("检查今日数据失败")
        return jsonify({"status": "error", "message": str(e)})


@pp_bp.route("/api/pp/crawl", methods=["POST"])
def start_crawl():
    """启动爬取任务"""
    try:
        data = request.get_json() or {}
        level = data.get("level")
        part_type = data.get("part_type")
        if level and part_type:
            task_id = run_crawl_task(level, part_type)
            return jsonify({"status": "success", "data": {"task_id": task_id, "level": level, "part_type": part_type}})
        else:
            tasks = run_all_crawl_tasks()
            return jsonify({"status": "success", "data": {"tasks": tasks, "message": "已启动全部爬取任务"}})
    except Exception as e:
        logger.exception("启动爬取失败")
        return jsonify({"status": "error", "message": str(e)})


@pp_bp.route("/api/pp/tasks", methods=["GET"])
def get_tasks():
    """获取爬取任务列表"""
    try:
        limit = request.args.get("limit", 20, type=int)
        data = pp_db.get_tasks(limit)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        logger.exception("获取任务列表失败")
        return jsonify({"status": "error", "message": str(e)})
