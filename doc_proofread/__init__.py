# 文档校对模块
from doc_proofread.parsers import docx_parser, xlsx_parser, pdf_parser, pptx_parser, image_parser
from doc_proofread.comparator import text_comparator, table_comparator
from doc_proofread.routes import register_proofread_routes
