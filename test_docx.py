import os

from docx import Document
from docx.document import Document as DocumentObject
# from lxml import etree # type: ignore

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, r"docx_templates\模板.docx")
# M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"

def docx_edit(doc: DocumentObject, score:float, matrix: list[list] ,ver: list)-> DocumentObject:
    matrix_values_list = [ x for row in matrix for x in row]
    # v_values_list = [ x  for x in ver]
    values_list = matrix_values_list + ver + [score]
    idx =0 
    mts = doc.element.xpath('.//m:t[text()="PMR"]')
    for mt in mts:
        if mt.text == 'PMR':
            if idx < len(values_list):
                mt.text = str(values_list[idx])
                idx += 1
            else:
                break
    return doc

if __name__ == "__main__":
    matirx = [
        [1, 2, 3, 4],
        [5, 6, 7, 8],
        [9, 10, 11, 12],
        [13, 14, 15, 16],
        [17, 18, 19, 20],
    ]
    ver = [2, 4, 6, 8]
    doc = Document(TEMPLATE_PATH)
    docs = docx_edit(doc, 88.0,  matirx ,ver)
    docs.save(os.path.join(BASE_DIR, "output.docx"))
    