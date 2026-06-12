import os
from dataclasses import dataclass, field
from dotenv import load_dotenv
import copy

# 明确指定.env文件路径，确保无论从哪个目录启动都能正确加载
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

def _parse_list(env_val, default):
    if env_val:
        return tuple(item.strip() for item in env_val.split(',') if item.strip())
    return default

# 可配置的爬取渠道定义
OPERATOR_SOURCES = {
    # === 原有渠道 ===
    'bidcenter': {'name': '中国采购与招标网', 'url': 'https://chinabidding.com.cn/', 'enabled': True},
    'ggzy': {'name': '全国公共资源交易平台', 'url': 'https://www.ggzy.gov.cn', 'enabled': True},
    'rss_bid': {'name': 'RSS聚合招标信息', 'url': 'https://www.chinabidding.mofcom.gov.cn', 'enabled': True},
    # === 运营商采购平台 ===
    'chinatelecom_purchase': {'name': '中国电信阳光采购网', 'url': 'https://caigou.chinatelecom.com.cn/MSS-PORTAL/account/login.do', 'enabled': True},
    'cmcc_b2b': {'name': '中国移动采购和招标网', 'url': 'https://b2b.10086.cn/#/index', 'enabled': True},
    'unicom_supplier': {'name': '中国联通供应商', 'url': 'https://www.cuecp.cn/login/', 'enabled': True},
    'unicom_global': {'name': '联通国际采购与招投标平台', 'url': 'https://etender.chinaunicomglobal.com:8081/supp/index.html#/', 'enabled': True},
    'chinatower_ebid': {'name': '中国铁塔电子采购平台', 'url': 'https://ebid.chinatowercom.cn/zgtt/', 'enabled': True},
    'chinatower_eco': {'name': '中国铁塔生态合作平台', 'url': 'https://partner.chinatowercom.cn', 'enabled': True},
    # === 移动各省分公司 ===
    'cmcc_gd': {'name': '中国移动广东公司供应商门户', 'url': 'https://www.telewiki.cn', 'enabled': True},
    'cmcc_gd_partner': {'name': '广东移动合作伙伴服务门户', 'url': 'https://221.179.44.125/zhengqi/dict/ptn/login', 'enabled': True},
    'cmcc_gd_eco': {'name': '山东移动生态合作统一门户', 'url': 'https://xe.sd.chinamobile.com/pms-portal-react/#/login', 'enabled': True},
    'cmcc_zj': {'name': '浙江移动生态合作伙伴门户', 'url': 'http://scm.zj.chinamobile.com/open/zqportal/#/portal', 'enabled': True},
    'cmcc_zj_tech': {'name': '浙江移动数智科技供应商门户', 'url': 'http://scm.zj.chinamobile.com/open/jcportal/#/door/home', 'enabled': True},
    'cmcc_js': {'name': '江苏移动招募甄选平台', 'url': 'https://www.jsdict.cn/#/login?user_type=2', 'enabled': True},
    'cmcc_sc': {'name': '四川移动生态合作统一门户', 'url': 'https://compass.scmcc.com.cn:18091/partner/index.html#/ptn/login', 'enabled': True},
    'cmcc_hn': {'name': '中国移动湖南ICT生态合作伙伴管理平台', 'url': 'https://partner.hncmict.com/ictp/index', 'enabled': True},
    'cmcc_hn_ict': {'name': '湖南移动ICT生态合作伙伴管理平台', 'url': 'https://partner.hncmict.com/ictp/login', 'enabled': True},
    'cmcc_henan': {'name': '中国移动河南供应商协同平台', 'url': 'http://10.92.81.26/vendorportal/mainPage.jsp', 'enabled': False},
    'cmcc_hebei': {'name': '中国移动河北合作管理系统', 'url': 'http://www.he.10086.cn/partner/#/sys/cms/loginPartner', 'enabled': True},
    'cmcc_yn': {'name': '中国移动云南供应商协同门户', 'url': 'https://scms.netvan.cn', 'enabled': True},
    'cmcc_ah': {'name': '安徽移动供应商门户系统', 'url': 'http://b2b.ah.chinamobile.com', 'enabled': True},
    'cmcc_cq': {'name': '重庆移动政企DICT合作门户', 'url': 'https://www.cqmc.com', 'enabled': True},
    'cmcc_nm': {'name': '中国移动内蒙古供应商协同门户', 'url': 'https://b2b.nm139.com:81/static/views/vendorLogin.html', 'enabled': True},
    'cmcc_nm_dict': {'name': '内蒙古移动DICT合作门户', 'url': 'https://dict.nm135.cn:81/', 'enabled': True},
    'cmcc_jl': {'name': '吉林移动政企合作伙伴生态运营管理平台', 'url': 'https://partner.10086-cname.cn/login', 'enabled': True},
    'cmcc_sx': {'name': '陕西移动ICT项目管理平台', 'url': 'https://cooperator.sxydzq.cn/cooperator/to_login.action', 'enabled': True},
    'cmcc_hlj': {'name': '黑龙江移动DICT生态合作统一门户', 'url': 'http://www.hl.10086.cn/pms-portal-react/#/login', 'enabled': True},
    'cmcc_jx': {'name': '江西移动阳光生态合作平台', 'url': 'https://jx.10086.cn/partner/console/partner/#/enterprise/enterpriseInfo', 'enabled': True},
    'cmcc_hb': {'name': '中国移动湖北合作伙伴管理系统', 'url': 'http://211.137.70.55/coop-partner-module/index.jsp', 'enabled': False},
    'cmcc_online': {'name': '中国移动在线营销服务中心', 'url': 'https://bfms.deskpro.cn:21001/pms-portal-react/#/register', 'enabled': True},
    'cmcc_bj': {'name': '北京移动合作生态管理平台', 'url': 'https://xywhz.bj.chinamobile.com/web/#/login', 'enabled': True},
    'cmcc_suzhou': {'name': '中移(苏州)软件技术供应商协同门户', 'url': 'https://scm.cmecloud.cn/pages/auth/login.html', 'enabled': True},
    'cmcc_integrate': {'name': '中移集成合作伙伴招募与甄选系统', 'url': 'https://117.132.185.62:8051/static/views/home/supplier.html', 'enabled': True},
    'cmcc_recruit': {'name': '中移官网甄选招募平台', 'url': 'http://www.shcmct.com', 'enabled': True},
    'migu_cnds': {'name': '咪咕CNDS平台-服务商门户', 'url': 'http://cnds.migu.cn/', 'enabled': True},
    'cmcc_aijia': {'name': '移动爱家生态平台', 'url': 'https://open.home.10086.cn/openhomePortal/pages/ecologicalEmpowerment/entrance/', 'enabled': True},
    'cmcc_terminal': {'name': '一级终端营销管理系统', 'url': 'https://device.open.10086.cn:8017/', 'enabled': True},
    'guizhou_mobile': {'name': '贵州移动信息科技电子招投标平台', 'url': 'http://36.137.157.155:50001/supplier/notice?city=818', 'enabled': True},
    # === 电信相关 ===
    'ct_eco': {'name': '中国电信政企生态合作统一开放平台', 'url': 'https://b.189.cn/cooperation#/home', 'enabled': True},
    'gpdi_bid': {'name': '广东省电信规划设计院电子招投标平台', 'url': 'https://bidding.gpdi.com/homepage/', 'enabled': True},
    # === 铁通/建设 ===
    'cmcc_tietong_js': {'name': '九翊供应商平台(中移铁通江苏)', 'url': 'http://183.134.62.137:7774/#/supplier-guide/purchase-business', 'enabled': True},
    # === 中通服 ===
    'chinaccsscm': {'name': '中通服供应链管理电子招标系统(链捷招)', 'url': 'https://zb.chinaccsscm.cn/', 'enabled': True},
    # === 政府采购平台 ===
    'ccgp_gd': {'name': '广东省政府采购网', 'url': 'https://gdgpo.czt.gd.gov.cn/', 'enabled': True},
    'ccgp_bj': {'name': '北京市政府采购电子交易平台', 'url': 'http://zbcg-bjzc.zhongcy.com/bjczj-portal-site/index.html#/home', 'enabled': True},
    'ccgp_bj_jinghua': {'name': '北京市政府采购电子卖场(京华云采)', 'url': 'https://www.zhongcy.com', 'enabled': True},
    'ccgp_gx': {'name': '广西政府采购网', 'url': 'http://www.ccgp-guangxi.gov.cn/', 'enabled': True},
    'zycg_gov': {'name': '中央政府采购网', 'url': 'https://www.zycg.gov.cn/', 'enabled': True},
    'ggzy_shandong_qd': {'name': '全国公共资源交易平台(山东青岛)', 'url': 'https://ggzy.qingdao.gov.cn', 'enabled': True},
    'shenzhen_tech': {'name': '深圳市技术转移促进中心业务系统', 'url': 'http://szjssc.org.cn/fg/toFgIndexPage.do', 'enabled': True},
    # === 招标平台 ===
    'chengezhao': {'name': '诚E招标书购买', 'url': 'https://www.chengezhao.com/member/sysreg/register.htm?isAudit=1&no_sitemesh', 'enabled': True},
    '365trade': {'name': '中招联合电子招标采购平台', 'url': 'http://www.365trade.com.cn', 'enabled': True},
    'caie_xin': {'name': '易招电子招投标采购交易平台(甘肃)', 'url': 'http://www.caie.xin/login', 'enabled': True},
    'e_qyzc': {'name': '黔云招采电子招标采购交易平台', 'url': 'https://www.e-qyzc.com/#/home', 'enabled': True},
    'youezhao': {'name': '邮E招平台', 'url': 'https://www.youezhao.cn/', 'enabled': True},
    'shabidding': {'name': '上海国际招标有限公司', 'url': 'https://zb.shabidding.com/ebidding/#/ls/account?type=en', 'enabled': True},
    'gzebid': {'name': '广咨电子招投标交易平台', 'url': 'https://www.gzebid.cn/#/register', 'enabled': True},
    'gmeetc': {'name': '广东省机电设备招标中心交易平台2.0', 'url': 'http://gmeetc.gdebidding.com/ebidding/#/login', 'enabled': True},
    'ezhaobiao': {'name': '国信电网智能招投标系统', 'url': 'https://e-zhaobiao.com.cn/#/login', 'enabled': True},
    'easyjcx': {'name': '竞采星', 'url': 'https://login.easyjcx.com/#/su/register', 'enabled': True},
    'lecaiyun': {'name': '乐采云平台', 'url': 'https://www.lecaiyun.com/', 'enabled': True},
    'china_tender': {'name': '中国通用招标网电子招标投标平台', 'url': 'https://cgci.china-tender.com.cn/zjxm/', 'enabled': True},
    'wuhan_newarea': {'name': '武汉长江新区政府采购电子交易系统', 'url': 'http://47.111.115.168:9090/caizhaoyun/views/net/Login.html?loginType=02', 'enabled': True},
    'js_comm_build': {'name': '江苏省通信建设交易平台', 'url': 'http://47.96.125.164:8060/', 'enabled': True},
    # === 电力/能源 ===
    'sgcc_ecp': {'name': '国家电网电子商务平台-电工交易专区', 'url': 'https://sgccetp.com.cn/portal/#/', 'enabled': True},
    'espic_ebid': {'name': '国家电投电子商务平台', 'url': 'https://ebid.espic.com.cn', 'enabled': True},
    'cnaf': {'name': '中国航空油料集团', 'url': 'https://zc.cnaf.com/', 'enabled': True},
    'minmetals': {'name': '中国五矿集团供应链管理平台', 'url': 'https://ec.minmetals.com.cn/logonAction.do', 'enabled': True},
    # === 科技公司 ===
    'alibaba_supplier': {'name': '阿里巴巴集团供应商门户', 'url': 'https://csupplier.alibabacorp.com/supplier/pub/index.htm', 'enabled': True},
    'alibaba_mozi': {'name': '阿里巴巴厂商协同平台', 'url': 'https://mozi-login.alibaba-inc.com/', 'enabled': True},
    'aliyun_partner': {'name': '阿里云产品生态合作伙伴', 'url': 'https://partner.aliyun.com/neibu/productecologicalpartner', 'enabled': True},
    'baidu_cloud': {'name': '百度智能云', 'url': 'https://cloud.baidu.com', 'enabled': True},
    'baidu_supplier': {'name': '百度云供应商系统', 'url': 'https://caigou.baidu.com/login.jsp', 'enabled': True},
    'jd_eco': {'name': '京东科技生态合作平台', 'url': 'https://shengtai.jd.com', 'enabled': True},
    'kuaishou_supplier': {'name': '快手供应商后台', 'url': 'https://supplier.corp.kuaishou.com/homePage', 'enabled': True},
    'netease_supplier': {'name': '网易集团供应商系统', 'url': 'https://ebooking.n.netease.com/#/login', 'enabled': True},
    'huawei_partner': {'name': '华为企业合作伙伴', 'url': 'https://partner.huawei.com/#/cn/web/china', 'enabled': True},
    'zte_bid': {'name': '中兴通讯招标系统', 'url': 'https://bid.zte.com.cn/ebid/com/zte/product/ui/web/Application/default.aspx', 'enabled': True},
    'zte_supply': {'name': 'SCC中兴供应链协同', 'url': 'https://supply.zte.com.cn', 'enabled': True},
    'inspur_scs': {'name': '浪潮电子采购平台', 'url': 'https://scs.inspur.com/homepage', 'enabled': True},
    'inspur_cloud': {'name': '浪潮云数据中心合作伙伴', 'url': 'https://hub.ieisystem.com:8050/vendorlogin', 'enabled': True},
    'fiberhome_srm': {'name': '烽火超微SRM系统', 'url': 'https://srm.fiberhome.com/', 'enabled': True},
    'changhong_supplier': {'name': '长虹佳华企业账户', 'url': 'http://webapps.changhongit.cn:8202/supplier/home/#/login', 'enabled': True},
    'dcits_partner': {'name': '神州信息供应商门户', 'url': 'http://partner.dcits.com/portal/#/user/login', 'enabled': True},
    'wanmei': {'name': '完美世界股份有限公司', 'url': 'https://wanmei.going-link.com/app/public/home', 'enabled': True},
    'nezha_bid': {'name': '哪吒公司网上招报价系统', 'url': 'http://124.70.137.212:9090/nzbp/webui/inner/index_inner_2.0.jsp', 'enabled': True},
    # === 设计院 ===
    'hxdi_bid': {'name': '华信设计院电子招标平台', 'url': 'https://hxzhaobiao.hxdi.cn/', 'enabled': True},
    # === 高校/科研 ===
    'sjtu_supplier': {'name': '上海交通大学供应商平台', 'url': 'https://pboffice.sjtu.edu.cn/provider/#/', 'enabled': True},
    # === 算力平台 ===
    'gz_suanli': {'name': '贵州算力商城平台', 'url': 'https://www.gzsuanli.com/ticket', 'enabled': True},
    'nm_suanli': {'name': '和林格尔集群多云算力资源监测与调度平台', 'url': 'https://www.nmgsuanli.com/page/687924429644103680', 'enabled': True},
    # === 其他 ===
    'idinfo': {'name': '联连平台(汇信CA)', 'url': 'https://oauth.idinfo.cn/login.jsp', 'enabled': True},
    'yibanquan': {'name': '电子版权认证联合服务平台', 'url': 'https://www.yibanquan.com.cn/index.at', 'enabled': True},
    'smartcert': {'name': '江苏智慧数字认证有限公司', 'url': 'https://online.smartcert.cn/#/user/register', 'enabled': True},
    'csair_supplier': {'name': '中国南方航空招标采购网', 'url': 'https://supplier.csair.cn/bmv6_supplier/eip/logon/index_supplier.html', 'enabled': True},
    'shangyan_partner': {'name': '上研院合作伙伴门户', 'url': 'https://117.135.164.28:5111', 'enabled': True},
}
COMPETITOR_SOURCES = {
    '36kr': {'name': '36氪', 'url': 'https://36kr.com', 'enabled': True},
    'ithome': {'name': 'IT之家', 'url': 'https://www.ithome.com', 'enabled': True},
    'tmtpost': {'name': '钛媒体', 'url': 'https://www.tmtpost.com', 'enabled': True},
    'leiphone': {'name': '雷锋网', 'url': 'https://www.leiphone.com', 'enabled': True},
    'oschina': {'name': '开源中国', 'url': 'https://www.oschina.net', 'enabled': True},
    'infoq': {'name': 'InfoQ中文', 'url': 'https://www.infoq.cn', 'enabled': True},
}
HARDWARE_SOURCES = {
    'zol': {'name': '中关村在线', 'url': 'https://diy.zol.com.cn', 'enabled': True},
    'pconline': {'name': '太平洋电脑网', 'url': 'https://diy.pconline.com.cn', 'enabled': True},
    'mydrivers': {'name': '快科技', 'url': 'https://www.mydrivers.com', 'enabled': True},
    'ithome_hw': {'name': 'IT之家硬件', 'url': 'https://www.ithome.com', 'enabled': True},
}

