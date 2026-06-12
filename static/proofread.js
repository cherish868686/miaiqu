/**
 * 文档校对功能 JavaScript
 * 区分原文本和校对文本，差异在原文本上标注
 */
var proofreadOriginalFile = null;
var proofreadProofreadFile = null;

function switchProofreadTab(tab) {
    var compareBtn = document.getElementById('proofread-tab-compare');
    var historyBtn = document.getElementById('proofread-tab-history');
    var compareSection = document.getElementById('proofread-compare-section');
    var historySection = document.getElementById('proofread-history-section');
    if (tab === 'compare') {
        compareBtn.className = 'btn-accent';
        historyBtn.className = 'btn-outline';
        compareSection.style.display = 'block';
        historySection.style.display = 'none';
    } else {
        compareBtn.className = 'btn-outline';
        historyBtn.className = 'btn-accent';
        compareSection.style.display = 'none';
        historySection.style.display = 'block';
        proofreadLoadHistory();
    }
}

// ==================== 文件上传 ====================
var proofreadAllowedExts = ['pdf', 'docx', 'doc', 'xlsx', 'xls', 'pptx', 'ppt', 'jpg', 'jpeg', 'png'];

function proofreadValidateFile(file) {
    var ext = file.name.split('.').pop().toLowerCase();
    if (proofreadAllowedExts.indexOf(ext) === -1) {
        showToast('不支持的文件格式: ' + file.name, 'error');
        return false;
    }
    return true;
}

function proofreadHandleDropOriginal(e) {
    e.preventDefault();
    e.currentTarget.style.borderColor = 'var(--border)';
    e.currentTarget.style.background = 'rgba(0,191,165,.02)';
    var files = Array.from(e.dataTransfer.files);
    if (files.length > 0) proofreadUploadOriginal(files[0]);
}

function proofreadHandleOriginalSelect(e) {
    var files = Array.from(e.target.files);
    if (files.length > 0) proofreadUploadOriginal(files[0]);
    e.target.value = '';
}

function proofreadHandleDropProofread(e) {
    e.preventDefault();
    e.currentTarget.style.borderColor = 'var(--border)';
    e.currentTarget.style.background = 'rgba(0,191,165,.02)';
    var files = Array.from(e.dataTransfer.files);
    if (files.length > 0) proofreadUploadProofread(files[0]);
}

function proofreadHandleProofreadSelect(e) {
    var files = Array.from(e.target.files);
    if (files.length > 0) proofreadUploadProofread(files[0]);
    e.target.value = '';
}

async function proofreadUploadOriginal(file) {
    if (!proofreadValidateFile(file)) return;
    showToast('正在上传原文本...', 'info');
    try {
        var formData = new FormData();
        formData.append('files', file);
        formData.append('role', 'original');
        var resp = await fetch('/api/proofread/upload', { method: 'POST', body: formData });
        var data = await resp.json();
        if (data.status !== 'success') { showToast(data.message || '上传失败', 'error'); return; }
        proofreadOriginalFile = data.files[0];
        proofreadOriginalFile.role = 'original';
        proofreadRenderOriginalPreview();
        proofreadUpdateCompareBtn();
        showToast('原文本上传成功', 'success');
    } catch (err) {
        showToast('上传失败: ' + err.message, 'error');
    }
}

async function proofreadUploadProofread(file) {
    if (!proofreadValidateFile(file)) return;
    showToast('正在上传校对文本...', 'info');
    try {
        var formData = new FormData();
        formData.append('files', file);
        formData.append('role', 'proofread');
        var resp = await fetch('/api/proofread/upload', { method: 'POST', body: formData });
        var data = await resp.json();
        if (data.status !== 'success') { showToast(data.message || '上传失败', 'error'); return; }
        proofreadProofreadFile = data.files[0];
        proofreadProofreadFile.role = 'proofread';
        proofreadRenderProofreadPreview();
        proofreadUpdateCompareBtn();
        showToast('校对文本上传成功', 'success');
    } catch (err) {
        showToast('上传失败: ' + err.message, 'error');
    }
}

