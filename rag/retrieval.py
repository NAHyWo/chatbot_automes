import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.abspath(os.path.join(current_dir, ".."))
os.environ["HF_HOME"] = os.path.join(base_dir, "huggingface_cache")
os.environ["TRANSFORMERS_CACHE"] = os.path.join(base_dir, "huggingface_cache", "transformers")
os.environ["HF_DATASETS_CACHE"] = os.path.join(base_dir, "huggingface_cache", "datasets")
os.environ["TORCH_HOME"] = os.path.join(base_dir, "huggingface_cache", "torch")
os.environ["TMPDIR"] = os.path.join(base_dir, "huggingface_cache", "tmp")

import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


index_path = "my_index.faiss"
texts_path = "my_index_texts.pkl"
embeddings_path = "my_index_embeddings.npy"

print("FAISS 인덱스, 텍스트, 임베딩 로딩 중...")
index = faiss.read_index(index_path)
with open(texts_path, "rb") as f:
    texts = pickle.load(f)

embeddings = np.load(embeddings_path)
# L2 정규화 (벡터 길이 1로 맞추기)
embeddings_normalized = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

print(f"총 {len(texts)}개의 문서 텍스트와 임베딩 로드 완료")

model = SentenceTransformer("BAAI/bge-m3")

while True:
    message = input("임베딩 테스트할 문장을 입력하세요. (종료: exit): ")
    if message.strip().lower() == "exit":
        break

    query = message
    query_embedding = model.encode([query])

    # FAISS L2 거리 검색
    top_k = 5
    D, I = index.search(query_embedding, top_k)

    # numpy로 Inner Product 계산
    inner_products = np.dot(query_embedding, embeddings.T)[0]

    print(f"\n쿼리: \"{query}\"\n")
    print("유사한 문서 Top", top_k)

    for rank, idx in enumerate(I[0]):
        print(f"\n{rank+1}. ▶ L2 Distance: {D[0][rank]:.4f}")
        print(f"    Inner Product: {inner_products[idx]:.4f}")
        print(f"문서 내용:\n{texts[idx][:500]}")
        print("-" * 50)