@dataclass
class Config:
    # 邮件配置
    operator_email: str = os.getenv('OPERATOR_EMAIL', 'cherish.li@cloudsky.com')
    market_email: str = os.getenv('MARKET_EMAIL', 'cherish.li@cloudsky.com')

    # 爬虫配置
    operator_keywords: tuple = _parse_list(os.getenv('OPERATOR_KEYWORDS', ''), ('算力', 'GPU'))
    competitors: tuple = _parse_list(os.getenv('COMPETITORS', ''), ('海马云', '蔚领时代', '瑞云渲染', '智谱', '实在智能', '顺网', '云更新', '庭宇科技', '锐捷网络'))
    hardware_keywords: tuple = _parse_list(os.getenv('HARDWARE_KEYWORDS', ''), ('GPU', 'CPU', '内存', '硬盘', '网卡'))

    # 爬取渠道配置（可动态开关）
    operator_sources: dict = field(default_factory=lambda: copy.deepcopy(OPERATOR_SOURCES))
    competitor_sources: dict = field(default_factory=lambda: copy.deepcopy(COMPETITOR_SOURCES))
    hardware_sources: dict = field(default_factory=lambda: copy.deepcopy(HARDWARE_SOURCES))

    # 日志配置
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    log_file: str = os.getenv('LOG_FILE', 'app.log')

    # 运营商网站URL
    operator_urls: list = (
        "http://www.chinamobile.com",
        "http://www.chinatelecom.com.cn",
        "http://www.chinaunicom.com.cn"
    )

    # SMTP配置
    smtp_server: str = os.getenv('SMTP_SERVER', 'smtp.cloudsky.com')
    smtp_port: int = int(os.getenv('SMTP_PORT', '587'))
    smtp_username: str = os.getenv('SMTP_USERNAME', 'auto-reporter@cloudsky.com')
    smtp_password: str = os.getenv('SMTP_PASSWORD', 'your_password_here')

    database_path: str = os.getenv('DATABASE_PATH', 'data/history.db')
    crawl_timeout: int = int(os.getenv('CRAWL_TIMEOUT', '10'))
    crawl_retry: int = int(os.getenv('CRAWL_RETRY', '3'))

    def to_dict(self):
        return {
            'operator_email': self.operator_email,
            'market_email': self.market_email,
            'operator_keywords': list(self.operator_keywords),
            'competitors': list(self.competitors),
            'hardware_keywords': list(self.hardware_keywords),
            'log_level': self.log_level,
            'smtp_server': self.smtp_server,
            'smtp_port': self.smtp_port,
            'smtp_username': self.smtp_username,
            'smtp_password': '******' if self.smtp_password else '',
            'crawl_timeout': self.crawl_timeout,
            'crawl_retry': self.crawl_retry,
            'operator_sources': self.operator_sources,
            'competitor_sources': self.competitor_sources,
            'hardware_sources': self.hardware_sources,
        }

    def update_from_dict(self, data):
        if 'operator_email' in data:
            self.operator_email = data['operator_email']
        if 'market_email' in data:
            self.market_email = data['market_email']
        if 'smtp_server' in data:
            self.smtp_server = data['smtp_server']
        if 'smtp_port' in data:
            self.smtp_port = int(data['smtp_port'])
        if 'smtp_username' in data:
            self.smtp_username = data['smtp_username']
        if 'smtp_password' in data and data['smtp_password'] != '******':
            self.smtp_password = data['smtp_password']
        if 'operator_keywords' in data:
            self.operator_keywords = tuple(data['operator_keywords'])
        if 'competitors' in data:
            self.competitors = tuple(data['competitors'])
        if 'hardware_keywords' in data:
            self.hardware_keywords = tuple(data['hardware_keywords'])
        if 'crawl_timeout' in data:
            self.crawl_timeout = int(data['crawl_timeout'])
        if 'crawl_retry' in data:
            self.crawl_retry = int(data['crawl_retry'])
        if 'operator_sources' in data:
            for key, val in data['operator_sources'].items():
                if key in self.operator_sources and isinstance(self.operator_sources[key], dict):
                    self.operator_sources[key]['enabled'] = val.get('enabled', True)
                else:
                    self.operator_sources[key] = val
        if 'competitor_sources' in data:
            for key, val in data['competitor_sources'].items():
                if key in self.competitor_sources and isinstance(self.competitor_sources[key], dict):
                    self.competitor_sources[key]['enabled'] = val.get('enabled', True)
                else:
                    self.competitor_sources[key] = val
        if 'hardware_sources' in data:
            for key, val in data['hardware_sources'].items():
                if key in self.hardware_sources and isinstance(self.hardware_sources[key], dict):
                    self.hardware_sources[key]['enabled'] = val.get('enabled', True)
                else:
                    self.hardware_sources[key] = val

    def save(self):
        """将当前配置持久化到JSON文件"""
        import json
        config_file = os.path.join(BASE_DIR, 'data', 'custom_config.json')
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        data = {
            'operator_sources': self.operator_sources,
            'competitor_sources': self.competitor_sources,
            'hardware_sources': self.hardware_sources,
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_custom(self):
        """从JSON文件加载自定义配置"""
        import json
        config_file = os.path.join(BASE_DIR, 'data', 'custom_config.json')
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.update_from_dict(data)
            except Exception:
                pass
