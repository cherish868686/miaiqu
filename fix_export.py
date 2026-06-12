
filepath = '/Users/lilingdeng/CodeGeeXProjects/miaiqu-ai-integrated/templates/index.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix clearAIChat welcome message colors
old_clear_welcome = "当前模式：<b id=\"aiModeLabel\">' + (_aiChatMode === 'search' ? 'AI+搜索' : 'AI') + '</b>"
new_clear_welcome = "当前模式：<b id=\"aiModeLabel\" style=\"color:#64ffda\">' + (_aiChatMode === 'search' ? 'AI+搜索' : 'AI') + '</b>"
content = content.replace(old_clear_welcome, new_clear_welcome, 1)

# Add exportAIChatDoc function after clearAIChat
old_block = """    function renderSources(containerId, sources, type) {"""

new_block = """    async function exportAIChatDoc(fmt) {
        if (!_aiChatHistory || _aiChatHistory.length === 0) {
            showToast('没有可导出的对话内容', 'warning');
            return;
        }
        var content = '';
        var title = 'AI对话记录_' + new Date().toLocaleDateString('zh-CN').replace(/\//g, '-');
        for (var i = 0; i < _aiChatHistory.length; i++) {
            var msg = _aiChatHistory[i];
            if (msg.role === 'user') {
                content += '【用户】\n' + msg.content + '\n\n';
            } else if (msg.role === 'assistant') {
                content += '【AI助手】\n' + msg.content + '\n\n';
            }
        }
        try {
            var resp = await fetch('/api/ai/export-doc', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({title: title, content: content, format: fmt})
            });
            if (!resp.ok) throw new Error('导出失败');
            var blob = await resp.blob();
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = title + '.' + fmt;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            showToast('文档导出成功', 'success');
        } catch (e) {
            var textContent = content;
            var blob = new Blob([textContent], {type: 'text/plain;charset=utf-8'});
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = title + '.txt';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            showToast('已导出为文本格式', 'info');
        }
    }

    function renderSources(containerId, sources, type) {"""

content = content.replace(old_block, new_block, 1)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Done - exportAIChatDoc added')
