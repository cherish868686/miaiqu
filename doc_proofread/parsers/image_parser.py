"""
图片解析器 (.jpg, .jpeg, .png)
使用OCR提取文本内容
"""
from PIL import Image


def parse_image(filepath):
    """解析图片，使用OCR提取文本"""
    texts = []
    tables = []

    try:
        import pytesseract
        img = Image.open(filepath)
        text = pytesseract.image_to_string(img, lang='chi_sim+eng').strip()

        if text:
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            for i, line in enumerate(lines):
                texts.append({
                    'index': i,
                    'content': line
                })

        # 尝试提取表格数据
        try:
            table_data = pytesseract.image_to_data(img, lang='chi_sim+eng', output_type=pytesseract.Output.DICT)
            words = []
            for i in range(len(table_data['text'])):
                if table_data['text'][i].strip():
                    words.append({
                        'text': table_data['text'][i].strip(),
                        'left': table_data['left'][i],
                        'top': table_data['top'][i],
                        'width': table_data['width'][i],
                        'height': table_data['height'][i]
                    })

            if words:
                words.sort(key=lambda w: (w['top'], w['left']))
                rows = []
                current_row = [words[0]]

                for w in words[1:]:
                    if abs(w['top'] - current_row[0]['top']) < current_row[0]['height'] * 0.8:
                        current_row.append(w)
                    else:
                        rows.append(current_row)
                        current_row = [w]
                if current_row:
                    rows.append(current_row)

                if len(rows) >= 2:
                    avg_cols = sum(len(r) for r in rows) / len(rows)
                    if avg_cols >= 2:
                        parsed_table = {
                            'index': 0,
                            'headers': [w['text'] for w in rows[0]],
                            'rows': []
                        }
                        for r_idx, row in enumerate(rows[1:], 1):
                            parsed_table['rows'].append({
                                'row_index': r_idx,
                                'cells': [w['text'] for w in row]
                            })
                        tables.append(parsed_table)
        except Exception:
            pass

        img.close()

    except ImportError:
        raise RuntimeError("图片OCR需要安装 pytesseract 和 Tesseract OCR引擎")

    return {'texts': texts, 'tables': tables}
