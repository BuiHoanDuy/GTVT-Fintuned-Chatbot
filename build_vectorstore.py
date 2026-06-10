import json
import sys
import traceback
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

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
    try:
        print("Step 1: Loading chunks...")
        sys.stdout.flush()
        docs = load_chunks(jsonl_path)
        print(f"✓ Loaded {len(docs)} chunks")
        sys.stdout.flush()
        
        print("\nStep 2: Initializing embeddings model...")
        sys.stdout.flush()
        embeddings = HuggingFaceEmbeddings(
            model_name="bkai-foundation-models/vietnamese-bi-encoder",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        print("✓ Embeddings model loaded")
        sys.stdout.flush()
        
        print("\nStep 3: Building FAISS vectorstore (may take 10-30 min on CPU)...")
        sys.stdout.flush()
        vectorstore = FAISS.from_documents(docs, embeddings)
        print("✓ FAISS vectorstore built")
        sys.stdout.flush()
        
        print("\nStep 4: Saving vectorstore...")
        sys.stdout.flush()
        vectorstore.save_local(save_path)
        print(f"✅ Vectorstore saved to {save_path}")
        sys.stdout.flush()
        
    except Exception as e:
        print(f"\n❌ ERROR occurred:")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()
        sys.stdout.flush()

if __name__ == "__main__":
    build()
    input("\nPress Enter to exit...")