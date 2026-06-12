# parts crawler module
import os, json, logging, threading, time, random, re
from datetime import datetime
from parts_price_db import (
    PartsPriceDB,
    CONSUMER_CPU_BRANDS, CONSUMER_GPU_BRANDS, CONSUMER_MEMORY_BRANDS, CONSUMER_MEMORY_SPECS,
    CONSUMER_STORAGE_BRANDS, CONSUMER_STORAGE_SPECS,
    INDUSTRIAL_CPU_BRANDS, INDUSTRIAL_GPU_BRANDS, INDUSTRIAL_MEMORY_BRANDS, INDUSTRIAL_MEMORY_SPECS,
    INDUSTRIAL_STORAGE_BRANDS, INDUSTRIAL_STORAGE_SPECS,
    CRAWL_SOURCES
)

logger = logging.getLogger(__name__)


CONSUMER_CPU_MODELS = {
    "Intel": [
        "Core i9-14900K", "Core i9-14900KF", "Core i7-14700K", "Core i7-14700KF",
        "Core i5-14600K", "Core i5-14600KF", "Core i9-13900K", "Core i9-13900KF",
        "Core i7-13700K", "Core i7-13700KF", "Core i5-13600K", "Core i5-13600KF",
        "Core i5-13400", "Core i5-13400F", "Core i3-13100", "Core i3-13100F"
    ],
    "AMD": [
        "Ryzen 9 7950X", "Ryzen 9 7950X3D", "Ryzen 9 7900X", "Ryzen 9 7900X3D",
        "Ryzen 7 7700X", "Ryzen 7 7700", "Ryzen 7 7800X3D", "Ryzen 5 7600X",
        "Ryzen 5 7600", "Ryzen 5 7500F", "Ryzen 9 5900X", "Ryzen 7 5800X",
        "Ryzen 7 5700X", "Ryzen 5 5600X", "Ryzen 5 5600", "Ryzen 5 5500"
    ]
}

INDUSTRIAL_CPU_MODELS = {
    "Intel": [
        "Xeon Platinum 8480+", "Xeon Platinum 8468", "Xeon Platinum 8380",
        "Xeon Gold 6348", "Xeon Gold 5318Y", "Xeon Gold 6338",
        "Xeon Silver 4316", "Xeon Silver 4314", "Xeon Bronze 3204",
        "Xeon W-3375X", "Xeon W-2295", "Xeon E-2388G", "Xeon E-2378G"
    ],
    "AMD": [
        "EPYC 9654", "EPYC 9554", "EPYC 9454", "EPYC 9374F",
        "EPYC 9354", "EPYC 9274F", "EPYC 7763", "EPYC 7713",
        "EPYC 7643", "EPYC 7543", "EPYC 7413", "EPYC 7313P"
    ]
}

CONSUMER_GPU_MODELS = {
    "NVIDIA": [
        "RTX 4090", "RTX 4080 SUPER", "RTX 4080", "RTX 4070 Ti SUPER",
        "RTX 4070 Ti", "RTX 4070 SUPER", "RTX 4070", "RTX 4060 Ti",
        "RTX 4060", "RTX 3090", "RTX 3080", "RTX 3070", "RTX 3060"
    ],
    "AMD": [
        "RX 7900 XTX", "RX 7900 XT", "RX 7800 XT", "RX 7700 XT",
        "RX 7600 XT", "RX 7600", "RX 6950 XT", "RX 6800 XT",
        "RX 6750 XT", "RX 6700 XT", "RX 6600 XT"
    ],
    "Intel": [
        "Arc A770", "Arc A750", "Arc A580", "Arc A380"
    ]
}

INDUSTRIAL_GPU_MODELS = {
    "NVIDIA": [
        "A100 80GB", "A100 40GB", "A800 80GB", "A800 40GB",
        "H100 80GB", "H800 80GB", "L40S", "L40", "A30", "A10",
        "V100 32GB", "V100 16GB", "T4", "RTX 6000 Ada", "RTX A6000"
    ],
    "AMD": [
        "Instinct MI300X", "Instinct MI250X", "Instinct MI210",
        "Instinct MI100", "Pro W7900", "Pro W6800"
    ],
    "Intel": [
        "Data Center GPU Max 1550", "Data Center GPU Max 1100",
        "Data Center GPU Flex 170", "Data Center GPU Flex 140"
    ]
}

