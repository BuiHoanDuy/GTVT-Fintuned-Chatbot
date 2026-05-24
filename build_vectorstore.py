# build_vectorstore.py
import json
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings  # ← đổi dòng này

def load_chunks(jsonl_path: str):
    docs = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            docs.append(Document(
                page_content=item["text"],
                metadata={"source": item["source"], "ref": item["ref"]},
            ))
    return docs

def build(jsonl_path="./corpus/chunks.jsonl", save_path="./vectorstore"):
    docs = load_chunks(jsonl_path)
    print(f"Loaded {len(docs)} chunks")
    
    embeddings = HuggingFaceEmbeddings(
        model_name="bkai-foundation-models/vietnamese-bi-encoder",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    
    vectorstore = FAISS.from_documents(docs, embeddings)
    vectorstore.save_local(save_path)
    print(f"✅ Vectorstore saved to {save_path}")

if __name__ == "__main__":
    build()