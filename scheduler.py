from apscheduler.schedulers.blocking import BlockingScheduler
from crawlers import OperatorCrawler, MarketCrawler
from email_sender import EmailSender
from config import Config
from database import Database
from parts_crawler import run_all_crawl_tasks
import logging

class Scheduler:
    def __init__(self, config: Config, operator_crawler: OperatorCrawler,
                 market_crawler: MarketCrawler, email_sender: EmailSender,
                 db: Database = None, schedule_config: dict = None):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.scheduler = BlockingScheduler()
        self.operator_crawler = operator_crawler
        self.market_crawler = market_crawler
        self.email_sender = email_sender
        self.db = db or Database(config.database_path)
        self.schedule_config = schedule_config or {}

    def schedule_jobs(self):
        """设置定时任务，支持自定义配置"""
        cfg = self.schedule_config or {}

        # 运营商任务配置
        op_hour = int(cfg.get('operator_hour', 9))
        op_minute = int(cfg.get('operator_minute', 0))
        op_range = cfg.get('operator_range', 'all')
        op_freq = cfg.get('operator_freq', 'daily')

        # 市场任务配置
        mkt_hour = int(cfg.get('market_hour', 17))
        mkt_minute = int(cfg.get('market_minute', 0))
        mkt_range = cfg.get('market_range', 'all')
        mkt_freq = cfg.get('market_freq', 'daily')

        # 添加运营商定时任务
        if op_range != 'none':
            op_day_of_week = 'mon-fri' if op_freq == 'weekly' else None
            self.scheduler.add_job(
                self.run_operator_job,
                'cron',
                hour=op_hour,
                minute=op_minute,
                day_of_week=op_day_of_week,
                name='operator_report'
            )
            self.logger.info(f"运营商定时任务已设置: {op_hour:02d}:{op_minute:02d}, 频率={op_freq}, 范围={op_range}")

        # 添加市场定时任务
        if mkt_range != 'none':
            mkt_day_of_week = 'mon-fri' if mkt_freq == 'weekly' else None
            self.scheduler.add_job(
                self.run_market_job,
                'cron',
                hour=mkt_hour,
                minute=mkt_minute,
                day_of_week=mkt_day_of_week,
                name='market_report'
            )
            self.logger.info(f"市场定时任务已设置: {mkt_hour:02d}:{mkt_minute:02d}, 频率={mkt_freq}, 范围={mkt_range}")

        # 配件时价定时任务：每天9:00、9:30、10:00 各爬取一次
        self.scheduler.add_job(
            self.run_parts_price_job,
            'cron',
            hour=9,
            minute='0,30,59',
            name='parts_price_crawl'
        )
        self.logger.info("配件时价定时任务已设置: 每天 09:00, 09:30, 09:59")

        self.logger.info("定时任务已启动")
        self.scheduler.start()

    def run_operator_job(self):
        """执行运营商任务"""
        cfg = self.schedule_config or {}
        op_range = cfg.get('operator_range', 'all')
        try:
            data = None
            source_results = []
            if op_range in ('all', 'crawl_only'):
                result = self.operator_crawler.crawl()
                # 兼容crawl返回tuple或单值
                if isinstance(result, tuple):
                    data, source_results = result
                else:
                    data = result
            count = len(data) if data else 0
            if data and op_range in ('all', 'crawl_only'):
                self.db.save_operator_data(data)
                # 保存每个数据源的爬取记录
                for sr in source_results:
                    self.db.save_crawl_log(
                        source_key=sr.get('source_key', ''),
                        source_name=sr.get('source_name', ''),
                        source_url=sr.get('source_url', ''),
                        task_type='operator',
                        status=sr.get('status', 'unknown'),
                        message=sr.get('message', ''),
                        found_count=sr.get('found_count', 0),
                        saved_count=count if sr.get('status') == 'success' else 0
                    )
            if op_range in ('all', 'email_only'):
                if op_range == 'email_only':
                    data = self.db.get_operator_history(limit=50)
                if data:
                    self.email_sender.send_operator_report(data)
            self.db.save_task_log('operator_scheduled', 'success', f'获取到{count}条数据', count)
            self.logger.info(f"运营商定时任务执行成功，获取到{count}条数据")
        except Exception as e:
            self.db.save_task_log('operator_scheduled', 'error', str(e))
            self.logger.error(f"运营商任务执行失败: {str(e)}")

    def run_parts_price_job(self):
        """执行配件时价爬取任务"""
        try:
            tasks = run_all_crawl_tasks()
            total_items = sum(t.get('items_count', 0) for t in tasks)
            self.db.save_task_log('parts_price_scheduled', 'success',
                                  f'配件时价爬取完成，启动{len(tasks)}个任务', len(tasks))
            self.logger.info(f"配件时价定时任务执行成功，启动{len(tasks)}个爬取任务")
        except Exception as e:
            self.db.save_task_log('parts_price_scheduled', 'error', str(e))
            self.logger.error(f"配件时价任务执行失败: {str(e)}")

    def run_market_job(self):
        """执行市场任务"""
        cfg = self.schedule_config or {}
        mkt_range = cfg.get('market_range', 'all')
        try:
            competitors = []
            hardware = []
            comp_sources = []
            hw_sources = []
            if mkt_range in ('all', 'crawl_only'):
                data = self.market_crawler.crawl()
                competitors = data.get('competitors', [])
                hardware = data.get('hardware', [])
                comp_sources = data.get('competitor_sources', [])
                hw_sources = data.get('hardware_sources', [])
            if competitors and mkt_range in ('all', 'crawl_only'):
                self.db.save_competitor_data(competitors)
                for sr in comp_sources:
                    self.db.save_crawl_log(
                        source_key=sr.get('source_key', ''),
                        source_name=sr.get('source_name', ''),
                        source_url=sr.get('source_url', ''),
                        task_type='competitor',
                        status=sr.get('status', 'unknown'),
                        message=sr.get('message', ''),
                        found_count=sr.get('found_count', 0),
                        saved_count=len(competitors) if sr.get('status') == 'success' else 0
                    )
            if hardware and mkt_range in ('all', 'crawl_only'):
                self.db.save_hardware_data(hardware)
                for sr in hw_sources:
                    self.db.save_crawl_log(
                        source_key=sr.get('source_key', ''),
                        source_name=sr.get('source_name', ''),
                        source_url=sr.get('source_url', ''),
                        task_type='hardware',
                        status=sr.get('status', 'unknown'),
                        message=sr.get('message', ''),
                        found_count=sr.get('found_count', 0),
                        saved_count=len(hardware) if sr.get('status') == 'success' else 0
                    )
            if mkt_range in ('all', 'email_only'):
                if mkt_range == 'email_only':
                    competitors = self.db.get_competitor_history(limit=50)
                    hardware = self.db.get_hardware_history(limit=50)
                if competitors or hardware:
                    self.email_sender.send_market_report({'competitors': competitors, 'hardware': hardware})
            total = len(competitors) + len(hardware)
            self.db.save_task_log('market_scheduled', 'success', f'获取到{total}条数据', total)
            self.logger.info(f"市场定时任务执行成功，获取到{total}条数据")
        except Exception as e:
            self.db.save_task_log('market_scheduled', 'error', str(e))
            self.logger.error(f"市场任务执行失败: {str(e)}")

def schedule_jobs(operator_crawler: OperatorCrawler,
                 market_crawler: MarketCrawler,
                 email_sender: EmailSender,
                 db: Database = None,
                 schedule_config: dict = None):
    """外部调用接口"""
    config = Config()
    scheduler = Scheduler(config, operator_crawler, market_crawler, email_sender, db, schedule_config)
    scheduler.schedule_jobs()