function proofreadGetFileIcon(fileType) {
    var icons = { pdf: 'bi-file-pdf', word: 'bi-file-word', excel: 'bi-file-excel', ppt: 'bi-file-ppt', image: 'bi-file-image' };
    return icons[fileType] || 'bi-file-earmark';
}

function proofreadGetFileColor(fileType) {
    var colors = { pdf: '#ef4444', word: '#3b82f6', excel: '#10b981', ppt: '#f59e0b', image: '#8b5cf6' };
    return colors[fileType] || 'var(--text-sec)';
}

function proofreadGetTypeName(fileType) {
    var names = { pdf: 'PDF', word: 'Word', excel: 'Excel', ppt: 'PPT', image: '图片' };
    return names[fileType] || '未知';
}

function proofreadRenderOriginalPreview() {
    var preview = document.getElementById('proofreadOriginalPreview');
    var placeholder = document.getElementById('proofreadOriginalPlaceholder');
    if (!proofreadOriginalFile) {
        preview.style.display = 'none';
        placeholder.style.display = 'block';
        return;
    }
    placeholder.style.display = 'none';
    preview.style.display = 'flex';
    preview.innerHTML = '<div style="display:flex;align-items:center;gap:10px;padding:8px 12px;background:var(--bg-card);border:1px solid var(--accent);border-radius:8px;width:100%">'
        + '<i class="bi ' + proofreadGetFileIcon(proofreadOriginalFile.file_type) + '" style="font-size:24px;color:' + proofreadGetFileColor(proofreadOriginalFile.file_type) + '"></i>'
        + '<div style="flex:1;min-width:0;text-align:left">'
        + '<div style="font-size:12px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + proofreadEscapeHtml(proofreadOriginalFile.original_name) + '</div>'
        + '<div style="font-size:10px;color:var(--accent)">' + proofreadGetTypeName(proofreadOriginalFile.file_type) + ' · 原文本</div>'
        + '</div>'
        + '<button onclick="event.stopPropagation();proofreadRemoveOriginal()" style="background:none;border:none;color:var(--text-sec);cursor:pointer;font-size:14px" title="移除"><i class="bi bi-x-lg"></i></button>'
        + '</div>';
}

function proofreadRenderProofreadPreview() {
    var preview = document.getElementById('proofreadProofreadPreview');
    var placeholder = document.getElementById('proofreadProofreadPlaceholder');
    if (!proofreadProofreadFile) {
        preview.style.display = 'none';
        placeholder.style.display = 'block';
        return;
    }
    placeholder.style.display = 'none';
    preview.style.display = 'flex';
    preview.innerHTML = '<div style="display:flex;align-items:center;gap:10px;padding:8px 12px;background:var(--bg-card);border:1px solid var(--warning);border-radius:8px;width:100%">'
        + '<i class="bi ' + proofreadGetFileIcon(proofreadProofreadFile.file_type) + '" style="font-size:24px;color:' + proofreadGetFileColor(proofreadProofreadFile.file_type) + '"></i>'
        + '<div style="flex:1;min-width:0;text-align:left">'
        + '<div style="font-size:12px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + proofreadEscapeHtml(proofreadProofreadFile.original_name) + '</div>'
        + '<div style="font-size:10px;color:var(--warning)">' + proofreadGetTypeName(proofreadProofreadFile.file_type) + ' · 校对文本</div>'
        + '</div>'
        + '<button onclick="event.stopPropagation();proofreadRemoveProofread()" style="background:none;border:none;color:var(--text-sec);cursor:pointer;font-size:14px" title="移除"><i class="bi bi-x-lg"></i></button>'
        + '</div>';
}

function proofreadRemoveOriginal() {
    proofreadOriginalFile = null;
    proofreadRenderOriginalPreview();
    proofreadUpdateCompareBtn();
}

function proofreadRemoveProofread() {
    proofreadProofreadFile = null;
    proofreadRenderProofreadPreview();
    proofreadUpdateCompareBtn();
}

