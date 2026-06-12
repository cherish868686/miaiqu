# -*- coding: utf-8 -*-
"""
AI服务模块 - 集成妙趣AI本的AI对话、文档生成、联网搜索等能力
使用融合API调用多种大模型
"""
import json
import os
import requests
import logging
import re
import time

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AI_CONFIG_PATH = os.path.join(BASE_DIR, 'ai_config.json')

# 融合API默认配置
DEFAULT_FUSION_BASE_URL = 'http://69.5.17.203:7820/v1'
DEFAULT_FUSION_KEY = 'sk-EMUuNRz5iqyEhj1EyU5mSDjpfb6QjGmOfajUYv3shcn8QljU'

# 各provider的独立API配置（base_url和默认api_key）
PROVIDER_API_CONFIG = {
    'fusion': {
        'name': '融合通道',
        'base_url': 'http://69.5.17.203:7820/v1',
        'default_key': 'sk-EMUuNRz5iqyEhj1EyU5mSDjpfb6QjGmOfajUYv3shcn8QljU',
        'key_label': '融合API Key',
        'key_placeholder': '输入融合API的Key',
    },
    'deepseek': {
        'name': 'DeepSeek',
        'base_url': 'https://api.deepseek.com/v1',
        'default_key': '',
        'key_label': 'DeepSeek API Key',
        'key_placeholder': '输入DeepSeek API Key',
    },
    'qwen': {
        'name': '通义千问',
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'default_key': '',
        'key_label': '通义千问 API Key',
        'key_placeholder': '输入DashScope API Key',
    },
    'zhipu': {
        'name': '智谱GLM',
        'base_url': 'https://open.bigmodel.cn/api/paas/v4',
        'default_key': '',
        'key_label': '智谱 API Key',
        'key_placeholder': '输入智谱API Key',
    },
    'kimi': {
        'name': 'Kimi',
        'base_url': 'https://api.moonshot.cn/v1',
        'default_key': '',
        'key_label': 'Moonshot API Key',
        'key_placeholder': '输入Moonshot API Key',
    },
    'doubao': {
        'name': '豆包',
        'base_url': 'https://ark.cn-beijing.volces.com/api/v3',
        'default_key': '',
        'key_label': '火山引擎 API Key',
        'key_placeholder': '输入火山引擎API Key',
    },
    'openai': {
        'name': 'OpenAI',
        'base_url': 'https://api.openai.com/v1',
        'default_key': '',
        'key_label': 'OpenAI API Key',
        'key_placeholder': '输入OpenAI API Key (sk-...)',
    },
    'ernie': {
        'name': '文心一言',
        'base_url': 'https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop',
        'default_key': '',
        'key_label': '百度千帆 API Key',
        'key_placeholder': '输入百度千帆API Key',
    },
}

# AI模型配置
AI_MODELS = {
    'fusion': {'name': '融合大模型', 'model': 'deepseek-chat', 'models': ['deepseek-chat', 'deepseek-reasoner', 'gpt-4o', 'gpt-4o-mini', 'doubao-pro-32k', 'moonshot-v1-8k']},
    'deepseek': {'name': 'DeepSeek', 'model': 'deepseek-v3', 'models': ['deepseek-v3', 'deepseek-chat', 'deepseek-reasoner']},
    'qwen': {'name': '通义千问', 'model': 'qwen-max', 'models': ['qwen-turbo', 'qwen-plus', 'qwen-max']},
    'zhipu': {'name': '智谱GLM', 'model': 'glm-4', 'models': ['glm-4', 'glm-4-flash', 'glm-4-plus']},
    'kimi': {'name': 'Kimi', 'model': 'moonshot-v1-128k', 'models': ['moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k']},
    'doubao': {'name': '豆包', 'model': 'doubao-pro-128k', 'models': ['doubao-pro-32k', 'doubao-pro-128k']},
    'openai': {'name': 'OpenAI', 'model': 'gpt-4o', 'models': ['gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo']},
    'ernie': {'name': '文心一言', 'model': 'ernie-4.0', 'models': ['ernie-4.0', 'ernie-3.5']},
}

FALLBACK_MODELS = ['deepseek-chat', 'deepseek-v3', 'doubao-pro-32k', 'moonshot-v1-8k', 'gpt-4o-mini']


def _get_provider_credentials(provider):
    """获取provider的API凭据（优先从ai_config.json读取，其次用默认值）"""
    config = load_ai_config()
    providers_cfg = config.get('providers', {})
    provider_cfg = providers_cfg.get(provider, {})
    api_config = PROVIDER_API_CONFIG.get(provider, PROVIDER_API_CONFIG['fusion'])
    base_url = provider_cfg.get('base_url') or api_config['base_url']
    api_key = provider_cfg.get('api_key') or api_config.get('default_key', '')
    return base_url, api_key


def load_ai_config():
    """加载AI配置"""
    try:
        if os.path.exists(AI_CONFIG_PATH):
            with open(AI_CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"加载AI配置失败: {e}")
    return {'currentProvider': 'fusion', 'currentModel': 'deepseek-chat', 'providers': {}}


