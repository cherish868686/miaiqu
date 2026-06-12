import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config
import logging
from typing import List, Dict
from datetime import datetime

class EmailSender:
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def send_operator_report(self, data: List[Dict]):
        """发送运营商招标报告"""
        subject = f"运营商招标日报 - {datetime.now().strftime('%Y-%m-%d')}"
        html = self._generate_operator_html(data)
        self._send_email(self.config.operator_email, subject, html)
        
    def send_market_report(self, data: Dict[str, List[Dict]]):
        """发送市场动态报告"""
        subject = f"市场动态日报 - {datetime.now().strftime('%Y-%m-%d')}"
        html = self._generate_market_html(data)
        self._send_email(self.config.market_email, subject, html)
        
    def send_test_email(self):
        """发送测试邮件"""
        subject = f"密信本系统测试邮件 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        html = self._generate_test_html()
        self._send_email(self.config.operator_email, subject, html)

    def _send_email(self, to: str, subject: str, html: str):
        """发送邮件核心方法"""
        msg = MIMEMultipart()
        msg['From'] = self.config.smtp_username
        msg['To'] = to
        msg['Subject'] = subject
        
        msg.attach(MIMEText(html, 'html', 'utf-8'))
        
        try:
            if self.config.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.config.smtp_server, self.config.smtp_port, timeout=30)
                server.ehlo()
            else:
                server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port, timeout=30)
                server.ehlo()
                server.starttls()
                server.ehlo()
            if self.config.smtp_password and self.config.smtp_password not in ("your_password_here", "", "******"):
                server.login(self.config.smtp_username, self.config.smtp_password)
                self.logger.info(f"SMTP认证成功: {self.config.smtp_username}")
            else:
                self.logger.warning("SMTP密码未配置，尝试无认证发送...")
            server.send_message(msg)
            server.quit()
            self.logger.info(f"邮件发送成功: {subject}")
        except smtplib.SMTPAuthenticationError as e:
            self.logger.error(f"SMTP认证失败: {str(e)}")
            raise Exception(f"SMTP认证失败，请检查用户名和密码是否正确: {str(e)}")
        except smtplib.SMTPException as e:
            self.logger.error(f"SMTP发送失败: {str(e)}")
            raise Exception(f"邮件发送失败: {str(e)}")
        except Exception as e:
            self.logger.error(f"邮件发送异常: {str(e)}")
            raise Exception(f"邮件发送异常: {str(e)}")
            
    def _generate_operator_html(self, data: List[Dict]) -> str:
        """生成运营商报告HTML"""
        rows = ""
        if data:
            for item in data:
                title = item.get('title', '未知标题')
                url = item.get('url', '#')
                date = item.get('date', '未知日期')
                source = item.get('source', '未知来源')
                summary = item.get('summary', '')
                keyword = item.get('keyword', '')
                rows += f"""
                <tr>
                    <td style="padding:10px;border:1px solid #ddd;">{date}</td>
                    <td style="padding:10px;border:1px solid #ddd;"><a href="{url}">{title}</a></td>
                    <td style="padding:10px;border:1px solid #ddd;">{source}</td>
                    <td style="padding:10px;border:1px solid #ddd;"><span style="background:#e3f2fd;color:#1565c0;padding:2px 8px;border-radius:4px;">{keyword}</span></td>
                    <td style="padding:10px;border:1px solid #ddd;">{summary}</td>
                </tr>"""
        else:
            rows = '<tr><td colspan="5" style="padding:20px;text-align:center;color:#999;">今日暂无相关招标信息</td></tr>'

        return f"""<html>
<body style="font-family:'Microsoft YaHei',Arial,sans-serif;margin:0;padding:20px;background:#f5f5f5;">
    <div style="max-width:900px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,0.1);">
        <div style="background:linear-gradient(135deg,#1a237e,#283593);color:#fff;padding:20px 30px;">
            <h1 style="margin:0;font-size:22px;">📡 运营商招标日报</h1>
            <p style="margin:5px 0 0;font-size:14px;opacity:0.8;">{datetime.now().strftime('%Y年%m月%d日')}</p>
        </div>
        <div style="padding:20px;">
            <table style="width:100%;border-collapse:collapse;">
                <thead>
                    <tr style="background:#f5f5f5;">
                        <th style="padding:10px;border:1px solid #ddd;text-align:left;">日期</th>
                        <th style="padding:10px;border:1px solid #ddd;text-align:left;">标题</th>
                        <th style="padding:10px;border:1px solid #ddd;text-align:left;">来源</th>
                        <th style="padding:10px;border:1px solid #ddd;text-align:left;">关键词</th>
                        <th style="padding:10px;border:1px solid #ddd;text-align:left;">摘要</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
        <div style="padding:15px 30px;background:#fafafa;color:#999;font-size:12px;text-align:center;">
            密信本自动报告系统 | 本邮件由系统自动发送，请勿回复
        </div>
    </div>
</body>
</html>"""
        
    def _generate_market_html(self, data: Dict[str, List[Dict]]) -> str:
        """生成市场报告HTML"""
        competitor_rows = ""
        competitors = data.get('competitors', [])
        if competitors:
            for item in competitors:
                name = item.get('name', '未知')
                title = item.get('title', '未知标题')
                url = item.get('url', '#')
                date = item.get('date', '未知日期')
                summary = item.get('summary', '')
                competitor_rows += f"""
                <tr>
                    <td style="padding:10px;border:1px solid #ddd;"><span style="background:#fce4ec;color:#c62828;padding:2px 8px;border-radius:4px;">{name}</span></td>
                    <td style="padding:10px;border:1px solid #ddd;"><a href="{url}">{title}</a></td>
                    <td style="padding:10px;border:1px solid #ddd;">{date}</td>
                    <td style="padding:10px;border:1px solid #ddd;">{summary}</td>
                </tr>"""
        else:
            competitor_rows = '<tr><td colspan="4" style="padding:20px;text-align:center;color:#999;">今日暂无友商动态</td></tr>'

        hardware_rows = ""
        hardware = data.get('hardware', [])
        if hardware:
            for item in hardware:
                name = item.get('name', '未知')
                category = item.get('category', '未知')
                price = item.get('price', '未知')
                trend = item.get('trend', '持平')
                trend_color = '#4caf50' if '涨' in trend else '#f44336' if '降' in trend else '#ff9800'
                hardware_rows += f"""
                <tr>
                    <td style="padding:10px;border:1px solid #ddd;">{name}</td>
                    <td style="padding:10px;border:1px solid #ddd;">{category}</td>
                    <td style="padding:10px;border:1px solid #ddd;">{price}</td>
                    <td style="padding:10px;border:1px solid #ddd;"><span style="color:{trend_color};font-weight:bold;">{trend}</span></td>
                </tr>"""
        else:
            hardware_rows = '<tr><td colspan="4" style="padding:20px;text-align:center;color:#999;">今日暂无硬件市场动态</td></tr>'

        return f"""<html>
<body style="font-family:'Microsoft YaHei',Arial,sans-serif;margin:0;padding:20px;background:#f5f5f5;">
    <div style="max-width:900px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,0.1);">
        <div style="background:linear-gradient(135deg,#004d40,#00695c);color:#fff;padding:20px 30px;">
            <h1 style="margin:0;font-size:22px;">📊 市场动态日报</h1>
            <p style="margin:5px 0 0;font-size:14px;opacity:0.8;">{datetime.now().strftime('%Y年%m月%d日')}</p>
        </div>
        <div style="padding:20px;">
            <h2 style="font-size:16px;color:#333;border-bottom:2px solid #004d40;padding-bottom:8px;">🏢 友商动态</h2>
            <table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
                <thead>
                    <tr style="background:#f5f5f5;">
                        <th style="padding:10px;border:1px solid #ddd;text-align:left;">友商</th>
                        <th style="padding:10px;border:1px solid #ddd;text-align:left;">标题</th>
                        <th style="padding:10px;border:1px solid #ddd;text-align:left;">日期</th>
                        <th style="padding:10px;border:1px solid #ddd;text-align:left;">摘要</th>
                    </tr>
                </thead>
                <tbody>{competitor_rows}</tbody>
            </table>
            <h2 style="font-size:16px;color:#333;border-bottom:2px solid #004d40;padding-bottom:8px;">🖥️ 硬件市场</h2>
            <table style="width:100%;border-collapse:collapse;">
                <thead>
                    <tr style="background:#f5f5f5;">
                        <th style="padding:10px;border:1px solid #ddd;text-align:left;">名称</th>
                        <th style="padding:10px;border:1px solid #ddd;text-align:left;">类别</th>
                        <th style="padding:10px;border:1px solid #ddd;text-align:left;">价格</th>
                        <th style="padding:10px;border:1px solid #ddd;text-align:left;">趋势</th>
                    </tr>
                </thead>
                <tbody>{hardware_rows}</tbody>
            </table>
        </div>
        <div style="padding:15px 30px;background:#fafafa;color:#999;font-size:12px;text-align:center;">
            密信本自动报告系统 | 本邮件由系统自动发送，请勿回复
        </div>
    </div>
</body>
</html>"""

    def _generate_test_html(self) -> str:
        """生成测试邮件HTML"""
        return f"""<html>
<body style="font-family:'Microsoft YaHei',Arial,sans-serif;margin:0;padding:20px;background:#f5f5f5;">
    <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,0.1);">
        <div style="background:linear-gradient(135deg,#1565c0,#1976d2);color:#fff;padding:20px 30px;">
            <h1 style="margin:0;font-size:20px;">✅ 密信本系统测试</h1>
        </div>
        <div style="padding:30px;text-align:center;">
            <p style="font-size:16px;color:#333;">这是一封测试邮件，用于验证邮件发送功能是否正常。</p>
            <p style="font-size:14px;color:#666;">发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <div style="margin-top:20px;padding:15px;background:#e8f5e9;border-radius:6px;color:#2e7d32;">
                ✓ 邮件发送功能运行正常
            </div>
        </div>
        <div style="padding:15px 30px;background:#fafafa;color:#999;font-size:12px;text-align:center;">
            密信本自动报告系统 | 本邮件由系统自动发送，请勿回复
        </div>
    </div>
</body>
</html>"""
