import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Tuple
from config import Config
import logging
import re
from datetime import datetime
from urllib.parse import urljoin, quote_plus
import json
import time

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

def safe_get(url, timeout=15, retries=2):
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            resp.encoding = resp.apparent_encoding or 'utf-8'
            return resp
        except Exception as e:
            logger.warning(f"请求{url}第{attempt+1}次失败: {e}")
    return None


class OperatorCrawler:
    """运营商招标信息爬虫 - 根据配置的渠道动态爬取"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def crawl(self) -> Tuple[List[Dict], List[Dict]]:
        """爬取运营商信息，返回 (数据列表, 各数据源详细结果)"""
        results = []
        source_results = []  # 每个数据源的爬取结果记录
        keywords = list(self.config.operator_keywords)
        sources = self.config.operator_sources

        # 渠道映射：source_key -> (爬取方法, 显示名称)
        source_methods = {
            'bidcenter': (self._crawl_bidcenter, '中国采购与招标网'),
            'ggzy': (self._crawl_ggzy, '全国公共资源交易平台'),
            'rss_bid': (self._crawl_rss_bid, 'RSS聚合招标信息'),
        }

        for source_key, (method, source_name) in source_methods.items():
            source_cfg = sources.get(source_key, {})
            enabled = source_cfg.get('enabled', True) if isinstance(source_cfg, dict) else True
            source_url = source_cfg.get('url', '') if isinstance(source_cfg, dict) else ''

            if not enabled:
                self.logger.info(f"跳过已禁用的渠道: {source_name}")
                source_results.append({
                    'source_key': source_key,
                    'source_name': source_name,
                    'source_url': source_url,
                    'status': 'skipped',
                    'message': '渠道已禁用',
                    'found_count': 0
                })
                continue

            try:
                self.logger.info(f"爬取{source_name}...")
                data = method(keywords)
                results.extend(data)
                self.logger.info(f"{source_name}获取{len(data)}条")
                source_results.append({
                    'source_key': source_key,
                    'source_name': source_name,
                    'source_url': source_url,
                    'status': 'success',
                    'message': f'成功获取{len(data)}条数据',
                    'found_count': len(data)
                })
            except Exception as e:
                self.logger.error(f"{source_name}爬取失败: {e}")
                source_results.append({
                    'source_key': source_key,
                    'source_name': source_name,
                    'source_url': source_url,
                    'status': 'error',
                    'message': str(e),
                    'found_count': 0
                })

        # 处理自定义渠道（不在预定义source_methods中的渠道）
        for source_key, source_cfg in sources.items():
            if source_key in source_methods:
                continue
            if not isinstance(source_cfg, dict):
                continue
            enabled = source_cfg.get('enabled', True)
            source_name = source_cfg.get('name', source_key)
            source_url = source_cfg.get('url', '')
            if not enabled:
                self.logger.info(f"跳过已禁用的自定义渠道: {source_name}")
                source_results.append({
                    'source_key': source_key,
                    'source_name': source_name,
                    'source_url': source_url,
                    'status': 'skipped',
                    'message': '渠道已禁用',
                    'found_count': 0
                })
                continue
            try:
                self.logger.info(f"爬取自定义渠道{source_name}({source_url})...")
                data = self._crawl_generic(source_url, keywords, source_name, 'operator')
                results.extend(data)
                self.logger.info(f"{source_name}获取{len(data)}条")
                source_results.append({
                    'source_key': source_key,
                    'source_name': source_name,
                    'source_url': source_url,
                    'status': 'success',
                    'message': f'成功获取{len(data)}条数据',
                    'found_count': len(data)
                })
            except Exception as e:
                self.logger.error(f"{source_name}爬取失败: {e}")
                source_results.append({
                    'source_key': source_key,
                    'source_name': source_name,
                    'source_url': source_url,
                    'status': 'error',
                    'message': str(e),
                    'found_count': 0
                })

        # 去重
        seen = set()
        unique = []
        for r in results:
            key = r['title'][:50]
            if key not in seen:
                seen.add(key)
                unique.append(r)

        self.logger.info(f"运营商爬取完成，共获取{len(unique)}条去重数据")
        return unique, source_results

    def _crawl_generic(self, url, keywords, source_name, data_type='operator'):
        """通用爬取方法：自动识别RSS/HTML/JSON，支持自定义渠道"""
        if not url:
            return []
        results = []
        try:
            resp = safe_get(url, timeout=12)
            if not resp:
                return []
            content_type = resp.headers.get('Content-Type', '')
            text = resp.text.strip()
            # 判断是否为RSS/XML
            is_rss = ('<rss' in text[:500] or '<feed' in text[:500] or '<channel' in text[:500]
                      or 'xml' in content_type.lower() or url.endswith('.xml') or '/rss' in url.lower() or '/feed' in url.lower())
            # 判断是否为JSON API
            is_json = ('json' in content_type.lower() or url.endswith('.json') or '/api/' in url.lower())
            if is_rss:
                results = self._parse_rss(text, keywords, source_name, data_type, url)
            elif is_json:
                results = self._parse_json(resp, keywords, source_name, data_type, url)
            else:
                results = self._parse_html(text, keywords, source_name, data_type, url)
        except Exception as e:
            self.logger.error(f"通用爬取{source_name}失败: {e}")
        return results[:15]

    def _parse_rss(self, text, keywords, source_name, data_type, base_url):
        """解析RSS/Atom feed"""
        results = []
        try:
            soup = BeautifulSoup(text, 'xml')
            for item in soup.find_all('item')[:30]:
                try:
                    title_tag = item.find('title')
                    link_tag = item.find('link')
                    desc_tag = item.find('description')
                    pub_tag = item.find('pubDate') or item.find('updated')
                    if not title_tag:
                        continue
                    title = title_tag.get_text(strip=True)
                    href = link_tag.get_text(strip=True) if link_tag else '#'
                    desc = desc_tag.get_text(strip=True)[:150] if desc_tag else ''
                    pub_date = pub_tag.get_text(strip=True) if pub_tag else datetime.now().strftime('%Y-%m-%d')
                    if not title or len(title) < 4:
                        continue
                    if data_type == 'operator':
                        matched = self._match_kw(title, keywords)
                        if matched:
                            results.append({'title': title[:200], 'url': href, 'date': pub_date, 'source': source_name, 'summary': desc, 'keyword': matched})
                    elif data_type == 'competitor':
                        matched = self._match_name(title, keywords) if hasattr(self, '_match_name') else None
                        if matched:
                            results.append({'name': matched, 'title': title[:200], 'url': href, 'date': pub_date, 'summary': desc})
                    elif data_type == 'hardware':
                        matched = self._match_hw(title, keywords) if hasattr(self, '_match_hw') else None
                        if matched:
                            trend = self._detect_trend(title) if hasattr(self, '_detect_trend') else '持平'
                            results.append({'name': title[:200], 'category': matched, 'price': '详见链接', 'trend': trend, 'url': href, 'summary': desc})
                except Exception:
                    continue
        except Exception as e:
            self.logger.error(f"RSS解析{source_name}失败: {e}")
        return results

    def _parse_json(self, resp, keywords, source_name, data_type, base_url):
        """解析JSON API响应"""
        results = []
        try:
            data = resp.json()
            items = data if isinstance(data, list) else data.get('data', data.get('items', data.get('articles', data.get('list', []))))
            if not isinstance(items, list):
                items = []
            for item in items[:30]:
                try:
                    title = item.get('title', '') or item.get('article_title', '') or item.get('name', '')
                    href = item.get('url', '') or item.get('link', '') or item.get('article_url', '')
                    desc = item.get('summary', '') or item.get('description', '') or item.get('article_summary', '')
                    pub_date = item.get('date', '') or item.get('publish_time', '') or item.get('created_at', '')
                    if not title or len(title) < 4:
                        continue
                    if not href and item.get('uuid'):
                        href = base_url.rstrip('/') + '/' + item['uuid']
                    if data_type == 'operator':
                        matched = self._match_kw(title, keywords)
                        if matched:
                            results.append({'title': title[:200], 'url': href, 'date': str(pub_date) or datetime.now().strftime('%Y-%m-%d'), 'source': source_name, 'summary': str(desc)[:150], 'keyword': matched})
                    elif data_type == 'competitor':
                        matched = self._match_name(title, keywords) if hasattr(self, '_match_name') else None
                        if matched:
                            results.append({'name': matched, 'title': title[:200], 'url': href, 'date': str(pub_date) or datetime.now().strftime('%Y-%m-%d'), 'summary': str(desc)[:150]})
                    elif data_type == 'hardware':
                        matched = self._match_hw(title, keywords) if hasattr(self, '_match_hw') else None
                        if matched:
                            trend = self._detect_trend(title) if hasattr(self, '_detect_trend') else '持平'
                            results.append({'name': title[:200], 'category': matched, 'price': '详见链接', 'trend': trend, 'url': href, 'summary': str(desc)[:150]})
                except Exception:
                    continue
        except Exception as e:
            self.logger.error(f"JSON解析{source_name}失败: {e}")
        return results

    def _parse_html(self, text, keywords, source_name, data_type, base_url):
        """解析HTML页面，自动提取文章列表"""
        results = []
        try:
            soup = BeautifulSoup(text, 'html.parser')
            # 尝试多种常见的文章列表选择器
            selectors = ['.list-item', '.news-list li', '.article-list li', '.result-list li',
                         '.search-result li', '.news-item', '.item', '.lst li', '.fl li',
                         'article', '.content li', '.post', '.entry', 'ul li']
            items = []
            for sel in selectors:
                found = soup.select(sel)
                if found and len(found) >= 2:
                    items = found[:30]
                    break
            if not items:
                # 兜底：找所有含链接的li
                items = soup.select('li')[:30]
            for item in items:
                try:
                    title_tag = item.select_one('a')
                    if not title_tag:
                        continue
                    title = title_tag.get_text(strip=True)
                    href = title_tag.get('href', '')
                    if not title or len(title) < 6:
                        continue
                    if href and not href.startswith('http'):
                        href = urljoin(base_url, href)
                    desc_tag = item.select_one('p, .desc, .summary, .description')
                    desc = desc_tag.get_text(strip=True)[:150] if desc_tag else ''
                    date_tag = item.select_one('.date, .time, span[class*=date], .pub-time')
                    pub_date = date_tag.get_text(strip=True) if date_tag else datetime.now().strftime('%Y-%m-%d')
                    if data_type == 'operator':
                        matched = self._match_kw(title, keywords)
                        if matched:
                            results.append({'title': title[:200], 'url': href or base_url, 'date': pub_date, 'source': source_name, 'summary': desc or title[:150], 'keyword': matched})
                    elif data_type == 'competitor':
                        matched = self._match_name(title, keywords) if hasattr(self, '_match_name') else None
                        if matched:
                            results.append({'name': matched, 'title': title[:200], 'url': href or base_url, 'date': pub_date, 'summary': desc or title[:150]})
                    elif data_type == 'hardware':
                        matched = self._match_hw(title, keywords) if hasattr(self, '_match_hw') else None
                        if matched:
                            trend = self._detect_trend(title) if hasattr(self, '_detect_trend') else '持平'
                            results.append({'name': title[:200], 'category': matched, 'price': '详见链接', 'trend': trend, 'url': href or base_url, 'summary': desc or title[:150]})
                except Exception:
                    continue
        except Exception as e:
            self.logger.error(f"HTML解析{source_name}失败: {e}")
        return results

    def _match_kw(self, text, keywords):
        for kw in keywords:
            if kw in text:
                return kw
        return None

    def _crawl_bidcenter(self, keywords):
        """爬取中国采购与招标网"""
        results = []
        for kw in keywords[:3]:
            try:
                url = f"https://search.bidcenter.com.cn/search?keywords={quote_plus(kw)}"
                resp = safe_get(url, timeout=12)
                if not resp:
                    continue
                soup = BeautifulSoup(resp.text, 'html.parser')
                for item in soup.select('.list-item, .result-list li, .search-result li, .news-list li'):
                    try:
                        title_tag = item.select_one('a')
                        if not title_tag:
                            continue
                        title = title_tag.get_text(strip=True)
                        href = title_tag.get('href', '')
                        if not title or len(title) < 6:
                            continue
                        matched = self._match_kw(title, keywords)
                        if matched:
                            date_tag = item.select_one('.date, .time, span[class*=date], .pub-time')
                            date = date_tag.get_text(strip=True) if date_tag else datetime.now().strftime('%Y-%m-%d')
                            results.append({
                                'title': title[:200],
                                'url': urljoin(url, href) if href else url,
                                'date': date,
                                'source': '中国采购与招标网',
                                'summary': title[:150],
                                'keyword': matched
                            })
                    except Exception:
                        continue
                if len(results) >= 10:
                    break
            except Exception as e:
                self.logger.error(f"中国采购与招标网搜索{kw}失败: {e}")
        return results[:10]

    def _crawl_ggzy(self, keywords):
        """爬取全国公共资源交易平台"""
        results = []
        for kw in keywords[:2]:
            try:
                url = f"https://ggzy.gov.cn/searchByType/index.html?type=1&searchText={quote_plus(kw)}"
                resp = safe_get(url, timeout=12)
                if not resp:
                    continue
                soup = BeautifulSoup(resp.text, 'html.parser')
                for item in soup.select('.list li, .news-list li, .result-item'):
                    try:
                        title_tag = item.select_one('a')
                        if not title_tag:
                            continue
                        title = title_tag.get_text(strip=True)
                        href = title_tag.get('href', '')
                        if not title or len(title) < 6:
                            continue
                        matched = self._match_kw(title, keywords)
                        if matched:
                            date_tag = item.select_one('.date, .time')
                            date = date_tag.get_text(strip=True) if date_tag else datetime.now().strftime('%Y-%m-%d')
                            results.append({
                                'title': title[:200],
                                'url': urljoin(url, href) if href else url,
                                'date': date,
                                'source': '全国公共资源交易平台',
                                'summary': title[:150],
                                'keyword': matched
                            })
                    except Exception:
                        continue
                if len(results) >= 8:
                    break
            except Exception as e:
                self.logger.error(f"全国公共资源交易平台搜索{kw}失败: {e}")
        return results[:8]

    def _crawl_rss_bid(self, keywords):
        """通过RSS聚合源获取招标信息"""
        results = []
        rss_sources = [
            'https://www.chinabidding.cn/rss/bid.xml',
            'https://feedx.net/rss/chinabidding.xml',
        ]
        for rss_url in rss_sources:
            try:
                resp = safe_get(rss_url, timeout=10)
                if not resp:
                    continue
                soup = BeautifulSoup(resp.text, 'xml')
                for item in soup.find_all('item')[:15]:
                    try:
                        title_tag = item.find('title')
                        link_tag = item.find('link')
                        desc_tag = item.find('description')
                        pub_tag = item.find('pubDate')
                        if not title_tag:
                            continue
                        title = title_tag.get_text(strip=True)
                        href = link_tag.get_text(strip=True) if link_tag else '#'
                        desc = desc_tag.get_text(strip=True)[:150] if desc_tag else ''
                        pub_date = pub_tag.get_text(strip=True) if pub_tag else datetime.now().strftime('%Y-%m-%d')
                        matched = self._match_kw(title, keywords)
                        if matched:
                            results.append({
                                'title': title[:200],
                                'url': href,
                                'date': pub_date,
                                'source': '招标RSS聚合',
                                'summary': desc,
                                'keyword': matched
                            })
                    except Exception:
                        continue
            except Exception as e:
                self.logger.error(f"RSS源{rss_url}爬取失败: {e}")
        return results[:10]


class MarketCrawler:
    """市场信息爬虫 - 根据配置的渠道动态爬取"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def crawl(self) -> Dict:
        """返回 {competitors: [...], hardware: [...], competitor_sources: [...], hardware_sources: [...]}"""
        competitors, comp_sources = self.crawl_competitors()
        hardware, hw_sources = self.crawl_hardware()
        return {
            "competitors": competitors,
            "hardware": hardware,
            "competitor_sources": comp_sources,
            "hardware_sources": hw_sources
        }

    def crawl_competitors(self) -> Tuple[List[Dict], List[Dict]]:
        """爬取友商动态，返回 (数据列表, 各数据源详细结果)"""
        results = []
        source_results = []
        competitors = list(self.config.competitors)
        sources = self.config.competitor_sources

        # 渠道映射
        source_methods = {
            '36kr': (self._crawl_36kr, '36氪'),
            'ithome': (self._crawl_ithome, 'IT之家'),
            'tmtpost': (self._crawl_tmtpost, '钛媒体'),
            'leiphone': (self._crawl_leiphone, '雷锋网'),
            'oschina': (self._crawl_oschina, '开源中国'),
            'infoq': (self._crawl_infoq, 'InfoQ中文'),
        }

        for source_key, (method, source_name) in source_methods.items():
            source_cfg = sources.get(source_key, {})
            enabled = source_cfg.get('enabled', True) if isinstance(source_cfg, dict) else True
            source_url = source_cfg.get('url', '') if isinstance(source_cfg, dict) else ''

            if not enabled:
                self.logger.info(f"跳过已禁用的渠道: {source_name}")
                source_results.append({
                    'source_key': source_key,
                    'source_name': source_name,
                    'source_url': source_url,
                    'status': 'skipped',
                    'message': '渠道已禁用',
                    'found_count': 0
                })
                continue

            try:
                self.logger.info(f"爬取{source_name}...")
                data = method(competitors)
                results.extend(data)
                self.logger.info(f"{source_name}获取{len(data)}条")
                source_results.append({
                    'source_key': source_key,
                    'source_name': source_name,
                    'source_url': source_url,
                    'status': 'success',
                    'message': f'成功获取{len(data)}条数据',
                    'found_count': len(data)
                })
            except Exception as e:
                self.logger.error(f"{source_name}爬取失败: {e}")
                source_results.append({
                    'source_key': source_key,
                    'source_name': source_name,
                    'source_url': source_url,
                    'status': 'error',
                    'message': str(e),
                    'found_count': 0
                })

        # 处理自定义渠道
        for source_key, source_cfg in sources.items():
            if source_key in source_methods:
                continue
            if not isinstance(source_cfg, dict):
                continue
            enabled = source_cfg.get('enabled', True)
            source_name = source_cfg.get('name', source_key)
            source_url = source_cfg.get('url', '')
            if not enabled:
                source_results.append({'source_key': source_key, 'source_name': source_name, 'source_url': source_url, 'status': 'skipped', 'message': '渠道已禁用', 'found_count': 0})
                continue
            try:
                self.logger.info(f"爬取自定义友商渠道{source_name}({source_url})...")
                data = self._crawl_generic(source_url, competitors, source_name, 'competitor')
                results.extend(data)
                source_results.append({'source_key': source_key, 'source_name': source_name, 'source_url': source_url, 'status': 'success', 'message': f'成功获取{len(data)}条数据', 'found_count': len(data)})
            except Exception as e:
                self.logger.error(f"{source_name}爬取失败: {e}")
                source_results.append({'source_key': source_key, 'source_name': source_name, 'source_url': source_url, 'status': 'error', 'message': str(e), 'found_count': 0})

        # 去重
        seen = set()
        unique = []
        for r in results:
            key = r['title'][:50]
            if key not in seen:
                seen.add(key)
                unique.append(r)

        self.logger.info(f"友商动态爬取完成，共获取{len(unique)}条去重数据")
        return unique, source_results

    def _crawl_generic(self, url, keywords, source_name, data_type='competitor'):
        """通用爬取方法：自动识别RSS/HTML/JSON"""
        if not url:
            return []
        results = []
        try:
            resp = safe_get(url, timeout=12)
            if not resp:
                return []
            content_type = resp.headers.get('Content-Type', '')
            text = resp.text.strip()
            is_rss = ('<rss' in text[:500] or '<feed' in text[:500] or '<channel' in text[:500]
                      or 'xml' in content_type.lower() or url.endswith('.xml') or '/rss' in url.lower() or '/feed' in url.lower())
            is_json = ('json' in content_type.lower() or url.endswith('.json') or '/api/' in url.lower())
            if is_rss:
                results = self._parse_rss(text, keywords, source_name, data_type, url)
            elif is_json:
                results = self._parse_json(resp, keywords, source_name, data_type, url)
            else:
                results = self._parse_html(text, keywords, source_name, data_type, url)
        except Exception as e:
            self.logger.error(f"通用爬取{source_name}失败: {e}")
        return results[:15]

    def _parse_rss(self, text, keywords, source_name, data_type, base_url):
        results = []
        try:
            soup = BeautifulSoup(text, 'xml')
            for item in soup.find_all('item')[:30]:
                try:
                    title_tag = item.find('title')
                    link_tag = item.find('link')
                    desc_tag = item.find('description')
                    pub_tag = item.find('pubDate') or item.find('updated')
                    if not title_tag: continue
                    title = title_tag.get_text(strip=True)
                    href = link_tag.get_text(strip=True) if link_tag else '#'
                    desc = desc_tag.get_text(strip=True)[:150] if desc_tag else ''
                    pub_date = pub_tag.get_text(strip=True) if pub_tag else datetime.now().strftime('%Y-%m-%d')
                    if not title or len(title) < 4: continue
                    if data_type == 'competitor':
                        matched = self._match_name(title, keywords)
                        if matched:
                            results.append({'name': matched, 'title': title[:200], 'url': href, 'date': pub_date, 'summary': desc})
                    elif data_type == 'hardware':
                        matched = self._match_hw(title, keywords)
                        if matched:
                            trend = self._detect_trend(title)
                            results.append({'name': title[:200], 'category': matched, 'price': '详见链接', 'trend': trend, 'url': href, 'summary': desc})
                except Exception: continue
        except Exception as e:
            self.logger.error(f"RSS解析{source_name}失败: {e}")
        return results

    def _parse_json(self, resp, keywords, source_name, data_type, base_url):
        results = []
        try:
            data = resp.json()
            items = data if isinstance(data, list) else data.get('data', data.get('items', data.get('articles', data.get('list', []))))
            if not isinstance(items, list): items = []
            for item in items[:30]:
                try:
                    title = item.get('title', '') or item.get('article_title', '') or item.get('name', '')
                    href = item.get('url', '') or item.get('link', '') or item.get('article_url', '')
                    desc = item.get('summary', '') or item.get('description', '') or item.get('article_summary', '')
                    pub_date = item.get('date', '') or item.get('publish_time', '') or item.get('created_at', '')
                    if not title or len(title) < 4: continue
                    if not href and item.get('uuid'): href = base_url.rstrip('/') + '/' + item['uuid']
                    if data_type == 'competitor':
                        matched = self._match_name(title, keywords)
                        if matched:
                            results.append({'name': matched, 'title': title[:200], 'url': href, 'date': str(pub_date) or datetime.now().strftime('%Y-%m-%d'), 'summary': str(desc)[:150]})
                    elif data_type == 'hardware':
                        matched = self._match_hw(title, keywords)
                        if matched:
                            trend = self._detect_trend(title)
                            results.append({'name': title[:200], 'category': matched, 'price': '详见链接', 'trend': trend, 'url': href, 'summary': str(desc)[:150]})
                except Exception: continue
        except Exception as e:
            self.logger.error(f"JSON解析{source_name}失败: {e}")
        return results

    def _parse_html(self, text, keywords, source_name, data_type, base_url):
        results = []
        try:
            soup = BeautifulSoup(text, 'html.parser')
            selectors = ['.list-item', '.news-list li', '.article-list li', '.result-list li',
                         '.search-result li', '.news-item', '.item', '.lst li', '.fl li',
                         'article', '.content li', '.post', '.entry', 'ul li']
            items = []
            for sel in selectors:
                found = soup.select(sel)
                if found and len(found) >= 2:
                    items = found[:30]
                    break
            if not items: items = soup.select('li')[:30]
            for item in items:
                try:
                    title_tag = item.select_one('a')
                    if not title_tag: continue
                    title = title_tag.get_text(strip=True)
                    href = title_tag.get('href', '')
                    if not title or len(title) < 6: continue
                    if href and not href.startswith('http'): href = urljoin(base_url, href)
                    desc_tag = item.select_one('p, .desc, .summary, .description')
                    desc = desc_tag.get_text(strip=True)[:150] if desc_tag else ''
                    date_tag = item.select_one('.date, .time, span[class*=date], .pub-time')
                    pub_date = date_tag.get_text(strip=True) if date_tag else datetime.now().strftime('%Y-%m-%d')
                    if data_type == 'competitor':
                        matched = self._match_name(title, keywords)
                        if matched:
                            results.append({'name': matched, 'title': title[:200], 'url': href or base_url, 'date': pub_date, 'summary': desc or title[:150]})
                    elif data_type == 'hardware':
                        matched = self._match_hw(title, keywords)
                        if matched:
                            trend = self._detect_trend(title)
                            results.append({'name': title[:200], 'category': matched, 'price': '详见链接', 'trend': trend, 'url': href or base_url, 'summary': desc or title[:150]})
                except Exception: continue
        except Exception as e:
            self.logger.error(f"HTML解析{source_name}失败: {e}")
        return results

    def _match_name(self, text, competitors):
        for name in competitors:
            if name in text:
                return name
        return None

    def _crawl_36kr(self, competitors):
        """爬取36氪"""
        results = []
        for name in competitors[:5]:
            try:
                url = f"https://36kr.com/search/articles/{quote_plus(name)}"
                resp = safe_get(url, timeout=12)
                if not resp:
                    continue
                soup = BeautifulSoup(resp.text, 'html.parser')
                for item in soup.select('.article-item, .search-result-item, .kr-flow-article-item'):
                    try:
                        title_tag = item.select_one('a[class*=title], .article-item-title a, a')
                        if not title_tag:
                            continue
                        title = title_tag.get_text(strip=True)
                        href = title_tag.get('href', '')
                        if not title or len(title) < 6:
                            continue
                        matched = self._match_name(title, competitors)
                        if matched:
                            desc_tag = item.select_one('.article-item-description, p')
                            desc = desc_tag.get_text(strip=True)[:150] if desc_tag else ''
                            date_tag = item.select_one('.time, .date')
                            date = date_tag.get_text(strip=True) if date_tag else datetime.now().strftime('%Y-%m-%d')
                            results.append({
                                'name': matched,
                                'title': title[:200],
                                'url': urljoin(url, href) if href else url,
                                'date': date,
                                'summary': desc
                            })
                    except Exception:
                        continue
                if len(results) >= 8:
                    break
            except Exception as e:
                self.logger.error(f"36氪搜索{name}失败: {e}")
        return results[:8]

    def _crawl_ithome(self, competitors):
        """爬取IT之家"""
        results = []
        try:
            resp = safe_get('https://www.ithome.com/rss/', timeout=10)
            if resp:
                soup = BeautifulSoup(resp.text, 'xml')
                for item in soup.find_all('item')[:30]:
                    try:
                        title_tag = item.find('title')
                        link_tag = item.find('link')
                        desc_tag = item.find('description')
                        pub_tag = item.find('pubDate')
                        if not title_tag:
                            continue
                        title = title_tag.get_text(strip=True)
                        href = link_tag.get_text(strip=True) if link_tag else '#'
                        desc = desc_tag.get_text(strip=True)[:150] if desc_tag else ''
                        pub_date = pub_tag.get_text(strip=True) if pub_tag else datetime.now().strftime('%Y-%m-%d')
                        matched = self._match_name(title, competitors)
                        if matched:
                            results.append({
                                'name': matched,
                                'title': title[:200],
                                'url': href,
                                'date': pub_date,
                                'summary': desc
                            })
                    except Exception:
                        continue
        except Exception as e:
            self.logger.error(f"IT之家RSS爬取失败: {e}")

        try:
            resp = safe_get('https://www.ithome.com/tag/ai/', timeout=10)
            if resp:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for item in soup.select('.lst li, .news-list li, .fl li')[:15]:
                    try:
                        title_tag = item.select_one('a')
                        if not title_tag:
                            continue
                        title = title_tag.get_text(strip=True)
                        href = title_tag.get('href', '')
                        if not title or len(title) < 6:
                            continue
                        matched = self._match_name(title, competitors)
                        if matched:
                            results.append({
                                'name': matched,
                                'title': title[:200],
                                'url': urljoin('https://www.ithome.com', href) if href else '#',
                                'date': datetime.now().strftime('%Y-%m-%d'),
                                'summary': title[:150]
                            })
                    except Exception:
                        continue
        except Exception as e:
            self.logger.error(f"IT之家板块爬取失败: {e}")
        return results[:10]

    def _crawl_tmtpost(self, competitors):
        """爬取钛媒体"""
        results = []
        for name in competitors[:3]:
            try:
                url = f"https://www.tmtpost.com/search?q={quote_plus(name)}"
                resp = safe_get(url, timeout=12)
                if not resp:
                    continue
                soup = BeautifulSoup(resp.text, 'html.parser')
                for item in soup.select('.article-item, .search-result-item, .item'):
                    try:
                        title_tag = item.select_one('a')
                        if not title_tag:
                            continue
                        title = title_tag.get_text(strip=True)
                        href = title_tag.get('href', '')
                        if not title or len(title) < 6:
                            continue
                        matched = self._match_name(title, competitors)
                        if matched:
                            desc_tag = item.select_one('p, .desc')
                            desc = desc_tag.get_text(strip=True)[:150] if desc_tag else ''
                            date_tag = item.select_one('.time, .date')
                            date = date_tag.get_text(strip=True) if date_tag else datetime.now().strftime('%Y-%m-%d')
                            results.append({
                                'name': matched,
                                'title': title[:200],
                                'url': urljoin(url, href) if href else url,
                                'date': date,
                                'summary': desc
                            })
                    except Exception:
                        continue
                if len(results) >= 6:
                    break
            except Exception as e:
                self.logger.error(f"钛媒体搜索{name}失败: {e}")
        return results[:6]

    def _crawl_leiphone(self, competitors):
        """爬取雷锋网"""
        results = []
        try:
            resp = safe_get('https://www.leiphone.com/feed', timeout=10)
            if resp:
                soup = BeautifulSoup(resp.text, 'xml')
                for item in soup.find_all('item')[:20]:
                    try:
                        title_tag = item.find('title')
                        link_tag = item.find('link')
                        desc_tag = item.find('description')
                        pub_tag = item.find('pubDate')
                        if not title_tag:
                            continue
                        title = title_tag.get_text(strip=True)
                        href = link_tag.get_text(strip=True) if link_tag else '#'
                        desc = desc_tag.get_text(strip=True)[:150] if desc_tag else ''
                        pub_date = pub_tag.get_text(strip=True) if pub_tag else datetime.now().strftime('%Y-%m-%d')
                        matched = self._match_name(title, competitors)
                        if matched:
                            results.append({
                                'name': matched,
                                'title': title[:200],
                                'url': href,
                                'date': pub_date,
                                'summary': desc
                            })
                    except Exception:
                        continue
        except Exception as e:
            self.logger.error(f"雷锋网RSS爬取失败: {e}")
        return results[:6]

    def _crawl_oschina(self, competitors):
        """爬取开源中国"""
        results = []
        try:
            resp = safe_get('https://www.oschina.net/news/rss', timeout=10)
            if resp:
                soup = BeautifulSoup(resp.text, 'xml')
                for item in soup.find_all('item')[:30]:
                    try:
                        title_tag = item.find('title')
                        link_tag = item.find('link')
                        desc_tag = item.find('description')
                        pub_tag = item.find('pubDate')
                        if not title_tag:
                            continue
                        title = title_tag.get_text(strip=True)
                        href = link_tag.get_text(strip=True) if link_tag else '#'
                        desc = desc_tag.get_text(strip=True)[:150] if desc_tag else ''
                        pub_date = pub_tag.get_text(strip=True) if pub_tag else datetime.now().strftime('%Y-%m-%d')
                        matched = self._match_name(title, competitors)
                        if matched:
                            results.append({
                                'name': matched,
                                'title': title[:200],
                                'url': href,
                                'date': pub_date,
                                'summary': desc
                            })
                    except Exception:
                        continue
        except Exception as e:
            self.logger.error(f"开源中国RSS爬取失败: {e}")
        return results[:8]

    def _crawl_infoq(self, competitors):
        """爬取InfoQ中文"""
        results = []
        try:
            resp = safe_get('https://www.infoq.cn/public/v1/article/list', timeout=10)
            if resp:
                try:
                    data = resp.json()
                    articles = data.get('data', [])
                    for article in articles[:20]:
                        title = article.get('article_title', '')
                        uuid = article.get('uuid', '')
                        desc = article.get('article_summary', '')[:150]
                        pub_date = article.get('publish_time', '')
                        if not title:
                            continue
                        matched = self._match_name(title, competitors)
                        if matched:
                            results.append({
                                'name': matched,
                                'title': title[:200],
                                'url': f'https://www.infoq.cn/article/{uuid}',
                                'date': pub_date if pub_date else datetime.now().strftime('%Y-%m-%d'),
                                'summary': desc
                            })
                except Exception:
                    pass
        except Exception as e:
            self.logger.error(f"InfoQ中文爬取失败: {e}")
        return results[:8]

    def crawl_hardware(self) -> Tuple[List[Dict], List[Dict]]:
        """爬取硬件市场动态，返回 (数据列表, 各数据源详细结果)"""
        results = []
        source_results = []
        hw_keywords = list(self.config.hardware_keywords)
        sources = self.config.hardware_sources

        # 渠道映射
        source_methods = {
            'zol': (self._crawl_zol, '中关村在线'),
            'pconline': (self._crawl_pconline, '太平洋电脑网'),
            'mydrivers': (self._crawl_mydrivers, '快科技'),
            'ithome_hw': (self._crawl_ithome_hw, 'IT之家硬件'),
        }

        for source_key, (method, source_name) in source_methods.items():
            source_cfg = sources.get(source_key, {})
            enabled = source_cfg.get('enabled', True) if isinstance(source_cfg, dict) else True
            source_url = source_cfg.get('url', '') if isinstance(source_cfg, dict) else ''

            if not enabled:
                self.logger.info(f"跳过已禁用的渠道: {source_name}")
                source_results.append({
                    'source_key': source_key,
                    'source_name': source_name,
                    'source_url': source_url,
                    'status': 'skipped',
                    'message': '渠道已禁用',
                    'found_count': 0
                })
                continue

            try:
                self.logger.info(f"爬取{source_name}...")
                data = method(hw_keywords)
                results.extend(data)
                self.logger.info(f"{source_name}获取{len(data)}条")
                source_results.append({
                    'source_key': source_key,
                    'source_name': source_name,
                    'source_url': source_url,
                    'status': 'success',
                    'message': f'成功获取{len(data)}条数据',
                    'found_count': len(data)
                })
            except Exception as e:
                self.logger.error(f"{source_name}爬取失败: {e}")
                source_results.append({
                    'source_key': source_key,
                    'source_name': source_name,
                    'source_url': source_url,
                    'status': 'error',
                    'message': str(e),
                    'found_count': 0
                })

        # 处理自定义渠道
        for source_key, source_cfg in sources.items():
            if source_key in source_methods:
                continue
            if not isinstance(source_cfg, dict):
                continue
            enabled = source_cfg.get('enabled', True)
            source_name = source_cfg.get('name', source_key)
            source_url = source_cfg.get('url', '')
            if not enabled:
                source_results.append({'source_key': source_key, 'source_name': source_name, 'source_url': source_url, 'status': 'skipped', 'message': '渠道已禁用', 'found_count': 0})
                continue
            try:
                self.logger.info(f"爬取自定义硬件渠道{source_name}({source_url})...")
                data = self._crawl_generic(source_url, hw_keywords, source_name, 'hardware')
                results.extend(data)
                source_results.append({'source_key': source_key, 'source_name': source_name, 'source_url': source_url, 'status': 'success', 'message': f'成功获取{len(data)}条数据', 'found_count': len(data)})
            except Exception as e:
                self.logger.error(f"{source_name}爬取失败: {e}")
                source_results.append({'source_key': source_key, 'source_name': source_name, 'source_url': source_url, 'status': 'error', 'message': str(e), 'found_count': 0})

        # 去重
        seen = set()
        unique = []
        for r in results:
            key = r['name'][:50]
            if key not in seen:
                seen.add(key)
                unique.append(r)

        self.logger.info(f"硬件市场爬取完成，共获取{len(unique)}条去重数据")
        return unique, source_results

    def _match_hw(self, text, keywords):
        for kw in keywords:
            if kw.upper() in text.upper() or kw in text:
                return kw
        return None

    def _detect_trend(self, title):
        """从标题检测价格趋势"""
        if any(w in title for w in ['涨价', '上涨', '上调', '攀升', '新高']):
            return '上涨'
        elif any(w in title for w in ['降价', '下跌', '下调', '暴跌', '新低', '破发']):
            return '下降'
        return '持平'

    def _crawl_zol(self, keywords):
        """爬取中关村在线"""
        results = []
        try:
            resp = safe_get('https://rss.zol.com.cn/news.xml', timeout=10)
            if resp:
                soup = BeautifulSoup(resp.text, 'xml')
                for item in soup.find_all('item')[:25]:
                    try:
                        title_tag = item.find('title')
                        link_tag = item.find('link')
                        desc_tag = item.find('description')
                        pub_tag = item.find('pubDate')
                        if not title_tag:
                            continue
                        title = title_tag.get_text(strip=True)
                        href = link_tag.get_text(strip=True) if link_tag else '#'
                        desc = desc_tag.get_text(strip=True)[:150] if desc_tag else ''
                        pub_date = pub_tag.get_text(strip=True) if pub_tag else datetime.now().strftime('%Y-%m-%d')
                        matched = self._match_hw(title, keywords)
                        if matched:
                            trend = self._detect_trend(title)
                            results.append({
                                'name': title[:200],
                                'category': matched,
                                'price': '详见链接',
                                'trend': trend,
                                'url': href,
                                'summary': desc
                            })
                    except Exception:
                        continue
        except Exception as e:
            self.logger.error(f"中关村在线RSS爬取失败: {e}")

        try:
            resp = safe_get('https://diy.zol.com.cn/', timeout=10)
            if resp:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for item in soup.select('.news-list li, .article-list li, .list-item')[:15]:
                    try:
                        title_tag = item.select_one('a')
                        if not title_tag:
                            continue
                        title = title_tag.get_text(strip=True)
                        href = title_tag.get('href', '')
                        if not title or len(title) < 6:
                            continue
                        matched = self._match_hw(title, keywords)
                        if matched:
                            trend = self._detect_trend(title)
                            results.append({
                                'name': title[:200],
                                'category': matched,
                                'price': '详见链接',
                                'trend': trend,
                                'url': urljoin('https://diy.zol.com.cn/', href) if href else '#',
                                'summary': title[:150]
                            })
                    except Exception:
                        continue
        except Exception as e:
            self.logger.error(f"中关村在线硬件频道爬取失败: {e}")
        return results[:10]

    def _crawl_pconline(self, keywords):
        """爬取太平洋电脑网"""
        results = []
        try:
            resp = safe_get('https://diy.pconline.com.cn/', timeout=10)
            if resp:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for item in soup.select('.article-list li, .news-item, .item')[:15]:
                    try:
                        title_tag = item.select_one('a')
                        if not title_tag:
                            continue
                        title = title_tag.get_text(strip=True)
                        href = title_tag.get('href', '')
                        if not title or len(title) < 6:
                            continue
                        matched = self._match_hw(title, keywords)
                        if matched:
                            trend = self._detect_trend(title)
                            results.append({
                                'name': title[:200],
                                'category': matched,
                                'price': '详见链接',
                                'trend': trend,
                                'url': urljoin('https://diy.pconline.com.cn/', href) if href else '#',
                                'summary': title[:150]
                            })
                    except Exception:
                        continue
        except Exception as e:
            self.logger.error(f"太平洋电脑网爬取失败: {e}")
        return results[:8]

    def _crawl_mydrivers(self, keywords):
        """爬取快科技(驱动之家)"""
        results = []
        try:
            resp = safe_get('https://www.mydrivers.com/', timeout=10)
            if resp:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for item in soup.select('.newslist li, .news-item, .item')[:20]:
                    try:
                        title_tag = item.select_one('a')
                        if not title_tag:
                            continue
                        title = title_tag.get_text(strip=True)
                        href = title_tag.get('href', '')
                        if not title or len(title) < 6:
                            continue
                        matched = self._match_hw(title, keywords)
                        if matched:
                            trend = self._detect_trend(title)
                            results.append({
                                'name': title[:200],
                                'category': matched,
                                'price': '详见链接',
                                'trend': trend,
                                'url': href if href.startswith('http') else urljoin('https://www.mydrivers.com/', href),
                                'summary': title[:150]
                            })
                    except Exception:
                        continue
        except Exception as e:
            self.logger.error(f"快科技爬取失败: {e}")
        return results[:8]

    def _crawl_ithome_hw(self, keywords):
        """爬取IT之家硬件板块"""
        results = []
        try:
            resp = safe_get('https://www.ithome.com/rss/', timeout=10)
            if resp:
                soup = BeautifulSoup(resp.text, 'xml')
                for item in soup.find_all('item')[:30]:
                    try:
                        title_tag = item.find('title')
                        link_tag = item.find('link')
                        desc_tag = item.find('description')
                        pub_tag = item.find('pubDate')
                        if not title_tag:
                            continue
                        title = title_tag.get_text(strip=True)
                        href = link_tag.get_text(strip=True) if link_tag else '#'
                        desc = desc_tag.get_text(strip=True)[:150] if desc_tag else ''
                        matched = self._match_hw(title, keywords)
                        if matched:
                            trend = self._detect_trend(title)
                            results.append({
                                'name': title[:200],
                                'category': matched,
                                'price': '详见链接',
                                'trend': trend,
                                'url': href,
                                'summary': desc
                            })
                    except Exception:
                        continue
        except Exception as e:
            self.logger.error(f"IT之家硬件RSS爬取失败: {e}")
        return results[:8]