def save_ai_config(config):
    """保存AI配置"""
    try:
        with open(AI_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存AI配置失败: {e}")
        return False


def call_ai_model(provider=None, model=None, messages=None, temperature=0.7, max_tokens=4096, api_key=None):
    """调用AI模型（兼容OpenAI格式），支持融合通道和单一模型直连"""
    if messages is None:
        messages = []
    provider = provider or 'fusion'
    provider_config = AI_MODELS.get(provider, AI_MODELS['fusion'])
    model = model or provider_config['model']

    # 根据provider获取对应的API凭据
    base_url, default_key = _get_provider_credentials(provider)
    effective_key = api_key or default_key
    url = f"{base_url}/chat/completions"
    payload = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens,
        'stream': False
    }
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {effective_key}'
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        data = resp.json()
        if 'error' in data:
            raise Exception(data['error'].get('message', str(data['error'])))
        content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
        usage = data.get('usage', {})
        return {'content': content, 'usage': usage, 'model': data.get('model', model)}
    except requests.exceptions.Timeout:
        raise Exception('AI请求超时')
    except requests.exceptions.ConnectionError:
        raise Exception('AI服务连接失败')
    except json.JSONDecodeError:
        raise Exception('AI响应解析失败')
    except Exception as e:
        if 'AI' not in str(e):
            raise Exception(f'AI请求失败: {str(e)}')
        raise


def call_ai_with_fallback(provider=None, model=None, messages=None, **kwargs):
    """带自动降级的AI调用"""
    try:
        return call_ai_model(provider=provider, model=model, messages=messages, **kwargs)
    except Exception as err:
        err_msg = str(err)
        fallback_keywords = ['No available channel', 'model not found', 'does not exist',
                           'not available', 'insufficient_quota', 'rate limit']
        if any(kw in err_msg for kw in fallback_keywords):
            logger.info(f"模型 {model} 不可用，尝试降级...")
            for fallback_model in FALLBACK_MODELS:
                if fallback_model == model:
                    continue
                try:
                    logger.info(f"尝试降级模型: {fallback_model}")
                    result = call_ai_model(provider='fusion', model=fallback_model, messages=messages, **kwargs)
                    result['fallbackFrom'] = model
                    result['fallbackTo'] = fallback_model
                    return result
                except Exception:
                    continue
            raise Exception('所有模型均不可用，请稍后重试')
        raise


def web_search(query, max_results=5):
    """联网搜索"""
    try:
        search_url = f"https://www.bing.com/search?q={requests.utils.quote(query)}"
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        resp = requests.get(search_url, headers=headers, timeout=10)
        html = resp.text
        results = []
        pattern = r'<li class="b_algo"><h2><a href="([^"]+)"[^>]*>(.*?)</a></h2><div[^>]*>(.*?)</div>'
        matches = re.findall(pattern, html, re.DOTALL)
        for url, title, snippet in matches[:max_results]:
            clean_title = re.sub(r'<[^>]+>', '', title).strip()
            clean_snippet = re.sub(r'<[^>]+>', '', snippet).strip()
            if clean_title and url.startswith('http'):
                results.append({'title': clean_title, 'url': url, 'snippet': clean_snippet})
        if not results:
            ddg_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
            resp = requests.get(ddg_url, headers=headers, timeout=10)
            html = resp.text
            pattern = r'<a rel="nofollow" class="result__a" href="([^"]+)">(.*?)</a>.*?<a class="result__snippet"[^>]*>(.*?)</a>'
            matches = re.findall(pattern, html, re.DOTALL)
            for url, title, snippet in matches[:max_results]:
                clean_title = re.sub(r'<[^>]+>', '', title).strip()
                clean_snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                if clean_title:
                    results.append({'title': clean_title, 'url': url, 'snippet': clean_snippet})
        return results
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        return []


