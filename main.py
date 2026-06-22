from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

print("Loading vectorstore...")
EMBED_MODEL = "bkai-foundation-models/vietnamese-bi-encoder"

embeddings = HuggingFaceEmbeddings(
    model_name=EMBED_MODEL,
    model_kwargs={"device": "cuda"},
    encode_kwargs={"normalize_embeddings": True},
)
vectorstore = FAISS.load_local(
    "./vectorstore",
    embeddings,
    allow_dangerous_deserialization=True,
)
retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 3},  # lấy top-1 chunks liên quan
)
print("✅ Vectorstore ready!\n")

# =========================================
# HÀM RAG CORE
# =========================================
def retrieve_context(question: str) -> tuple[str, list[str]]:
    """Trả về (context_string, danh_sách_nguồn)"""
    docs = retriever.invoke(question)
    
    context_parts = []
    sources = []
    for i, doc in enumerate(docs, 1):
        context_parts.append(f"[{i}] {doc.page_content}")
        sources.append(doc.metadata.get("source", "unknown"))
    
    context = "\n\n".join(context_parts)
    return context, sources

def build_rag_prompt(question: str, context: str) -> str:
    return f"""Dựa vào 1 quy định đúng nhất trong các quy định pháp luật sau đây để trả lời câu hỏi, không trả lời lan man ngoài phạm vi câu hỏi của người dùng:

{context}

---
Câu hỏi: {question}

Hãy trả lời chính xác, trích dẫn điều khoản/nghị định cụ thể từ tài liệu trên."""