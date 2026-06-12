# ============ URL检测与渠道管理API ============
from flask import request, jsonify
import requests as _req
from bs4 import BeautifulSoup as _BS
from urllib.parse import urlparse as _urlparse
from datetime import datetime
import re as _re

def register_api_routes(app, app_config, db, logger):
    """注册URL检测和渠道管理API路由"""

    @app.route('/api/detect-url', methods=['POST'])
    def detect_url():
        """检测URL类型，自动识别RSS/HTML/JSON，返回建议的渠道配置"""
        try:
            url = request.json.get('url', '').strip()
            if not url:
                return jsonify({"status": "error", "message": "URL不能为空"})
            if not url.startswith('http'):
                url = 'https://' + url
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            try:
                resp = _req.get(url, headers=headers, timeout=10, allow_redirects=True)
                resp.encoding = resp.apparent_encoding or 'utf-8'
            except Exception as e:
                return jsonify({"status": "error", "message": "无法访问该URL: " + str(e)})
            content_type = resp.headers.get('Content-Type', '')
            text = resp.text.strip() if resp.text else ''
            is_rss = ('<rss' in text[:500] or '<feed' in text[:500] or '<channel' in text[:500]
                      or 'xml' in content_type.lower() or url.endswith('.xml') or '/rss' in url.lower() or '/feed' in url.lower())
            is_json = ('json' in content_type.lower() or url.endswith('.json') or '/api/' in url.lower())
            if is_rss:
                source_type = 'RSS'
            elif is_json:
                source_type = 'JSON API'
            else:
                source_type = 'HTML网页'
            site_name = ''
            try:
                if is_rss:
                    soup = _BS(text, 'xml')
                    title_tag = soup.find('title')
                    if title_tag:
                        site_name = title_tag.get_text(strip=True)
                else:
                    soup = _BS(text, 'html.parser')
                    title_tag = soup.find('title')
                    if title_tag:
                        site_name = title_tag.get_text(strip=True)
                    if not site_name:
                        meta = soup.find('meta', property='og:site_name')
                        if meta:
                            site_name = meta.get('content', '')
            except Exception:
                pass
            if not site_name:
                parsed = _urlparse(url)
                site_name = parsed.netloc.replace('www.', '').split('.')[0].title()
            source_key = _re.sub(r'[^a-zA-Z0-9]', '_', site_name).lower().strip('_')
            if not source_key:
                source_key = 'custom_' + str(int(datetime.now().timestamp()))
            return jsonify({
                "status": "success",
                "data": {
                    "url": url,
                    "source_type": source_type,
                    "source_name": site_name[:50],
                    "source_key": source_key,
                    "status_code": resp.status_code,
                    "content_length": len(text)
                }
            })
        except Exception as e:
            logger.exception("URL检测失败")
            return jsonify({"status": "error", "message": str(e)})

    @app.route('/api/add-source', methods=['POST'])
    def add_source():
        """添加新的爬取渠道"""
        try:
            data = request.json
            source_type = data.get('type', '')
            source_key = data.get('key', '')
            source_name = data.get('name', '')
            source_url = data.get('url', '')
            enabled = data.get('enabled', True)
            if not source_type or not source_key or not source_url:
                return jsonify({"status": "error", "message": "缺少必要参数"})
            if source_type == 'operator':
                sources = app_config.operator_sources
            elif source_type == 'competitor':
                sources = app_config.competitor_sources
            elif source_type == 'hardware':
                sources = app_config.hardware_sources
            else:
                return jsonify({"status": "error", "message": "无效的渠道类型"})
            sources[source_key] = {'name': source_name, 'url': source_url, 'enabled': enabled}
            app_config.save()
            logger.info("添加新渠道: " + source_type + "/" + source_key + " - " + source_name + "(" + source_url + ")")
            return jsonify({"status": "success", "message": "渠道添加成功"})
        except Exception as e:
            logger.exception("添加渠道失败")
            return jsonify({"status": "error", "message": str(e)})

    @app.route('/api/lookup-site', methods=['POST'])
    def lookup_site():
        """通过网站名称查找对应的URL地址，支持中英文网站名"""
        try:
            name = request.json.get('name', '').strip()
            if not name:
                return jsonify({"status": "error", "message": "名称不能为空"})

            # 常见中文科技/IT网站映射表
            KNOWN_SITES = {
                # === IT资讯 ===
                'csdn': {'name': 'CSDN', 'url': 'https://www.csdn.net', 'rss': 'https://blog.csdn.net/rss/list', 'type': 'RSS'},
                '博客园': {'name': '博客园', 'url': 'https://www.cnblogs.com', 'rss': 'https://feed.cnblogs.com/blog/sitehome/rss', 'type': 'RSS'},
                '掘金': {'name': '掘金', 'url': 'https://juejin.cn', 'rss': '', 'type': 'HTML网页'},
                '知乎': {'name': '知乎', 'url': 'https://www.zhihu.com', 'rss': '', 'type': 'HTML网页'},
                '36氪': {'name': '36氪', 'url': 'https://36kr.com', 'rss': 'https://36kr.com/feed', 'type': 'RSS'},
                'it之家': {'name': 'IT之家', 'url': 'https://www.ithome.com', 'rss': 'https://www.ithome.com/rss/', 'type': 'RSS'},
                'ithome': {'name': 'IT之家', 'url': 'https://www.ithome.com', 'rss': 'https://www.ithome.com/rss/', 'type': 'RSS'},
                '钛媒体': {'name': '钛媒体', 'url': 'https://www.tmtpost.com', 'rss': '', 'type': 'HTML网页'},
                '雷锋网': {'name': '雷锋网', 'url': 'https://www.leiphone.com', 'rss': '', 'type': 'HTML网页'},
                '开源中国': {'name': '开源中国', 'url': 'https://www.oschina.net', 'rss': 'https://www.oschina.net/action/rss', 'type': 'RSS'},
                'oschina': {'name': '开源中国', 'url': 'https://www.oschina.net', 'rss': 'https://www.oschina.net/action/rss', 'type': 'RSS'},
                'infoq': {'name': 'InfoQ中文', 'url': 'https://www.infoq.cn', 'rss': '', 'type': 'HTML网页'},
                'infoq中文': {'name': 'InfoQ中文', 'url': 'https://www.infoq.cn', 'rss': '', 'type': 'HTML网页'},
                '中关村在线': {'name': '中关村在线', 'url': 'https://www.zol.com.cn', 'rss': '', 'type': 'HTML网页'},
                'zol': {'name': '中关村在线', 'url': 'https://www.zol.com.cn', 'rss': '', 'type': 'HTML网页'},
                '太平洋电脑': {'name': '太平洋电脑网', 'url': 'https://www.pconline.com.cn', 'rss': '', 'type': 'HTML网页'},
                '太平洋电脑网': {'name': '太平洋电脑网', 'url': 'https://www.pconline.com.cn', 'rss': '', 'type': 'HTML网页'},
                'pconline': {'name': '太平洋电脑网', 'url': 'https://www.pconline.com.cn', 'rss': '', 'type': 'HTML网页'},
                '快科技': {'name': '快科技', 'url': 'https://www.mydrivers.com', 'rss': '', 'type': 'HTML网页'},
                'mydrivers': {'name': '快科技', 'url': 'https://www.mydrivers.com', 'rss': '', 'type': 'HTML网页'},
                '驱动之家': {'name': '驱动之家', 'url': 'https://www.mydrivers.com', 'rss': '', 'type': 'HTML网页'},
                '虎嗅': {'name': '虎嗅', 'url': 'https://www.huxiu.com', 'rss': '', 'type': 'HTML网页'},
                '少数派': {'name': '少数派', 'url': 'https://sspai.com', 'rss': 'https://sspai.com/feed', 'type': 'RSS'},
                'sspai': {'name': '少数派', 'url': 'https://sspai.com', 'rss': 'https://sspai.com/feed', 'type': 'RSS'},
                'segmentfault': {'name': 'SegmentFault', 'url': 'https://segmentfault.com', 'rss': '', 'type': 'HTML网页'},
                '思否': {'name': 'SegmentFault', 'url': 'https://segmentfault.com', 'rss': '', 'type': 'HTML网页'},
                'v2ex': {'name': 'V2EX', 'url': 'https://www.v2ex.com', 'rss': 'https://www.v2ex.com/index.xml', 'type': 'RSS'},
                'cnbeta': {'name': 'cnBeta', 'url': 'https://www.cnbeta.com', 'rss': 'https://www.cnbeta.com/backend.php', 'type': 'RSS'},
                '新浪科技': {'name': '新浪科技', 'url': 'https://tech.sina.com.cn', 'rss': '', 'type': 'HTML网页'},
                '腾讯科技': {'name': '腾讯科技', 'url': 'https://tech.qq.com', 'rss': '', 'type': 'HTML网页'},
                '网易科技': {'name': '网易科技', 'url': 'https://tech.163.com', 'rss': '', 'type': 'HTML网页'},
                '搜狐科技': {'name': '搜狐科技', 'url': 'https://it.sohu.com', 'rss': '', 'type': 'HTML网页'},
                'freebuf': {'name': 'FreeBuf', 'url': 'https://www.freebuf.com', 'rss': '', 'type': 'HTML网页'},
                '安全客': {'name': '安全客', 'url': 'https://www.anquanke.com', 'rss': '', 'type': 'HTML网页'},
                '先知社区': {'name': '先知社区', 'url': 'https://xz.aliyun.com', 'rss': '', 'type': 'HTML网页'},
                # === 云服务 ===
                '阿里云': {'name': '阿里云', 'url': 'https://www.aliyun.com', 'rss': '', 'type': 'HTML网页'},
                '腾讯云': {'name': '腾讯云', 'url': 'https://cloud.tencent.com', 'rss': '', 'type': 'HTML网页'},
                '华为云': {'name': '华为云', 'url': 'https://www.huaweicloud.com', 'rss': '', 'type': 'HTML网页'},
                'gitee': {'name': 'Gitee', 'url': 'https://gitee.com', 'rss': '', 'type': 'HTML网页'},
                '码云': {'name': 'Gitee', 'url': 'https://gitee.com', 'rss': '', 'type': 'HTML网页'},
                'github': {'name': 'GitHub', 'url': 'https://github.com', 'rss': '', 'type': 'HTML网页'},
                '百度智能云': {'name': '百度智能云', 'url': 'https://cloud.baidu.com', 'rss': '', 'type': 'HTML网页'},
                'baidu_cloud': {'name': '百度智能云', 'url': 'https://cloud.baidu.com', 'rss': '', 'type': 'HTML网页'},
                # === 运营商采购 ===
                '中国采购与招标网': {'name': '中国采购与招标网', 'url': 'https://chinabidding.com.cn/', 'rss': '', 'type': 'HTML网页'},
                'bidcenter': {'name': '中国采购与招标网', 'url': 'https://chinabidding.com.cn/', 'rss': '', 'type': 'HTML网页'},
                '全国公共资源交易平台': {'name': '全国公共资源交易平台', 'url': 'https://www.ggzy.gov.cn', 'rss': '', 'type': 'HTML网页'},
                'ggzy': {'name': '全国公共资源交易平台', 'url': 'https://www.ggzy.gov.cn', 'rss': '', 'type': 'HTML网页'},
                '中国电信阳光采购网': {'name': '中国电信阳光采购网', 'url': 'https://caigou.chinatelecom.com.cn/MSS-PORTAL/account/login.do', 'rss': '', 'type': 'HTML网页'},
                '中国移动采购和招标网': {'name': '中国移动采购和招标网', 'url': 'https://b2b.10086.cn/#/index', 'rss': '', 'type': 'HTML网页'},
                '移动采购': {'name': '中国移动采购和招标网', 'url': 'https://b2b.10086.cn/#/index', 'rss': '', 'type': 'HTML网页'},
                '中国联通供应商': {'name': '中国联通供应商', 'url': 'https://www.cuecp.cn/login/', 'rss': '', 'type': 'HTML网页'},
                '联通国际采购': {'name': '联通国际采购与招投标平台', 'url': 'https://etender.chinaunicomglobal.com:8081/supp/index.html#/', 'rss': '', 'type': 'HTML网页'},
                '中国铁塔电子采购': {'name': '中国铁塔电子采购平台', 'url': 'https://ebid.chinatowercom.cn/zgtt/', 'rss': '', 'type': 'HTML网页'},
                '中国铁塔生态合作': {'name': '中国铁塔生态合作平台', 'url': 'https://partner.chinatowercom.cn', 'rss': '', 'type': 'HTML网页'},
                '中国电信政企生态': {'name': '中国电信政企生态合作统一开放平台', 'url': 'https://b.189.cn/cooperation#/home', 'rss': '', 'type': 'HTML网页'},
                # === 移动各省 ===
                '广东移动': {'name': '中国移动广东公司供应商门户', 'url': 'https://www.telewiki.cn', 'rss': '', 'type': 'HTML网页'},
                '山东移动': {'name': '山东移动生态合作统一门户', 'url': 'https://xe.sd.chinamobile.com/pms-portal-react/#/login', 'rss': '', 'type': 'HTML网页'},
                '浙江移动': {'name': '浙江移动生态合作伙伴门户', 'url': 'http://scm.zj.chinamobile.com/open/zqportal/#/portal', 'rss': '', 'type': 'HTML网页'},
                '江苏移动': {'name': '江苏移动招募甄选平台', 'url': 'https://www.jsdict.cn/#/login?user_type=2', 'rss': '', 'type': 'HTML网页'},
                '四川移动': {'name': '四川移动生态合作统一门户', 'url': 'https://compass.scmcc.com.cn:18091/partner/index.html#/ptn/login', 'rss': '', 'type': 'HTML网页'},
                '湖南移动': {'name': '中国移动湖南ICT生态合作伙伴管理平台', 'url': 'https://partner.hncmict.com/ictp/index', 'rss': '', 'type': 'HTML网页'},
                '河南移动': {'name': '中国移动河南供应商协同平台', 'url': 'http://10.92.81.26/vendorportal/mainPage.jsp', 'rss': '', 'type': 'HTML网页'},
                '河北移动': {'name': '中国移动河北合作管理系统', 'url': 'http://www.he.10086.cn/partner/#/sys/cms/loginPartner', 'rss': '', 'type': 'HTML网页'},
                '云南移动': {'name': '中国移动云南供应商协同门户', 'url': 'https://scms.netvan.cn', 'rss': '', 'type': 'HTML网页'},
                '安徽移动': {'name': '安徽移动供应商门户系统', 'url': 'http://b2b.ah.chinamobile.com', 'rss': '', 'type': 'HTML网页'},
                '重庆移动': {'name': '重庆移动政企DICT合作门户', 'url': 'https://www.cqmc.com', 'rss': '', 'type': 'HTML网页'},
                '内蒙古移动': {'name': '中国移动内蒙古供应商协同门户', 'url': 'https://b2b.nm139.com:81/static/views/vendorLogin.html', 'rss': '', 'type': 'HTML网页'},
                '吉林移动': {'name': '吉林移动政企合作伙伴生态运营管理平台', 'url': 'https://partner.10086-cname.cn/login', 'rss': '', 'type': 'HTML网页'},
                '陕西移动': {'name': '陕西移动ICT项目管理平台', 'url': 'https://cooperator.sxydzq.cn/cooperator/to_login.action', 'rss': '', 'type': 'HTML网页'},
                '黑龙江移动': {'name': '黑龙江移动DICT生态合作统一门户', 'url': 'http://www.hl.10086.cn/pms-portal-react/#/login', 'rss': '', 'type': 'HTML网页'},
                '江西移动': {'name': '江西移动阳光生态合作平台', 'url': 'https://jx.10086.cn/partner/console/partner/#/enterprise/enterpriseInfo', 'rss': '', 'type': 'HTML网页'},
                '湖北移动': {'name': '中国移动湖北合作伙伴管理系统', 'url': 'http://211.137.70.55/coop-partner-module/index.jsp', 'rss': '', 'type': 'HTML网页'},
                '北京移动': {'name': '北京移动合作生态管理平台', 'url': 'https://xywhz.bj.chinamobile.com/web/#/login', 'rss': '', 'type': 'HTML网页'},
                '贵州移动': {'name': '贵州移动信息科技电子招投标平台', 'url': 'http://36.137.157.155:50001/supplier/notice?city=818', 'rss': '', 'type': 'HTML网页'},
                # === 政府采购 ===
                '广东省政府采购网': {'name': '广东省政府采购网', 'url': 'https://gdgpo.czt.gd.gov.cn/', 'rss': '', 'type': 'HTML网页'},
                '北京市政府采购': {'name': '北京市政府采购电子交易平台', 'url': 'http://zbcg-bjzc.zhongcy.com/bjczj-portal-site/index.html#/home', 'rss': '', 'type': 'HTML网页'},
                '京华云采': {'name': '北京市政府采购电子卖场(京华云采)', 'url': 'https://www.zhongcy.com', 'rss': '', 'type': 'HTML网页'},
                '广西政府采购网': {'name': '广西政府采购网', 'url': 'http://www.ccgp-guangxi.gov.cn/', 'rss': '', 'type': 'HTML网页'},
                '中央政府采购网': {'name': '中央政府采购网', 'url': 'https://www.zycg.gov.cn/', 'rss': '', 'type': 'HTML网页'},
                '青岛公共资源': {'name': '全国公共资源交易平台(山东青岛)', 'url': 'https://ggzy.qingdao.gov.cn', 'rss': '', 'type': 'HTML网页'},
                '深圳技术转移': {'name': '深圳市技术转移促进中心业务系统', 'url': 'http://szjssc.org.cn/fg/toFgIndexPage.do', 'rss': '', 'type': 'HTML网页'},
                # === 招标平台 ===
                '诚E招标': {'name': '诚E招标书购买', 'url': 'https://www.chengezhao.com/member/sysreg/register.htm?isAudit=1&no_sitemesh', 'rss': '', 'type': 'HTML网页'},
                '中招联合': {'name': '中招联合电子招标采购平台', 'url': 'http://www.365trade.com.cn', 'rss': '', 'type': 'HTML网页'},
                '易招': {'name': '易招电子招投标采购交易平台(甘肃)', 'url': 'http://www.caie.xin/login', 'rss': '', 'type': 'HTML网页'},
                '黔云招采': {'name': '黔云招采电子招标采购交易平台', 'url': 'https://www.e-qyzc.com/#/home', 'rss': '', 'type': 'HTML网页'},
                '邮E招': {'name': '邮E招平台', 'url': 'https://www.youezhao.cn/', 'rss': '', 'type': 'HTML网页'},
                '上海国际招标': {'name': '上海国际招标有限公司', 'url': 'https://zb.shabidding.com/ebidding/#/ls/account?type=en', 'rss': '', 'type': 'HTML网页'},
                '广咨电子': {'name': '广咨电子招投标交易平台', 'url': 'https://www.gzebid.cn/#/register', 'rss': '', 'type': 'HTML网页'},
                '广东机电招标': {'name': '广东省机电设备招标中心交易平台2.0', 'url': 'http://gmeetc.gdebidding.com/ebidding/#/login', 'rss': '', 'type': 'HTML网页'},
                '竞采星': {'name': '竞采星', 'url': 'https://login.easyjcx.com/#/su/register', 'rss': '', 'type': 'HTML网页'},
                '乐采云': {'name': '乐采云平台', 'url': 'https://www.lecaiyun.com/', 'rss': '', 'type': 'HTML网页'},
                '中国通用招标网': {'name': '中国通用招标网电子招标投标平台', 'url': 'https://cgci.china-tender.com.cn/zjxm/', 'rss': '', 'type': 'HTML网页'},
                '链捷招': {'name': '中通服供应链管理电子招标系统(链捷招)', 'url': 'https://zb.chinaccsscm.cn/', 'rss': '', 'type': 'HTML网页'},
                # === 电力/能源 ===
                '国家电网': {'name': '国家电网电子商务平台-电工交易专区', 'url': 'https://sgccetp.com.cn/portal/#/', 'rss': '', 'type': 'HTML网页'},
                '国家电投': {'name': '国家电投电子商务平台', 'url': 'https://ebid.espic.com.cn', 'rss': '', 'type': 'HTML网页'},
                '中国航空油料': {'name': '中国航空油料集团', 'url': 'https://zc.cnaf.com/', 'rss': '', 'type': 'HTML网页'},
                '中国五矿': {'name': '中国五矿集团供应链管理平台', 'url': 'https://ec.minmetals.com.cn/logonAction.do', 'rss': '', 'type': 'HTML网页'},
                # === 科技公司供应商 ===
                '阿里巴巴供应商': {'name': '阿里巴巴集团供应商门户', 'url': 'https://csupplier.alibabacorp.com/supplier/pub/index.htm', 'rss': '', 'type': 'HTML网页'},
                '阿里巴巴厂商协同': {'name': '阿里巴巴厂商协同平台', 'url': 'https://mozi-login.alibaba-inc.com/', 'rss': '', 'type': 'HTML网页'},
                '阿里云合作伙伴': {'name': '阿里云产品生态合作伙伴', 'url': 'https://partner.aliyun.com/neibu/productecologicalpartner', 'rss': '', 'type': 'HTML网页'},
                '百度供应商': {'name': '百度云供应商系统', 'url': 'https://caigou.baidu.com/login.jsp', 'rss': '', 'type': 'HTML网页'},
                '京东生态': {'name': '京东科技生态合作平台', 'url': 'https://shengtai.jd.com', 'rss': '', 'type': 'HTML网页'},
                '快手供应商': {'name': '快手供应商后台', 'url': 'https://supplier.corp.kuaishou.com/homePage', 'rss': '', 'type': 'HTML网页'},
                '网易供应商': {'name': '网易集团供应商系统', 'url': 'https://ebooking.n.netease.com/#/login', 'rss': '', 'type': 'HTML网页'},
                '华为合作伙伴': {'name': '华为企业合作伙伴', 'url': 'https://partner.huawei.com/#/cn/web/china', 'rss': '', 'type': 'HTML网页'},
                '中兴招标': {'name': '中兴通讯招标系统', 'url': 'https://bid.zte.com.cn/ebid/com/zte/product/ui/web/Application/default.aspx', 'rss': '', 'type': 'HTML网页'},
                '中兴供应链': {'name': 'SCC中兴供应链协同', 'url': 'https://supply.zte.com.cn', 'rss': '', 'type': 'HTML网页'},
                '浪潮采购': {'name': '浪潮电子采购平台', 'url': 'https://scs.inspur.com/homepage', 'rss': '', 'type': 'HTML网页'},
                '烽火超微': {'name': '烽火超微SRM系统', 'url': 'https://srm.fiberhome.com/', 'rss': '', 'type': 'HTML网页'},
                '长虹佳华': {'name': '长虹佳华企业账户', 'url': 'http://webapps.changhongit.cn:8202/supplier/home/#/login', 'rss': '', 'type': 'HTML网页'},
                '神州信息': {'name': '神州信息供应商门户', 'url': 'http://partner.dcits.com/portal/#/user/login', 'rss': '', 'type': 'HTML网页'},
                '完美世界': {'name': '完美世界股份有限公司', 'url': 'https://wanmei.going-link.com/app/public/home', 'rss': '', 'type': 'HTML网页'},
                '哪吒': {'name': '哪吒公司网上招报价系统', 'url': 'http://124.70.137.212:9090/nzbp/webui/inner/index_inner_2.0.jsp', 'rss': '', 'type': 'HTML网页'},
                '南航招标': {'name': '中国南方航空招标采购网', 'url': 'https://supplier.csair.cn/bmv6_supplier/eip/logon/index_supplier.html', 'rss': '', 'type': 'HTML网页'},
                # === 设计院 ===
                '华信设计院': {'name': '华信设计院电子招标平台', 'url': 'https://hxzhaobiao.hxdi.cn/', 'rss': '', 'type': 'HTML网页'},
                '广东电信设计院': {'name': '广东省电信规划设计院电子招投标平台', 'url': 'https://bidding.gpdi.com/homepage/', 'rss': '', 'type': 'HTML网页'},
                # === 算力平台 ===
                '贵州算力': {'name': '贵州算力商城平台', 'url': 'https://www.gzsuanli.com/ticket', 'rss': '', 'type': 'HTML网页'},
                '和林格尔': {'name': '和林格尔集群多云算力资源监测与调度平台', 'url': 'https://www.nmgsuanli.com/page/687924429644103680', 'rss': '', 'type': 'HTML网页'},
                # === 友商 ===
                '海马云': {'name': '海马云', 'url': 'https://www.haimacloud.com', 'rss': '', 'type': 'HTML网页'},
                '蔚领时代': {'name': '蔚领时代', 'url': 'https://www.wltime.com', 'rss': '', 'type': 'HTML网页'},
                '智谱': {'name': '智谱AI', 'url': 'https://www.zhipuai.cn', 'rss': '', 'type': 'HTML网页'},
                '瑞云渲染': {'name': '瑞云渲染', 'url': 'https://www.rayvision.com', 'rss': '', 'type': 'HTML网页'},
                '顺网': {'name': '顺网科技', 'url': 'https://www.shunwang.com', 'rss': '', 'type': 'HTML网页'},
                '锐捷网络': {'name': '锐捷网络', 'url': 'https://www.ruijie.com.cn', 'rss': '', 'type': 'HTML网页'},
                '云天畅想': {'name': '云天畅想', 'url': '', 'rss': '', 'type': 'HTML网页'},
            }

            # 生成source_key的辅助函数，支持中文名
            def _make_key(n):
                # 先从app_config的sources中查找（这些key都是英文的）
                for src_dict in [app_config.operator_sources, app_config.competitor_sources, app_config.hardware_sources]:
                    for k, v in src_dict.items():
                        if v.get('name') == n:
                            return k
                # 再从已知站点中找纯英文key（优先用英文别名）
                best_key = ''
                for k, v in KNOWN_SITES.items():
                    if v['name'] == n:
                        key = _re.sub(r'[^a-zA-Z0-9]', '_', k).lower().strip('_')
                        if key and (not best_key or key.isascii()):
                            best_key = key
                            # 纯英文key优先
                            if k.isascii():
                                return key
                if best_key:
                    return best_key
                # 用名称本身生成
                key = _re.sub(r'[^a-zA-Z0-9]', '_', n).lower().strip('_')
                if key:
                    return key
                # 纯中文名，用hash生成key
                import hashlib
                return 'site_' + hashlib.md5(n.encode('utf-8')).hexdigest()[:8]

            name_lower = name.lower().strip()
            # 1. 精确匹配
            result = KNOWN_SITES.get(name_lower) or KNOWN_SITES.get(name)
            if result:
                best_url = result.get('rss') or result['url']
                return jsonify({
                    "status": "success",
                    "data": {
                        "name": result['name'],
                        "url": best_url,
                        "site_url": result['url'],
                        "source_type": result.get('type', 'HTML网页'),
                        "source_key": _make_key(result['name']),
                        "match_type": "exact"
                    }
                })

            # 2. 模糊匹配：在已知站点中搜索
            matches = []
            for key, info in KNOWN_SITES.items():
                if name_lower in key.lower() or name_lower in info['name'].lower():
                    matches.append(info)
            if matches:
                best = matches[0]
                best_url = best.get('rss') or best['url']
                return jsonify({
                    "status": "success",
                    "data": {
                        "name": best['name'],
                        "url": best_url,
                        "site_url": best['url'],
                        "source_type": best.get('type', 'HTML网页'),
                        "source_key": _make_key(best['name']),
                        "match_type": "fuzzy",
                        "alternatives": [{"name": m['name'], "url": m.get('rss') or m['url']} for m in matches[1:4]]
                    }
                })

            # 3. 搜索引擎查找：通过Bing搜索API尝试找到网站
            try:
                search_url = 'https://www.bing.com/search?q=' + _req.utils.quote(name + ' 官网')
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                resp = _req.get(search_url, headers=headers, timeout=8, allow_redirects=True)
                resp.encoding = resp.apparent_encoding or 'utf-8'
                soup = _BS(resp.text, 'html.parser')
                # 提取搜索结果中的URL
                found_urls = []
                for li in soup.select('li.b_algo'):
                    a_tag = li.find('a')
                    if a_tag and a_tag.get('href'):
                        href = a_tag['href']
                        if href.startswith('http') and 'bing.com' not in href and 'microsoft.com' not in href:
                            parsed = _urlparse(href)
                            domain = parsed.netloc
                            # 过滤掉搜索引擎和翻译等
                            skip_domains = ['translate.google', 'webcache.google', 'bing.com']
                            if not any(s in domain for s in skip_domains):
                                found_urls.append({'url': href, 'domain': domain, 'title': a_tag.get_text(strip=True)[:80]})
                if found_urls:
                    best = found_urls[0]
                    source_key = _make_key(name)
                    if not source_key:
                        source_key = 'custom_' + str(int(datetime.now().timestamp()))
                    return jsonify({
                        "status": "success",
                        "data": {
                            "name": name,
                            "url": best['url'],
                            "site_url": best['url'],
                            "source_type": 'HTML网页',
                            "source_key": source_key,
                            "match_type": "search",
                            "search_title": best.get('title', ''),
                            "alternatives": [{"name": u.get('title', u['domain']), "url": u['url']} for u in found_urls[1:4]]
                        }
                    })
            except Exception as e:
                logger.warning("搜索引擎查找失败: " + str(e))

            return jsonify({"status": "error", "message": '未找到"' + name + '"对应的网站，请直接输入URL地址'})
        except Exception as e:
            logger.exception("网站查找失败")
            return jsonify({"status": "error", "message": str(e)})

    @app.route('/api/remove-source', methods=['POST'])
    def remove_source():
        """删除爬取渠道"""
        try:
            data = request.json
            source_type = data.get('type', '')
            source_key = data.get('key', '')
            if not source_type or not source_key:
                return jsonify({"status": "error", "message": "缺少必要参数"})
            if source_type == 'operator':
                sources = app_config.operator_sources
            elif source_type == 'competitor':
                sources = app_config.competitor_sources
            elif source_type == 'hardware':
                sources = app_config.hardware_sources
            else:
                return jsonify({"status": "error", "message": "无效的渠道类型"})
            if source_key in sources:
                del sources[source_key]
                app_config.save()
                logger.info("删除渠道: " + source_type + "/" + source_key)
                return jsonify({"status": "success", "message": "渠道已删除"})
            else:
                return jsonify({"status": "error", "message": "渠道不存在"})
        except Exception as e:
            logger.exception("删除渠道失败")
            return jsonify({"status": "error", "message": str(e)})