def fetch_url_content(url, max_length=3000):
    """抓取网页内容"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=10)
        html = resp.text
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:max_length]
    except Exception:
        return ''


def ai_search(query, provider=None, model=None):
    """AI+联网搜索融合"""
    search_results = web_search(query)
    page_contents = []
    for r in search_results[:3]:
        content = fetch_url_content(r['url'])
        if content:
            page_contents.append({'title': r['title'], 'url': r['url'], 'content': content[:2000]})
    search_context = "搜索结果：\n"
    for i, r in enumerate(search_results, 1):
        search_context += f"{i}. {r['title']} - {r['snippet']}\n来源: {r['url']}\n\n"
    if page_contents:
        search_context += "\n网页详细内容：\n"
        for p in page_contents:
            search_context += f"【{p['title']}】({p['url']})\n{p['content'][:1500]}\n\n"
    messages = [
        {'role': 'system', 'content': '你是一个智能搜索助手。请基于搜索结果和网页内容，给出全面、准确的回答。请标注信息来源。'},
        {'role': 'user', 'content': f'问题：{query}\n\n{search_context}'}
    ]
    return call_ai_with_fallback(provider=provider, model=model, messages=messages, temperature=0.5)


# ============ 知识库管理 ============
KNOWLEDGE_DIR = os.path.join(BASE_DIR, 'knowledge')
KNOWLEDGE_META_PATH = os.path.join(KNOWLEDGE_DIR, 'meta.json')


def ensure_knowledge_dir():
    """确保知识库目录存在"""
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    if not os.path.exists(KNOWLEDGE_META_PATH):
        with open(KNOWLEDGE_META_PATH, 'w', encoding='utf-8') as f:
            json.dump({'items': []}, f, ensure_ascii=False, indent=2)


def get_knowledge_list():
    """获取知识库列表"""
    ensure_knowledge_dir()
    try:
        with open(KNOWLEDGE_META_PATH, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        return meta.get('items', [])
    except Exception:
        return []


def add_knowledge_item(item):
    """添加知识库条目"""
    ensure_knowledge_dir()
    items = get_knowledge_list()
    items.append(item)
    with open(KNOWLEDGE_META_PATH, 'w', encoding='utf-8') as f:
        json.dump({'items': items}, f, ensure_ascii=False, indent=2)
    return True


def delete_knowledge_item(item_id):
    """删除知识库条目"""
    ensure_knowledge_dir()
    items = get_knowledge_list()
    new_items = [i for i in items if i.get('id') != item_id]
    for i in items:
        if i.get('id') == item_id and i.get('file_path'):
            fp = os.path.join(KNOWLEDGE_DIR, i['file_path'])
            if os.path.exists(fp):
                os.remove(fp)
    with open(KNOWLEDGE_META_PATH, 'w', encoding='utf-8') as f:
        json.dump({'items': new_items}, f, ensure_ascii=False, indent=2)
    return True


def get_knowledge_context(max_length=6000):
    """获取知识库上下文（用于AI生成时注入）"""
    items = get_knowledge_list()
    if not items:
        return ''
    context_parts = []
    total_len = 0
    for item in items:
        content = item.get('content', '')
        name = item.get('name', '未知')
        if content:
            part = f"=== {name} ===\n{content}\n\n"
            if total_len + len(part) > max_length:
                break
            context_parts.append(part)
            total_len += len(part)
    return ''.join(context_parts)


def parse_uploaded_file(filepath, filename):
    """解析上传的文件，提取文本内容"""
    ext = os.path.splitext(filename)[1].lower()
    content = ''
    file_type = 'unknown'

    try:
        if ext in ('.docx', '.doc'):
            file_type = 'word'
            from doc_proofread.parsers.docx_parser import parse_docx
            result = parse_docx(filepath)
            texts = result.get('texts', [])
            content = '\n'.join([t.get('content', '') for t in texts])
            tables = result.get('tables', [])
            for tbl in tables:
                headers = tbl.get('headers', [])
                content += '\n\n表格：' + ' | '.join(headers) + '\n'
                for row in tbl.get('rows', []):
                    cells = row.get('cells', [])
                    content += ' | '.join(cells) + '\n'
        elif ext in ('.xlsx', '.xls'):
            file_type = 'excel'
            from doc_proofread.parsers.xlsx_parser import parse_xlsx
            result = parse_xlsx(filepath)
            tables = result.get('tables', [])
            for tbl in tables:
                sheet_name = tbl.get('sheet_name', '')
                content += f'\n=== Sheet: {sheet_name} ===\n'
                headers = tbl.get('headers', [])
                content += ' | '.join([str(h) for h in headers]) + '\n'
                for row in tbl.get('rows', []):
                    cells = row.get('cells', [])
                    content += ' | '.join([str(c) for c in cells]) + '\n'
        elif ext in ('.pptx', '.ppt'):
            file_type = 'ppt'
            from doc_proofread.parsers.pptx_parser import parse_pptx
            result = parse_pptx(filepath)
            texts = result.get('texts', [])
            for t in texts:
                slide = t.get('slide', '')
                content += f'第{slide}页：{t.get("content", "")}\n'
            tables = result.get('tables', [])
            for tbl in tables:
                slide = tbl.get('slide', '')
                content += f'\n第{slide}页表格：'
                headers = tbl.get('headers', [])
                content += ' | '.join(headers) + '\n'
                for row in tbl.get('rows', []):
                    cells = row.get('cells', [])
                    content += ' | '.join(cells) + '\n'
        elif ext == '.pdf':
            file_type = 'pdf'
            from doc_proofread.parsers.pdf_parser import parse_pdf
            result = parse_pdf(filepath)
            texts = result.get('texts', [])
            content = '\n'.join([t.get('content', '') for t in texts])
        elif ext in ('.txt', '.md', '.json', '.csv'):
            file_type = 'text'
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
    except Exception as e:
        logger.error(f"解析文件 {filename} 失败: {e}")
        content = f'[解析失败: {str(e)}]'

    return {'content': content, 'type': file_type, 'length': len(content)}
