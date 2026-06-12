import sys
deps = ['flask','requests','bs4','apscheduler','dotenv','lxml','docx','openpyxl','pptx','PIL','fitz','pdfplumber']
for d in deps:
    try:
        __import__(d)
        print(f'{d}: OK')
    except ImportError:
        print(f'{d}: MISSING')