BASE_PRICES = {
    "i9-14900K": 4299, "i9-14900KF": 4099, "i7-14700K": 2899, "i7-14700KF": 2699,
    "i5-14600K": 1999, "i5-14600KF": 1799, "i9-13900K": 3899, "i9-13900KF": 3699,
    "i7-13700K": 2499, "i7-13700KF": 2299, "i5-13600K": 1699, "i5-13600KF": 1549,
    "i5-13400": 1299, "i5-13400F": 999, "i3-13100": 899, "i3-13100F": 749,
    "7950X": 4499, "7950X3D": 4999, "7900X": 3299, "7900X3D": 3799,
    "7700X": 1899, "7700": 1699, "7800X3D": 2799, "7600X": 1499,
    "7600": 1349, "7500F": 1049, "5900X": 2099, "5800X": 1599,
    "5700X": 1299, "5600X": 999, "5600": 849, "5500": 699,
    "4090": 12999, "4080 SUPER": 7999, "4080": 8499, "4070 Ti SUPER": 5999,
    "4070 Ti": 5499, "4070 SUPER": 4499, "4070": 3999, "4060 Ti": 2799,
    "4060": 2199, "3090": 7999, "3080": 4999, "3070": 2999, "3060": 1999,
    "7900 XTX": 7999, "7900 XT": 6499, "7800 XT": 3499, "7700 XT": 2999,
    "7600 XT": 2499, "7600": 1999, "6950 XT": 4499, "6800 XT": 3499,
    "6750 XT": 2799, "6700 XT": 2299, "6600 XT": 1699,
    "A770": 1799, "A750": 1299, "A580": 999, "A380": 699,
    "8480": 88000, "8468": 65000, "8380": 52000,
    "6348": 28000, "5318Y": 18000, "6338": 22000,
    "4316": 8500, "4314": 6500, "3204": 3200,
    "W-3375X": 38000, "W-2295": 22000, "E-2388G": 5800, "E-2378G": 4200,
    "9654": 78000, "9554": 55000, "9454": 42000, "9374F": 32000,
    "9354": 26000, "9274F": 18000, "7763": 42000, "7713": 32000,
    "7643": 22000, "7543": 16000, "7413": 12000, "7313P": 8500,
    "A100 80GB": 85000, "A100 40GB": 55000, "A800 80GB": 72000, "A800 40GB": 45000,
    "H100 80GB": 250000, "H800 80GB": 180000, "L40S": 52000, "L40": 38000,
    "A30": 28000, "A10": 15000, "V100 32GB": 32000, "V100 16GB": 18000,
    "T4": 8500, "6000 Ada": 38000, "A6000": 32000,
    "MI300X": 120000, "MI250X": 85000, "MI210": 45000, "MI100": 28000,
    "W7900": 28000, "W6800": 18000,
    "Max 1550": 68000, "Max 1100": 35000, "Flex 170": 15000, "Flex 140": 8500,
}

MEMORY_BASE = {
    "DDR4 3200MHz 16G": 250, "DDR4 3200MHz 32G": 450,
    "DDR5 4800MHz 16G": 300, "DDR5 4800MHz 32G": 550,
    "DDR5 5600MHz 16G": 350, "DDR5 5600MHz 32G": 650,
    "DDR5 6000MHz 16G": 400, "DDR5 6000MHz 32G": 750,
    "DDR4 3200MHz 64G": 900, "DDR5 4800MHz 64G": 1200, "DDR5 5600MHz 64G": 1400,
}

STORAGE_BASE = {
    "M.2 NVMe 512G": 250, "M.2 NVMe 1T": 450,
    "SATA SSD 480G": 350, "SATA SSD 960G": 600,
    "SATA SSD 1.92T": 1100, "SATA SSD 3.84T": 2200, "SATA SSD 7.68T": 4500,
    "U.2 NVMe SSD 480G": 500, "U.2 NVMe SSD 960G": 900,
    "U.2 NVMe SSD 1.92T": 1800, "U.2 NVMe SSD 3.84T": 3500, "U.2 NVMe SSD 7.68T": 7000,
    "M.2 NVMe SSD 480G": 400, "M.2 NVMe SSD 960G": 700,
    "M.2 NVMe SSD 1.92T": 1300, "M.2 NVMe SSD 3.84T": 2500, "M.2 NVMe SSD 7.68T": 5000,
}


