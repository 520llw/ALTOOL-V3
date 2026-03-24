# -*- coding: utf-8 -*-
import pdfplumber
import json
import os

def extract_pdf_content(pdf_path):
    content = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_data = {
                    "page": i + 1,
                    "text": page.extract_text(),
                    "tables": page.extract_tables()
                }
                content.append(page_data)
        return content
    except Exception as e:
        return f"Error: {str(e)}"

pdfs = [
    "/home/gjw/AITOOL/尚阳通规格书/Sanrise-SRE50N120FSUS7(1).pdf",
    "/home/gjw/AITOOL/尚阳通规格书/SRC30R018BTLTR-G\u00a0preliminary Datasheet\u00a0V0.1 .pdf",
    "/home/gjw/AITOOL/尚阳通规格书/SRC60R017FBDatasheetV1.pdf",
    "/home/gjw/AITOOL/尚阳通规格书/SRC60R017FBS\u00a0Datasheet\u00a0V1.1.pdf",
    "/home/gjw/AITOOL/尚阳通规格书/SRC60R020BS\u00a0\u00a0\u00a0DatasheetV1.0(1).pdf"
]

results = {}
for path in pdfs:
    name = os.path.basename(path)
    print(f"Extracting {name}...")
    results[name] = extract_pdf_content(path)

with open("raw_pdf_content.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
