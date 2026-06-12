
import re

filepath = '/Users/lilingdeng/CodeGeeXProjects/miaiqu-ai-integrated/templates/index.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix user message bubble
old_user = 'background:var(--accent);color:#fff;padding:10px 14px;border-radius:12px 12px 2px 12px;font-size:14px;line-height:1.6;word-break:break-word'
new_user = 'background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:10px 14px;border-radius:12px 12px 2px 12px;font-size:14px;line-height:1.6;word-break:break-word;box-shadow:0 2px 8px rgba(102,126,234,.3)'
content = content.replace(old_user, new_user, 1)

# 2. Fix error message
old_error = 'background:rgba(248,81,73,.1);border:1px solid var(--danger);color:var(--danger);padding:10px 14px;border-radius:12px 12px 12px 2px;font-size:13px'
new_error = 'background:rgba(248,81,73,.15);border:1px solid #f85149;color:#ff6b6b;padding:10px 14px;border-radius:12px 12px 12px 2px;font-size:13px'
content = content.replace(old_error, new_error, 1)

# 3. Fix AI message model tag
old_model = 'font-size:10px;color:var(--text-sec);margin-top:4px'
new_model = 'font-size:10px;color:#64ffda;margin-top:6px;opacity:.7'
content = content.replace(old_model, new_model, 1)

# 4. Fix AI message bubble
old_ai = 'background:var(--bg-dark);border:1px solid var(--border);padding:10px 14px;border-radius:12px 12px 12px 2px;font-size:14px;line-height:1.6;word-break:break-word'
new_ai = 'background:#16213e;border:1px solid #2a2a4a;padding:12px 16px;border-radius:12px 12px 12px 2px;font-size:14px;line-height:1.8;word-break:break-word;color:#e6f1ff;box-shadow:0 2px 8px rgba(0,0,0,.2)'
content = content.replace(old_ai, new_ai, 1)

# 5. Fix clearAIChat welcome message colors
old_welcome = "color:var(--text-sec)\"><i class=\"bi bi-robot\" style=\"font-size:48px;display:block;margin-bottom:12px;color:var(--accent2);opacity:.5\">"
new_welcome = "color:#8892b0\"><i class=\"bi bi-robot\" style=\"font-size:48px;display:block;margin-bottom:12px;color:#64ffda;opacity:.6\">"
content = content.replace(old_welcome, new_welcome, 1)

old_welcome2 = 'color:var(--text-pri)">AI助手已就绪'
new_welcome2 = 'color:#ccd6f6">AI助手已就绪'
content = content.replace(old_welcome2, new_welcome2, 1)

old_welcome3 = '<b id=\"aiModeLabel\">AI+搜索</b>'
new_welcome3 = '<b id=\"aiModeLabel\" style=\"color:#64ffda\">AI+搜索</b>'
content = content.replace(old_welcome3, new_welcome3, 1)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Done - all replacements made')