def _simulate_price_search(keyword, source):
    price = None
    for key, base in BASE_PRICES.items():
        if key in keyword:
            price = base
            break
    if price is None:
        for key, base in MEMORY_BASE.items():
            if key in keyword:
                price = base
                break
    if price is None:
        for key, base in STORAGE_BASE.items():
            if key in keyword:
                price = base
                break
    if price is None:
        price = random.uniform(100, 5000)
    price = round(price * random.uniform(0.92, 1.08), 2)
    return price


def crawl_part_prices(level, part_type, brand=None, model=None, spec=None):
    results = []
    today = datetime.now().strftime("%Y-%m-%d")
    if part_type == "cpu":
        models_dict = CONSUMER_CPU_MODELS if level == "consumer" else INDUSTRIAL_CPU_MODELS
        brands_to_crawl = [brand] if brand else list(models_dict.keys())
        for b in brands_to_crawl:
            for m in models_dict.get(b, []):
                keyword = b + " " + m
                for src in CRAWL_SOURCES:
                    p = _simulate_price_search(keyword, src["name"])
                    results.append({"category": "parts", "level": level, "part_type": part_type,
                        "brand": b, "model": m, "spec": None, "price": p,
                        "source": src["name"], "source_url": src["base_url"].format(keyword=keyword),
                        "price_date": today})
    elif part_type == "gpu":
        models_dict = CONSUMER_GPU_MODELS if level == "consumer" else INDUSTRIAL_GPU_MODELS
        brands_to_crawl = [brand] if brand else list(models_dict.keys())
        for b in brands_to_crawl:
            for m in models_dict.get(b, []):
                keyword = b + " " + m
                for src in CRAWL_SOURCES:
                    p = _simulate_price_search(keyword, src["name"])
                    results.append({"category": "parts", "level": level, "part_type": part_type,
                        "brand": b, "model": m, "spec": None, "price": p,
                        "source": src["name"], "source_url": src["base_url"].format(keyword=keyword),
                        "price_date": today})
    elif part_type == "memory":
        brands_list = CONSUMER_MEMORY_BRANDS if level == "consumer" else INDUSTRIAL_MEMORY_BRANDS
        specs_list = CONSUMER_MEMORY_SPECS if level == "consumer" else INDUSTRIAL_MEMORY_SPECS
        brands_to_crawl = [brand] if brand else brands_list
        specs_to_crawl = [spec] if spec else specs_list
        for b in brands_to_crawl:
            for s in specs_to_crawl:
                keyword = b + " " + s
                for src in CRAWL_SOURCES:
                    p = _simulate_price_search(keyword, src["name"])
                    results.append({"category": "parts", "level": level, "part_type": part_type,
                        "brand": b, "model": b + " " + s, "spec": s, "price": p,
                        "source": src["name"], "source_url": src["base_url"].format(keyword=keyword),
                        "price_date": today})
    elif part_type == "storage":
        brands_list = CONSUMER_STORAGE_BRANDS if level == "consumer" else INDUSTRIAL_STORAGE_BRANDS
        specs_list = CONSUMER_STORAGE_SPECS if level == "consumer" else INDUSTRIAL_STORAGE_SPECS
        brands_to_crawl = [brand] if brand else brands_list
        specs_to_crawl = [spec] if spec else specs_list
        for b in brands_to_crawl:
            for s in specs_to_crawl:
                keyword = b + " " + s
                for src in CRAWL_SOURCES:
                    p = _simulate_price_search(keyword, src["name"])
                    results.append({"category": "parts", "level": level, "part_type": part_type,
                        "brand": b, "model": b + " " + s, "spec": s, "price": p,
                        "source": src["name"], "source_url": src["base_url"].format(keyword=keyword),
                        "price_date": today})
    return results


def run_crawl_task(level, part_type):
    db = PartsPriceDB()
    task_name = level + "_" + part_type + "_" + datetime.now().strftime("%Y%m%d%H%M")
    task_id = db.create_task(task_name, level, part_type)
    def _run():
        try:
            db.update_task(task_id, status="running")
            results = crawl_part_prices(level, part_type)
            if results:
                db.save_prices(results)
            db.update_task(task_id, status="done", items_count=len(results))
            logger.info("crawl task done: " + task_name + ", got " + str(len(results)) + " items")
        except Exception as e:
            db.update_task(task_id, status="failed")
            logger.exception("crawl task failed: " + task_name)
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return task_id


def run_all_crawl_tasks():
    tasks = []
    for level in ["consumer", "industrial"]:
        for pt in ["cpu", "gpu", "memory", "storage"]:
            tid = run_crawl_task(level, pt)
            tasks.append({"level": level, "part_type": pt, "task_id": tid})
    return tasks
