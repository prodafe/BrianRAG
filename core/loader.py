import os
from typing import List
from langchain_community.document_loaders import TextLoader, PyPDFLoader, UnstructuredMarkdownLoader
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from langchain_classic.schema import Document

def load_documents(file_paths: List[str]) -> List[Document]:
    docs = []
    for path in file_paths:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".pdf":
            loader = PyPDFLoader(path)
        elif ext == ".md":
            loader = UnstructuredMarkdownLoader(path)
        else:
            loader = TextLoader(path, encoding="utf-8")
        docs.extend(loader.load())
    return docs

def split_documents(docs: List[Document], chunk_size=500, chunk_overlap=50) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
    )
    chunks = splitter.split_documents(docs)
    return [chunk.page_content for chunk in chunks]