function proofreadClearFiles() {
    proofreadOriginalFile = null;
    proofreadProofreadFile = null;
    proofreadRenderOriginalPreview();
    proofreadRenderProofreadPreview();
    proofreadUpdateCompareBtn();
}

function proofreadUpdateCompareBtn() {
    var actions = document.getElementById('proofreadUploadActions');
    var btn = document.getElementById('proofreadCompareBtn');
    var ready = proofreadOriginalFile && proofreadProofreadFile;
    actions.style.display = (proofreadOriginalFile || proofreadProofreadFile) ? 'flex' : 'none';
    actions.style.justifyContent = 'space-between';
    actions.style.alignItems = 'center';
    btn.disabled = !ready;
}

// ==================== 比对 ====================
async function proofreadStartCompare() {
    if (!proofreadOriginalFile || !proofreadProofreadFile) {
        showToast('请分别上传原文本和校对文本', 'error');
        return;
    }
    document.getElementById('proofread-upload-area').style.display = 'none';
    document.getElementById('proofread-progress').style.display = 'block';
    document.getElementById('proofread-result').style.display = 'none';

    var progressBar = document.getElementById('proofreadProgressBar');
    var progressText = document.getElementById('proofreadProgressText');
    var progress = 0;
    var progressInterval = setInterval(function () {
        progress = Math.min(progress + Math.random() * 15, 90);
        progressBar.style.width = progress + '%';
    }, 500);
    var steps = ['解析原文本...', '解析校对文本...', '提取文本内容...', '提取表格数据...', '执行文本比对...', '执行表格比对...', '生成比对报告...'];
    var stepIdx = 0;
    var stepInterval = setInterval(function () {
        if (stepIdx < steps.length) { progressText.textContent = steps[stepIdx]; stepIdx++; }
    }, 800);

    try {
        var resp = await fetch('/api/proofread/compare', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                original: proofreadOriginalFile,
                proofread: proofreadProofreadFile
            })
        });
        var data = await resp.json();
        clearInterval(progressInterval);
        clearInterval(stepInterval);
        progressBar.style.width = '100%';
        if (data.status !== 'success') throw new Error(data.message || '比对失败');
        setTimeout(function () {
            document.getElementById('proofread-progress').style.display = 'none';
            proofreadRenderResults(data.results, data.history_id, data.original_file_id);
            showToast('比对完成！', 'success');
        }, 500);
    } catch (err) {
        clearInterval(progressInterval);
        clearInterval(stepInterval);
        showToast('比对失败: ' + err.message, 'error');
        document.getElementById('proofread-progress').style.display = 'none';
        document.getElementById('proofread-upload-area').style.display = 'block';
    }
}

function proofreadBackToUpload() {
    document.getElementById('proofread-upload-area').style.display = 'block';
    document.getElementById('proofread-progress').style.display = 'none';
    document.getElementById('proofread-result').style.display = 'none';
}

