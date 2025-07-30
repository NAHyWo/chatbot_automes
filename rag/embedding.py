import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.abspath(os.path.join(current_dir, ".."))
os.environ["HF_HOME"] = os.path.join(base_dir, "huggingface_cache")
os.environ["TRANSFORMERS_CACHE"] = os.path.join(base_dir, "huggingface_cache", "transformers")
os.environ["HF_HUB_CACHE"] = os.path.join(base_dir, "huggingface_cache", "hub")
os.environ["HF_DATASETS_CACHE"] = os.path.join(base_dir, "huggingface_cache", "datasets")
os.environ["TORCH_HOME"] = os.path.join(base_dir, "huggingface_cache", "torch")
os.environ["TMPDIR"] = os.path.join(base_dir, "huggingface_cache", "tmp")

import pickle
import numpy as np
from typing import List
from langchain.document_loaders import (
    TextLoader, PyPDFLoader, UnstructuredWordDocumentLoader,
    UnstructuredHTMLLoader, CSVLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import faiss


# 확장자별 문서 로더
EXTENSION_LOADER_MAP = {
    ".txt": TextLoader,
    ".md": TextLoader,
    ".pdf": PyPDFLoader,
    ".docx": UnstructuredWordDocumentLoader,
    ".html": UnstructuredHTMLLoader,
    ".htm": UnstructuredHTMLLoader,
    ".csv": CSVLoader,
}


def load_document_by_extension(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    loader_class = EXTENSION_LOADER_MAP.get(ext)

    if not loader_class:
        print(f"지원하지 않는 형식: {file_path}")
        return []

    try:
        loader = loader_class(file_path)
        return loader.load()
    except Exception as e:
        print(f"로딩 실패: {file_path} → {e}")
        return []


def load_all_documents(folder_path="docs") -> List:
    all_docs = []
    for file in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file)
        docs = load_document_by_extension(file_path)
        all_docs.extend(docs)
    print(f"총 {len(all_docs)}개의 문서 로딩 완료")
    return all_docs


def split_documents(docs, chunk_size=500, chunk_overlap=50):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return splitter.split_documents(docs)


def embed_documents(chunks, embedding_model_name="BAAI/bge-m3"):
    embedder = SentenceTransformer(embedding_model_name)

    texts = [f"passage: {chunk.page_content}" for chunk in chunks]
    sources = [os.path.basename(chunk.metadata.get("source", "unknown")) for chunk in chunks]

    embeddings = embedder.encode(texts, show_progress_bar=True)
    return embeddings, texts, sources


def save_faiss_index(embeddings, texts, sources, index_name="doc_index"):
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    faiss.write_index(index, f"{index_name}.faiss")

    with open(f"{index_name}_texts.pkl", "wb") as f:
        pickle.dump(texts, f)

    with open(f"{index_name}_sources.pkl", "wb") as f:
        pickle.dump(sources, f)

    np.save(f"{index_name}_embeddings.npy", embeddings)

    print(
        f"저장 완료: {index_name}.faiss / {index_name}_texts.pkl / {index_name}_sources.pkl / {index_name}_embeddings.npy")


def run_embedding_pipeline(folder_path="docs", embedding_model="BAAI/bge-m3", index_name="doc_index"):
    print("문서 로딩 중...")
    docs = load_all_documents(folder_path)

    print("문서 분할 중...")
    chunks = split_documents(docs)

    print("임베딩 생성 중...")
    embeddings, texts, sources = embed_documents(chunks, embedding_model)

    print("FAISS 저장 중...")
    save_faiss_index(embeddings, texts, sources, index_name)

    print("전체 임베딩 파이프라인 완료")


if __name__ == "__main__":
    docs_path = os.path.join(base_dir, "docs")
    run_embedding_pipeline(folder_path=docs_path, index_name="my_index")
