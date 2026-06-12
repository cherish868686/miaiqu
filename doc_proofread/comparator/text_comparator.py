"""
文本比对器
使用difflib进行文本差异比对，标注不一致内容
"""
import difflib


def compare_texts(texts_a, texts_b):
    """比对两组文本内容，返回差异结果"""
    lines_a = [t['content'] for t in texts_a]
    lines_b = [t['content'] for t in texts_b]

    matcher = difflib.SequenceMatcher(None, lines_a, lines_b)
    differences = []
    difference_count = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            continue

        diff = {
            'type': tag,
            'doc_a_range': [i1, i2],
            'doc_b_range': [j1, j2],
            'doc_a_content': lines_a[i1:i2],
            'doc_b_content': lines_b[j1:j2],
            'details': []
        }

        if tag == 'replace':
            max_len = max(i2 - i1, j2 - j1)
            for k in range(max_len):
                line_a = lines_a[i1 + k] if i1 + k < i2 else ''
                line_b = lines_b[j1 + k] if j1 + k < j2 else ''
                if line_a and line_b:
                    char_diff = get_char_level_diff(line_a, line_b)
                    diff['details'].append({
                        'line_a_index': i1 + k if i1 + k < i2 else None,
                        'line_b_index': j1 + k if j1 + k < j2 else None,
                        'content_a': line_a,
                        'content_b': line_b,
                        'char_diff': char_diff
                    })
                elif line_a:
                    diff['details'].append({
                        'line_a_index': i1 + k,
                        'line_b_index': None,
                        'content_a': line_a,
                        'content_b': '',
                        'char_diff': [{'type': 'delete', 'text': line_a}]
                    })
                elif line_b:
                    diff['details'].append({
                        'line_a_index': None,
                        'line_b_index': j1 + k,
                        'content_a': '',
                        'content_b': line_b,
                        'char_diff': [{'type': 'insert', 'text': line_b}]
                    })
        elif tag == 'delete':
            for k in range(i1, i2):
                diff['details'].append({
                    'line_a_index': k,
                    'line_b_index': None,
                    'content_a': lines_a[k],
                    'content_b': '',
                    'char_diff': [{'type': 'delete', 'text': lines_a[k]}]
                })
        elif tag == 'insert':
            for k in range(j1, j2):
                diff['details'].append({
                    'line_a_index': None,
                    'line_b_index': k,
                    'content_a': '',
                    'content_b': lines_b[k],
                    'char_diff': [{'type': 'insert', 'text': lines_b[k]}]
                })

        differences.append(diff)
        difference_count += 1

    unified_diff = list(difflib.unified_diff(lines_a, lines_b, lineterm='', n=1))

    return {
        'total_lines_a': len(lines_a),
        'total_lines_b': len(lines_b),
        'difference_count': difference_count,
        'differences': differences,
        'unified_diff': unified_diff
    }


def get_char_level_diff(text_a, text_b):
    """获取字符级别的差异"""
    matcher = difflib.SequenceMatcher(None, text_a, text_b)
    char_diffs = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            char_diffs.append({'type': 'equal', 'text_a': text_a[i1:i2], 'text_b': text_b[j1:j2]})
        elif tag == 'replace':
            char_diffs.append({'type': 'replace', 'text_a': text_a[i1:i2], 'text_b': text_b[j1:j2]})
        elif tag == 'delete':
            char_diffs.append({'type': 'delete', 'text_a': text_a[i1:i2], 'text_b': ''})
        elif tag == 'insert':
            char_diffs.append({'type': 'insert', 'text_a': '', 'text_b': text_b[j1:j2]})
    return char_diffs
