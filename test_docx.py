import os

from docx import Document
from docx.document import Document as DocumentObject
from lxml import etree # type: ignore

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, r"docx_templates\模板.docx")

if __name__ == "__main__":
    doc = Document(TEMPLATE_PATH)
    print(f"段落数量: {len(doc.paragraphs)}")
    print(f"表格数量: {len(doc.tables)}")
    for i, para in enumerate(doc.paragraphs[:10]):
        text_preview = para.text[:60] if para.text else "(空或含公式)"
        print(f"  段落{i}: {text_preview}")
    M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
    omath_count = len(doc.element.findall(f'.//{{{M_NS}}}oMath'))
    print(f"\nOMML 公式 (<m:oMath>) 数量: {omath_count}")