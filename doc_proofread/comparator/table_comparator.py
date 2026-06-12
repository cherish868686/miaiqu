"""
表格比对器
逐行比对表格数据，标注一致/不一致及差异说明
"""
import difflib


def compare_tables(tables_a, tables_b):
    """比对两组表格数据，逐行标注一致/不一致"""
    result = {
        'tables': [],
        'total_tables_compared': 0,
        'total_rows_compared': 0,
        'total_inconsistent_rows': 0
    }

    max_tables = max(len(tables_a), len(tables_b))

    for t_idx in range(max_tables):
        table_a = tables_a[t_idx] if t_idx < len(tables_a) else None
        table_b = tables_b[t_idx] if t_idx < len(tables_b) else None

        table_comparison = {
            'table_index': t_idx,
            'table_a_name': table_a.get('sheet_name', f'表格{t_idx+1}') if table_a else '不存在',
            'table_b_name': table_b.get('sheet_name', f'表格{t_idx+1}') if table_b else '不存在',
            'headers_a': table_a.get('headers', []) if table_a else [],
            'headers_b': table_b.get('headers', []) if table_b else [],
            'header_status': '一致',
            'header_differences': [],
            'rows': [],
            'summary': {
                'total_rows': 0,
                'consistent_rows': 0,
                'inconsistent_rows': 0
            }
        }

        # 比对表头
        if table_a and table_b:
            headers_a = table_a.get('headers', [])
            headers_b = table_b.get('headers', [])
            header_diff = compare_headers(headers_a, headers_b)
            table_comparison['header_status'] = header_diff['status']
            table_comparison['header_differences'] = header_diff['differences']

        # 比对行数据
        rows_a = table_a.get('rows', []) if table_a else []
        rows_b = table_b.get('rows', []) if table_b else []
        max_rows = max(len(rows_a), len(rows_b))

        for r_idx in range(max_rows):
            row_a = rows_a[r_idx] if r_idx < len(rows_a) else None
            row_b = rows_b[r_idx] if r_idx < len(rows_b) else None

            row_comparison = compare_row(
                row_a, row_b, r_idx,
                table_a.get('headers', []) if table_a else [],
                table_b.get('headers', []) if table_b else []
            )

            table_comparison['rows'].append(row_comparison)
            table_comparison['summary']['total_rows'] += 1

            if row_comparison['status'] == '一致':
                table_comparison['summary']['consistent_rows'] += 1
            else:
                table_comparison['summary']['inconsistent_rows'] += 1

        result['tables'].append(table_comparison)
        result['total_tables_compared'] += 1
        result['total_rows_compared'] += table_comparison['summary']['total_rows']
        result['total_inconsistent_rows'] += table_comparison['summary']['inconsistent_rows']

    return result


def compare_headers(headers_a, headers_b):
    """比对表头"""
    differences = []
    status = '一致'
    max_len = max(len(headers_a), len(headers_b))

    for i in range(max_len):
        h_a = headers_a[i] if i < len(headers_a) else '(缺失)'
        h_b = headers_b[i] if i < len(headers_b) else '(缺失)'

        if h_a != h_b:
            status = '不一致'
            differences.append({
                'column_index': i,
                'header_a': h_a,
                'header_b': h_b,
                'difference': f"列{i+1}: 文档A为'{h_a}', 文档B为'{h_b}'"
            })

    return {'status': status, 'differences': differences}


def compare_row(row_a, row_b, row_index, headers_a, headers_b):
    """比对单行数据"""
    if row_a is None and row_b is None:
        return {
            'row_index': row_index + 1,
            'status': '一致',
            'cells_a': [],
            'cells_b': [],
            'differences': [],
            'difference_description': ''
        }

    if row_a is None:
        return {
            'row_index': row_index + 1,
            'status': '不一致',
            'cells_a': [],
            'cells_b': row_b.get('cells', []),
            'differences': [{'type': 'missing_in_a', 'description': '文档A中缺失此行'}],
            'difference_description': '文档A中缺失此行'
        }

    if row_b is None:
        return {
            'row_index': row_index + 1,
            'status': '不一致',
            'cells_a': row_a.get('cells', []),
            'cells_b': [],
            'differences': [{'type': 'missing_in_b', 'description': '文档B中缺失此行'}],
            'difference_description': '文档B中缺失此行'
        }

    cells_a = row_a.get('cells', [])
    cells_b = row_b.get('cells', [])
    differences = []
    max_cols = max(len(cells_a), len(cells_b))
    headers = headers_a if len(headers_a) >= max_cols else headers_b

    for c_idx in range(max_cols):
        val_a = cells_a[c_idx] if c_idx < len(cells_a) else '(缺失)'
        val_b = cells_b[c_idx] if c_idx < len(cells_b) else '(缺失)'

        if val_a != val_b:
            col_name = headers[c_idx] if c_idx < len(headers) else f'列{c_idx+1}'
            similarity = difflib.SequenceMatcher(None, str(val_a), str(val_b)).ratio()

            diff_type = 'replace'
            if val_a == '(缺失)':
                diff_type = 'missing_in_a'
            elif val_b == '(缺失)':
                diff_type = 'missing_in_b'

            char_diff = get_cell_char_diff(str(val_a), str(val_b))

            differences.append({
                'type': diff_type,
                'column_index': c_idx,
                'column_name': col_name,
                'value_a': val_a,
                'value_b': val_b,
                'similarity': round(similarity * 100, 1),
                'char_diff': char_diff,
                'description': f"{col_name}: 文档A为'{val_a}', 文档B为'{val_b}' (相似度{round(similarity*100,1)}%)"
            })

    status = '一致' if not differences else '不一致'
    diff_desc = '; '.join(d['description'] for d in differences) if differences else ''

    return {
        'row_index': row_index + 1,
        'status': status,
        'cells_a': cells_a,
        'cells_b': cells_b,
        'differences': differences,
        'difference_description': diff_desc
    }


def get_cell_char_diff(val_a, val_b):
    """获取单元格字符级差异"""
    matcher = difflib.SequenceMatcher(None, val_a, val_b)
    char_diffs = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            char_diffs.append({'type': 'equal', 'text': val_a[i1:i2]})
        elif tag == 'replace':
            char_diffs.append({'type': 'replace', 'text_a': val_a[i1:i2], 'text_b': val_b[j1:j2]})
        elif tag == 'delete':
            char_diffs.append({'type': 'delete', 'text_a': val_a[i1:i2]})
        elif tag == 'insert':
            char_diffs.append({'type': 'insert', 'text_b': val_b[j1:j2]})
    return char_diffs
