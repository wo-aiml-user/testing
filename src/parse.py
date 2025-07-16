"""from typing import List
from langchain_community.document_loaders.parsers.pdf import PDFPlumberParser
from langchain_community.document_loaders.blob_loaders import Blob
from langchain_core.documents import Document

def extract_text_from_pdf_path(file_path: str) -> str:
    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        blob = Blob.from_data(file_bytes, path=file_path)
        parser = PDFPlumberParser(extract_images=True)
        documents: List[Document] = parser.parse(blob)

        return "\n\n".join(doc.page_content for doc in documents)

    except Exception as e:
        print(f"[ERROR] Failed to parse PDF: {e}")
        return ""
pdf_path = "/home/desk0046/Documents/agent/data/Project.pdf"
content = extract_text_from_pdf_path(pdf_path)
print(content)"""

