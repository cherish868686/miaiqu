# 新城小米虾 - 集成密信本智能信息监控系统

## 简介
新城小米虾是集成了密信本核心能力的智能办公平台，主要功能包括：

### 核心功能
- 🏠 **智能首页** - 一站式办公入口，快速访问所有功能
- 🛡️ **密信本** - 智能信息监控系统
  - 📡 运营商招标信息爬取和报告
  - 🏢 友商动态监控
  - 🖥️ 硬件市场行情追踪
  - 📧 自动邮件报告发送
  - ⏰ 定时任务调度
- 📝 **文档校对** - 多格式文档比对校对
  - 支持 PDF/Word/Excel/PPT/图片 格式
  - 文本差异对比
  - 表格差异对比
  - 生成带标注的Word文档

## 技术栈
- **后端**: Python 3.9 + Flask
- **前端**: Bootstrap 5 + Bootstrap Icons
- **数据库**: SQLite
- **爬虫**: Requests + BeautifulSoup4
- **调度**: APScheduler
- **配置**: python-dotenv

## 快速开始

### 1. 安装依赖
```bash
cd miaiqu-ai-integrated
pip3 install -r requirements.txt
```

### 2. 配置环境变量
```bash
# 已有默认 .env 文件，按需修改SMTP等配置
```

### 3. 启动应用
```bash
python3 app.py
```

访问 http://localhost:5001 即可使用。

### 4. 使用 pm2 持久运行
```bash
pm2 start "python3 app.py" --name miaiqu-ai
pm2 save
```

## 页面导航
| 页面 | 路径 | 说明 |
|------|------|------|
| 首页 | / | 新城小米虾主界面，集成所有功能入口 |
| 密信本 | 侧边栏切换 | 信息监控中心 |
| 文档校对 | 侧边栏切换 | 文档比对校对 |
| 运营商招标 | 侧边栏切换 | 招标信息管理 |
| 友商动态 | 侧边栏切换 | 竞争对手监控 |
| 硬件市场 | 侧边栏切换 | 硬件行情追踪 |
| 系统配置 | 侧边栏切换 | 邮件/爬虫/渠道配置 |

## 项目结构
```
miaiqu-ai-integrated/
├── app.py              # Flask主应用（集成入口）
├── config.py           # 配置管理
├── crawlers.py         # 爬虫模块
├── database.py         # 数据库模块
├── email_sender.py     # 邮件发送模块
├── scheduler.py        # 定时任务调度
├── api_routes.py       # URL检测与渠道管理API
├── .env                # 环境变量配置
├── requirements.txt    # Python依赖
├── data/               # 数据存储
│   ├── history.db      # SQLite数据库
│   └── custom_config.json
├── doc_proofread/      # 文档校对模块
│   ├── routes.py       # 校对API路由
│   ├── parsers/        # 文档解析器
│   └── comparator/     # 差异比较器
├── static/             # 静态资源
│   └── proofread.js    # 校对前端JS
└── templates/          # HTML模板
    └── index.html      # 主页面（集成所有功能）
```

## 与原密信本的区别
1. **统一入口**: 新城小米虾首页集成密信本所有功能，无需切换系统
2. **密信本页面**: 保留密信本完整的信息监控仪表盘
3. **文档校对**: 直接集成在侧边栏中，无需单独页面
4. **品牌统一**: 所有页面统一使用"新城小米虾"品牌

## 注意事项
- macOS 的 AirPlay 服务默认占用 5000 端口，本系统使用 5001 端口
- SMTP密码等敏感信息请通过 .env 文件配置，不要硬编码
- 爬虫请求已添加超时和重试机制，默认超时10秒，重试3次
