"""
PDF文档解析器 (.pdf)
提取文本内容，尝试提取表格
"""
import os


def parse_pdf(filepath):
    """解析PDF文档，返回文本和表格内容"""
    texts = []
    tables = []

    # 尝试使用PyMuPDF (fitz)
    try:
        import fitz
        doc = fitz.open(filepath)

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").strip()
            if text:
                paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
                for para in paragraphs:
                    texts.append({
                        'index': len(texts),
                        'content': para,
                        'page': page_num + 1
                    })

            try:
                tabs = page.find_tables()
                if tabs and tabs.tables:
                    for tab in tabs.tables:
                        table_data = tab.extract()
                        if table_data and len(table_data) > 0:
                            parsed_table = {
                                'index': len(tables),
                                'page': page_num + 1,
                                'headers': [str(c) if c else '' for c in table_data[0]],
                                'rows': []
                            }
                            for r_idx, row in enumerate(table_data[1:], 1):
                                parsed_table['rows'].append({
                                    'row_index': r_idx,
                                    'cells': [str(c) if c else '' for c in row]
                                })
                            tables.append(parsed_table)
            except Exception:
                pass

        doc.close()
        return {'texts': texts, 'tables': tables}
    except ImportError:
        pass

    # 备选方案：使用pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(filepath) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
                    for para in paragraphs:
                        texts.append({
                            'index': len(texts),
                            'content': para,
                            'page': page_num + 1
                        })
                try:
                    page_tables = page.extract_tables()
                    for table_data in page_tables:
                        if table_data and len(table_data) > 0:
                            parsed_table = {
                                'index': len(tables),
                                'page': page_num + 1,
                                'headers': [str(c) if c else '' for c in table_data[0]],
                                'rows': []
                            }
                            for r_idx, row in enumerate(table_data[1:], 1):
                                parsed_table['rows'].append({
                                    'row_index': r_idx,
                                    'cells': [str(c) if c else '' for c in row]
                                })
                            tables.append(parsed_table)
                except Exception:
                    pass
        return {'texts': texts, 'tables': tables}
    except ImportError:
        pass

    # 最终备选：使用pdf2image + OCR
    try:
        from doc_proofread.parsers.image_parser import parse_image
        from pdf2image import convert_from_path
        images = convert_from_path(filepath)
        for page_num, img in enumerate(images):
            temp_path = filepath + f'_page_{page_num}.png'
            img.save(temp_path, 'PNG')
            try:
                result = parse_image(temp_path)
                for t in result.get('texts', []):
                    t['page'] = page_num + 1
                    texts.append(t)
                for tb in result.get('tables', []):
                    tb['page'] = page_num + 1
                    tables.append(tb)
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        return {'texts': texts, 'tables': tables}
    except Exception as e:
        raise RuntimeError(f"PDF解析失败，请安装 PyMuPDF (pip install PyMuPDF) 或 pdfplumber (pip install pdfplumber): {str(e)}")
