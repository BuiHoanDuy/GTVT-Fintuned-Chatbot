from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from peft import PeftModel
import torch
import json
import os
import asyncio
import threading
import uvicorn

from main import build_rag_prompt, retrieve_context

# =========================================
# LOAD MODEL KHI KHỞI ĐỘNG SERVER
# =========================================
print("=" * 60)
print("Loading VN Legal Traffic Model...")
print("=" * 60)

MODEL_PATH = "./lora_qwen25_vn_legal_rag"

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH,
    trust_remote_code=True,
)

adapter_config_path = os.path.join(MODEL_PATH, "adapter_config.json")
with open(adapter_config_path, "r") as f:
    adapter_config = json.load(f)
base_model_name = adapter_config.get("base_model_name_or_path", "Qwen/Qwen2.5-7B-Instruct")
print(f"Base model: {base_model_name}")

base_model = AutoModelForCausalLM.from_pretrained(
    base_model_name,
    trust_remote_code=True,
    device_map={"": 0},
)

model = PeftModel.from_pretrained(base_model, MODEL_PATH)
model.eval()

print("✅ Model ready!\n")

# =========================================
# FASTAPI APP
# =========================================
app = FastAPI(title="VN Legal Traffic API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SYSTEM_PROMPT = "Bạn là chuyên gia pháp luật giao thông Việt Nam, trả lời chính xác và có căn cứ pháp lý."

# Padding để mỗi SSE chunk vượt ngưỡng buffer của browser (thường 1KB)
SSE_PADDING = ": " + "p" * 1024 + "\n"

class QuestionRequest(BaseModel):
    question: str
    max_new_tokens: int = 1024
    temperature: float = 0.4

# class AnswerResponse(BaseModel):
#     question: str
#     answer: str

class AnswerResponse(BaseModel):
    question: str
    answer: str
    sources: list[str] = []

# =========================================
# ENDPOINTS
# =========================================
@app.get("/health")
def health():
    return {"status": "ok", "model": "lora_qwen25_vn_legal_rag"}


# @app.post("/generate", response_model=AnswerResponse)
# def generate(req: QuestionRequest):
#     if not req.question.strip():
#         raise HTTPException(status_code=400, detail="Câu hỏi không được để trống.")
#     try:
#         messages = [
#             {"role": "system", "content": SYSTEM_PROMPT},
#             {"role": "user",   "content": req.question},
#         ]
#         text = tokenizer.apply_chat_template(
#             messages, tokenize=False, add_generation_prompt=True,
#         )
#         inputs = tokenizer(text, return_tensors="pt").to("cuda")
#         with torch.no_grad():
#             outputs = model.generate(
#                 **inputs,
#                 max_new_tokens=req.max_new_tokens,
#                 temperature=req.temperature,
#                 top_p=0.9,
#                 repetition_penalty=1.05,
#                 do_sample=True,
#                 use_cache=True,
#             )
#         answer = tokenizer.decode(
#             outputs[0][inputs["input_ids"].shape[1]:],
#             skip_special_tokens=True,
#         )
#         return AnswerResponse(question=req.question, answer=answer)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate", response_model=AnswerResponse)
def generate(req: QuestionRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Câu hỏi không được để trống.")
    try:
        # ── RAG: lấy context ──
        context, sources = retrieve_context(req.question)
        rag_question = build_rag_prompt(req.question, context)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": rag_question},  # ← dùng rag_question
        ]
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
        )
        inputs = tokenizer(text, return_tensors="pt").to("cuda")
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=req.max_new_tokens,
                temperature=req.temperature,
                top_p=0.9,
                repetition_penalty=1.05,
                do_sample=True,
                use_cache=True,
            )
        answer = tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
        )
        return AnswerResponse(
            question=req.question,
            answer=answer,
            sources=sources,  # trả về nguồn để hiển thị UI
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/stream")
async def generate_stream(req: QuestionRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Câu hỏi không được để trống.")

    # ── RAG: lấy context ──
    context, sources = retrieve_context(req.question)
    rag_question = build_rag_prompt(req.question, context)

    print(f"Sources:\n{json.dumps(sources, ensure_ascii=False, indent=2)}\n")
    print(f"RAG question:\n{rag_question}\n")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": rag_question},
    ]
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
    )
    inputs = tokenizer(text, return_tensors="pt").to("cuda")

    streamer = TextIteratorStreamer(
        tokenizer,
        skip_prompt=True,
        skip_special_tokens=True,
        timeout=30.0,
    )

    generation_kwargs = dict(
        **inputs,
        streamer=streamer,
        max_new_tokens=req.max_new_tokens,
        temperature=req.temperature,
        top_p=0.9,
        repetition_penalty=1.05,
        do_sample=True,
        use_cache=True,
    )

    thread = threading.Thread(target=model.generate, kwargs=generation_kwargs)
    thread.start()

    async def async_token_generator():
        # Gửi sources trước để frontend biết nguồn ngay từ đầu
        yield SSE_PADDING
        sources_payload = json.dumps({"sources": sources}, ensure_ascii=False)
        yield f"data: {sources_payload}\n\n"
        await asyncio.sleep(0)

        try:
            for token in streamer:
                if token:
                    payload = json.dumps({"token": token}, ensure_ascii=False)
                    yield SSE_PADDING + f"data: {payload}\n\n"
                    await asyncio.sleep(0)
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        async_token_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked",
        },
    )

# Serve giao diện web
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        # h11 backend flush tốt hơn với SSE trên Windows
        http="h11",
    )