function proofreadEscapeHtml(text) {
    if (!text) return '';
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==================== 下载标注文档 ====================
function proofreadDownloadAnnotated(historyId) {
    window.open('/api/proofread/download-annotated/' + historyId, '_blank');
}

// ==================== 渲染结果：差异在原文本上标注 ====================
function proofreadRenderResults(results, historyId, originalFileId) {
    var section = document.getElementById('proofread-result');
    section.style.display = 'block';
    var html = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:8px">';
    html += '<button class="btn-outline" onclick="proofreadBackToUpload()"><i class="bi bi-arrow-left"></i> 重新比对</button>';
    html += '<div style="display:flex;gap:8px;align-items:center">';
    if (originalFileId) {
        html += '<button class="btn-accent" onclick="proofreadDownloadAnnotated(\'' + historyId + '\')"><i class="bi bi-download"></i> 下载标注文档</button>';
    }
    html += '<span class="badge-kw" style="font-size:11px"><i class="bi bi-fingerprint"></i> ' + (historyId || '').substring(0, 8) + '</span>';
    html += '</div></div>';

    for (var c = 0; c < results.length; c++) {
        var comp = results[c];
        var summary = comp.summary;
        var isConsistent = summary.overall_status === '一致';

        html += '<div class="card" style="margin-bottom:16px">';
        html += '<div class="card-header"><span>';
        html += '<span class="badge-kw" style="background:rgba(0,191,165,.15);color:var(--accent)"><i class="bi bi-file-earmark-text"></i> ' + proofreadEscapeHtml(comp.doc_a) + '</span>';
        html += ' <i class="bi bi-arrow-right" style="color:var(--warning);margin:0 6px"></i> ';
        html += '<span class="badge-kw" style="background:rgba(210,153,34,.15);color:var(--warning)"><i class="bi bi-pencil-square"></i> ' + proofreadEscapeHtml(comp.doc_b) + '</span>';
        html += '</span>';
        html += '<span style="color:' + (isConsistent ? 'var(--success)' : 'var(--danger)') + ';font-weight:600;font-size:13px"><i class="bi bi-' + (isConsistent ? 'check-circle' : 'exclamation-triangle') + '"></i> ' + (isConsistent ? '内容一致' : '存在差异') + '</span>';
        html += '</div>';
        html += '<div class="card-body">';

        // 摘要统计
        html += '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:16px">';
        html += '<div style="text-align:center;padding:12px;background:var(--bg-dark);border-radius:8px"><div style="font-size:22px;font-weight:700;color:var(--accent)">' + (summary.total_text_differences || 0) + '</div><div style="font-size:11px;color:var(--text-sec)">文本差异</div></div>';
        html += '<div style="text-align:center;padding:12px;background:var(--bg-dark);border-radius:8px"><div style="font-size:22px;font-weight:700;color:var(--warning)">' + (summary.total_table_differences || 0) + '</div><div style="font-size:11px;color:var(--text-sec)">表格差异行</div></div>';
        html += '<div style="text-align:center;padding:12px;background:var(--bg-dark);border-radius:8px"><div style="font-size:22px;font-weight:700;color:var(--text-sec)">' + (summary.total_table_rows || 0) + '</div><div style="font-size:11px;color:var(--text-sec)">表格总行数</div></div>';
        html += '<div style="text-align:center;padding:12px;background:var(--bg-dark);border-radius:8px"><div style="font-size:22px;font-weight:700;color:var(--success)">' + (summary.consistent_table_rows || 0) + '</div><div style="font-size:11px;color:var(--text-sec)">一致行数</div></div>';
        html += '<div style="text-align:center;padding:12px;background:var(--bg-dark);border-radius:8px"><div style="font-size:22px;font-weight:700;color:' + (isConsistent ? 'var(--success)' : 'var(--danger)') + '">' + (isConsistent ? '✓' : '✗') + '</div><div style="font-size:11px;color:var(--text-sec)">整体状态</div></div>';
        html += '</div>';

        // 差异标注在原文本上
        if (comp.text_diff) html += proofreadRenderTextAnnotation(comp.text_diff, comp.doc_a, comp.doc_b);
        if (comp.table_diff) html += proofreadRenderTableDiff(comp.table_diff, comp.doc_a, comp.doc_b);
        if (!comp.text_diff && !comp.table_diff) {
            html += '<div style="text-align:center;padding:20px;color:var(--success)"><i class="bi bi-check2-all" style="font-size:28px;display:block;margin-bottom:6px"></i>两份文档内容完全一致</div>';
        }
        html += '</div></div>';
    }
    section.innerHTML = html;
}

// ==================== 文本差异：在原文本上标注 ====================
function proofreadRenderTextAnnotation(textDiff, docA, docB) {
    var html = '<div style="margin-bottom:16px">';
    html += '<h6 style="font-size:14px;font-weight:600;margin-bottom:8px"><i class="bi bi-highlighter" style="color:var(--accent);margin-right:6px"></i>差异标注 ';
    html += '<span style="font-size:11px;padding:2px 8px;border-radius:4px;' + (textDiff.difference_count > 0 ? 'background:rgba(248,81,73,.15);color:var(--danger)' : 'background:rgba(46,160,67,.15);color:var(--success)') + '">' + (textDiff.difference_count > 0 ? textDiff.difference_count + ' 处差异' : '无差异') + '</span></h6>';

    if (textDiff.difference_count === 0) {
        html += '<div style="padding:10px;background:var(--bg-dark);border-radius:6px;color:var(--success);font-size:12px"><i class="bi bi-check"></i> 文本内容完全一致</div>';
    } else {
        // 图例说明
        html += '<div style="display:flex;gap:16px;margin-bottom:10px;font-size:11px;color:var(--text-sec);padding:8px 12px;background:var(--bg-dark);border-radius:6px">';
        html += '<span><span style="display:inline-block;width:24px;height:10px;background:rgba(248,81,73,.25);border-radius:2px;vertical-align:middle;margin-right:4px"></span>删除内容</span>';
        html += '<span><span style="display:inline-block;width:24px;height:10px;background:rgba(46,160,67,.25);border-radius:2px;vertical-align:middle;margin-right:4px"></span>新增内容</span>';
        html += '<span><span style="display:inline-block;width:24px;height:10px;background:rgba(210,153,34,.25);border-radius:2px;vertical-align:middle;margin-right:4px"></span>修改内容</span>';
        html += '<span><i class="bi bi-chat-left-text" style="color:var(--warning);margin-right:4px"></i>校对说明</span>';
        html += '</div>';

        // 在原文本上逐行标注
        html += '<div style="border:1px solid var(--border);border-radius:8px;overflow:hidden">';

        // 构建差异行索引
        var diffLineMap = {};
        for (var d = 0; d < textDiff.differences.length; d++) {
            var diff = textDiff.differences[d];
            for (var k = 0; k < diff.details.length; k++) {
                var detail = diff.details[k];
                if (detail.line_a_index !== null && detail.line_a_index !== undefined) {
                    diffLineMap[detail.line_a_index] = { diff: diff, detail: detail, diffIdx: d };
                }
            }
        }

        // 渲染原文本全文，差异处标注
        var totalLines = textDiff.total_lines_a || 0;
        // 收集所有原文行
        var allLinesA = [];
        for (var d2 = 0; d2 < textDiff.differences.length; d2++) {
            var diff2 = textDiff.differences[d2];
            for (var k2 = 0; k2 < diff2.details.length; k2++) {
                var det2 = diff2.details[k2];
                if (det2.content_a && det2.line_a_index !== null && det2.line_a_index !== undefined) {
                    allLinesA.push({ index: det2.line_a_index, content: det2.content_a, diff: diff2, detail: det2 });
                }
            }
        }

        // 渲染差异区域
        for (var d3 = 0; d3 < textDiff.differences.length; d3++) {
            var diff3 = textDiff.differences[d3];

            for (var k3 = 0; k3 < diff3.details.length; k3++) {
                var detail3 = diff3.details[k3];
                var lineNum = detail3.line_a_index !== null && detail3.line_a_index !== undefined ? detail3.line_a_index + 1 : '-';

                html += '<div style="display:grid;grid-template-columns:50px 1fr;border-bottom:1px solid var(--border)">';

                // 行号
                html += '<div style="padding:8px 6px;text-align:right;font-family:monospace;font-size:11px;color:var(--text-sec);background:var(--bg-dark);border-right:1px solid var(--border)">' + lineNum + '</div>';

                // 内容区
                html += '<div style="padding:8px 12px">';

                if (diff3.type === 'delete') {
                    // 删除：原文本有，校对文本无
                    html += '<div style="background:rgba(248,81,73,.1);border-left:3px solid var(--danger);padding:4px 8px;border-radius:0 4px 4px 0;margin-bottom:4px">';
                    html += '<div style="font-size:12px;color:#fca5a5;text-decoration:line-through">' + proofreadEscapeHtml(detail3.content_a) + '</div>';
                    html += '</div>';
                    html += '<div style="font-size:11px;color:var(--danger);margin-top:2px"><i class="bi bi-dash-circle"></i> 删除</div>';
                } else if (diff3.type === 'replace') {
                    // 修改：原文本被修改
                    html += '<div style="background:rgba(210,153,34,.08);border-left:3px solid var(--warning);padding:4px 8px;border-radius:0 4px 4px 0;margin-bottom:4px">';
                    if (detail3.char_diff) {
                        html += '<div style="font-size:12px">' + proofreadRenderCharDiffAnnotated(detail3.char_diff) + '</div>';
                    } else {
                        html += '<div style="font-size:12px;color:#fcd34d">' + proofreadEscapeHtml(detail3.content_a) + '</div>';
                    }
                    html += '</div>';
                    // 校对说明
                    if (detail3.content_b) {
                        html += '<div style="background:rgba(46,160,67,.06);border-left:3px solid var(--success);padding:4px 8px;border-radius:0 4px 4px 0;margin-top:4px">';
                        html += '<div style="font-size:11px;color:var(--success)"><i class="bi bi-chat-left-text" style="margin-right:4px"></i>校对为：' + proofreadEscapeHtml(detail3.content_b) + '</div>';
                        html += '</div>';
                    }
                } else if (diff3.type === 'insert') {
                    // 新增：校对文本有，原文本无
                    html += '<div style="background:rgba(46,160,67,.08);border-left:3px solid var(--success);padding:4px 8px;border-radius:0 4px 4px 0">';
                    html += '<div style="font-size:11px;color:var(--success)"><i class="bi bi-plus-circle"></i> 新增：' + proofreadEscapeHtml(detail3.content_b) + '</div>';
                    html += '</div>';
                }

                html += '</div></div>';
            }
        }

        html += '</div>';
    }
    html += '</div>';
    return html;
}

function proofreadRenderCharDiffAnnotated(charDiffs) {
    var html = '';
    for (var i = 0; i < charDiffs.length; i++) {
        var cd = charDiffs[i];
        if (cd.type === 'equal') {
            html += proofreadEscapeHtml(cd.text_a || cd.text_b || '');
        } else if (cd.type === 'replace') {
            html += '<span style="background:rgba(248,81,73,.3);text-decoration:line-through;border-radius:2px;padding:0 1px" title="原文：' + proofreadEscapeHtml(cd.text_a) + '">' + proofreadEscapeHtml(cd.text_a) + '</span>';
            html += '<span style="background:rgba(46,160,67,.3);border-radius:2px;padding:0 1px" title="校对：' + proofreadEscapeHtml(cd.text_b) + '">' + proofreadEscapeHtml(cd.text_b) + '</span>';
        } else if (cd.type === 'delete') {
            html += '<span style="background:rgba(248,81,73,.3);text-decoration:line-through;border-radius:2px;padding:0 1px">' + proofreadEscapeHtml(cd.text_a) + '</span>';
        } else if (cd.type === 'insert') {
            html += '<span style="background:rgba(46,160,67,.3);border-radius:2px;padding:0 1px">' + proofreadEscapeHtml(cd.text_b) + '</span>';
        }
    }
    return html;
}

// ==================== 表格差异 ====================
function proofreadRenderTableDiff(tableDiff, docA, docB) {
    var html = '<div style="margin-bottom:16px">';
    html += '<h6 style="font-size:14px;font-weight:600;margin-bottom:8px"><i class="bi bi-table" style="color:var(--warning);margin-right:6px"></i>表格差异 ';
    html += '<span style="font-size:11px;padding:2px 8px;border-radius:4px;' + (tableDiff.total_inconsistent_rows > 0 ? 'background:rgba(248,81,73,.15);color:var(--danger)' : 'background:rgba(46,160,67,.15);color:var(--success)') + '">' + (tableDiff.total_inconsistent_rows > 0 ? tableDiff.total_inconsistent_rows + ' 行不一致' : '全部一致') + '</span></h6>';

    if (tableDiff.total_rows_compared === 0) {
        html += '<div style="padding:10px;background:var(--bg-dark);border-radius:6px;color:var(--text-sec);font-size:12px"><i class="bi bi-info-circle"></i> 未检测到表格数据</div>';
    } else {
        for (var t = 0; t < tableDiff.tables.length; t++) {
            var table = tableDiff.tables[t];
            html += '<div style="margin-bottom:12px">';
            html += '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px"><span style="font-size:13px;font-weight:600">表格 ' + (t + 1) + '</span>';
            html += '<span style="font-size:11px;padding:2px 8px;border-radius:4px;' + (table.summary.inconsistent_rows > 0 ? 'background:rgba(210,153,34,.15);color:var(--warning)' : 'background:rgba(46,160,67,.15);color:var(--success)') + '">' + table.summary.consistent_rows + '/' + table.summary.total_rows + ' 行一致</span></div>';

            if (table.header_status === '不一致' && table.header_differences && table.header_differences.length > 0) {
                html += '<div style="padding:8px 12px;margin-bottom:8px;border-radius:6px;background:rgba(210,153,34,.08);border:1px solid rgba(210,153,34,.3)">';
                html += '<div style="font-size:12px;font-weight:600;color:var(--warning);margin-bottom:4px"><i class="bi bi-exclamation-triangle"></i> 表头存在差异</div>';
                for (var h = 0; h < table.header_differences.length; h++) {
                    html += '<div style="font-size:11px;color:var(--text-sec)">' + proofreadEscapeHtml(table.header_differences[h].difference) + '</div>';
                }
                html += '</div>';
            }

            var maxHeaders = table.headers_a.length >= table.headers_b.length ? table.headers_a : table.headers_b;
            html += '<div style="overflow-x:auto;border:1px solid var(--border);border-radius:8px">';
            html += '<table style="width:100%;border-collapse:collapse;font-size:12px">';
            html += '<thead><tr>';
            html += '<th style="width:50px;text-align:center">行号</th>';
            html += '<th style="width:70px;text-align:center">状态</th>';
            for (var hi = 0; hi < maxHeaders.length; hi++) {
                html += '<th>' + proofreadEscapeHtml(maxHeaders[hi] || '列' + (hi + 1)) + '</th>';
            }
            html += '<th style="min-width:180px">差异说明</th>';
            html += '</tr></thead><tbody>';

            for (var r = 0; r < table.rows.length; r++) {
                var row = table.rows[r];
                var rowConsistent = row.status === '一致';
                html += '<tr style="border-left:3px solid ' + (rowConsistent ? 'var(--success)' : 'var(--danger)') + '">';
                html += '<td style="text-align:center;font-family:monospace;font-size:11px">' + row.row_index + '</td>';
                html += '<td style="text-align:center"><span style="font-size:11px;padding:2px 6px;border-radius:3px;' + (rowConsistent ? 'background:rgba(46,160,67,.15);color:var(--success)' : 'background:rgba(248,81,73,.15);color:var(--danger)') + '"><i class="bi bi-' + (rowConsistent ? 'check' : 'x') + '"></i> ' + row.status + '</span></td>';

                var maxCells = Math.max((row.cells_a || []).length, (row.cells_b || []).length, maxHeaders.length);
                for (var ci = 0; ci < maxCells; ci++) {
                    var valA = (row.cells_a && ci < row.cells_a.length) ? row.cells_a[ci] : '';
                    var valB = (row.cells_b && ci < row.cells_b.length) ? row.cells_b[ci] : '';
                    var hasDiff = valA !== valB;
                    html += '<td style="' + (hasDiff ? 'background:rgba(210,153,34,.08)' : '') + '">';
                    if (hasDiff) {
                        if (valA && valB) {
                            html += '<div style="font-size:11px;color:#fca5a5;text-decoration:line-through">' + proofreadEscapeHtml(valA) + '</div>';
                            html += '<div style="font-size:11px;color:#6ee7b7">' + proofreadEscapeHtml(valB) + '</div>';
                        } else if (valA) {
                            html += '<div style="font-size:11px;color:#fca5a5;text-decoration:line-through">' + proofreadEscapeHtml(valA) + '</div>';
                        } else if (valB) {
                            html += '<div style="font-size:11px;color:#6ee7b7">' + proofreadEscapeHtml(valB) + '</div>';
                        }
                    } else {
                        html += proofreadEscapeHtml(valA || valB);
                    }
                    html += '</td>';
                }

                html += '<td style="font-size:11px;color:' + (rowConsistent ? 'var(--success)' : 'var(--danger)') + '">' + (rowConsistent ? '-' : proofreadEscapeHtml(row.difference_description)) + '</td>';
                html += '</tr>';
            }

            html += '</tbody></table></div></div>';
        }
    }
    html += '</div>';
    return html;
}

// ==================== 历史记录 ====================
async function proofreadLoadHistory() {
    try {
        var resp = await fetch('/api/proofread/history');
        var data = await resp.json();
        if (data.status !== 'success') return;

        var list = document.getElementById('proofreadHistoryList');
        var empty = document.getElementById('proofreadHistoryEmpty');

        if (!data.data || data.data.length === 0) {
            list.innerHTML = '';
            empty.style.display = 'block';
            return;
        }

        empty.style.display = 'none';
        var html = '';
        for (var i = 0; i < data.data.length; i++) {
            var record = data.data[i];
            var isConsistent = record.overall_status === '一致';
            html += '<div class="card" style="margin-bottom:8px;cursor:pointer" onclick="proofreadViewHistory(\'' + record.id + '\')">';
            html += '<div class="card-body" style="padding:12px 16px;display:flex;justify-content:space-between;align-items:center">';
            html += '<div style="display:flex;align-items:center;gap:10px">';
            html += '<i class="bi bi-code-compare" style="font-size:18px;color:var(--accent)"></i>';
            html += '<div>';
            html += '<div style="display:flex;align-items:center;gap:6px;margin-bottom:2px">';
            for (var j = 0; j < record.files.length; j++) {
                if (j > 0) html += '<i class="bi bi-arrow-right" style="font-size:10px;color:var(--warning)"></i>';
                html += '<span class="badge-kw" style="font-size:10px">' + proofreadEscapeHtml(record.files[j]) + '</span>';
            }
            html += '</div>';
            html += '<div style="font-size:11px;color:var(--text-sec)">' + proofreadFormatTime(record.timestamp) + '</div>';
            html += '</div></div>';
            html += '<div style="display:flex;align-items:center;gap:8px">';
            html += '<span style="font-size:11px;padding:2px 8px;border-radius:4px;' + (isConsistent ? 'background:rgba(46,160,67,.15);color:var(--success)' : 'background:rgba(248,81,73,.15);color:var(--danger)') + '">' + record.overall_status + '</span>';
            html += '<button class="btn-del" onclick="event.stopPropagation();proofreadDeleteHistory(\'' + record.id + '\')" title="删除"><i class="bi bi-trash3"></i></button>';
            html += '</div></div></div>';
        }
        list.innerHTML = html;
    } catch (err) {
        showToast('加载历史记录失败', 'error');
    }
}

async function proofreadViewHistory(historyId) {
    try {
        var resp = await fetch('/api/proofread/history/' + historyId);
        var data = await resp.json();
        if (data.status !== 'success') {
            showToast(data.message || '获取失败', 'error');
            return;
        }
        switchProofreadTab('compare');
        document.getElementById('proofread-upload-area').style.display = 'none';
        document.getElementById('proofread-result').style.display = 'block';
        proofreadRenderResults(data.data.results, data.data.id, data.data.original_file_id);
    } catch (err) {
        showToast('查看历史记录失败', 'error');
    }
}

async function proofreadDeleteHistory(historyId) {
    if (!confirm('确定要删除这条历史记录吗？')) return;
    try {
        var resp = await fetch('/api/proofread/history/' + historyId, { method: 'DELETE' });
        var data = await resp.json();
        if (data.status === 'success') {
            showToast('已删除', 'success');
            proofreadLoadHistory();
        } else {
            showToast(data.message || '删除失败', 'error');
        }
    } catch (err) {
        showToast('删除失败', 'error');
    }
}

function proofreadFormatTime(ts) {
    if (!ts) return '';
    var d = new Date(ts);
    return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}
