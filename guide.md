### Bước 1 — Kiểm tra Python và GPU

python --version
nvidia-smi

- `python --version` phải ra 3.10 trở lên
- `nvidia-smi` phải thấy GPU và cột **CUDA Version** (ví dụ: 12.4)

Nếu không có `nvidia-smi`, cần cài driver NVIDIA tại https://www.nvidia.com/drivers

### Bước 2 — Tạo và kích hoạt virtual environment
cd C:\DATN\Backend
python -m venv venv
venv\Scripts\activate

### Bước 3 — Nâng cấp pip
python -m pip install --upgrade pip setuptools wheel

### Bước 4 — Cài PyTorch với CUDA

Chọn đúng theo cột **CUDA Version** trong `nvidia-smi`:


# CUDA 12.4 (khuyến nghị)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

Kiểm tra GPU nhận đúng chưa:

python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0))"

Phải ra `CUDA: True` và tên GPU của bạn. Nếu ra `CUDA: False` thì dừng lại, kiểm tra lại driver và CUDA version.

### Bước 5 — Cài các thư viện

Cài lần lượt, **không gộp chung** để tránh pip tự upgrade torch:

pip install transformers==5.5.0 --no-deps
pip install tokenizers==0.22.2 --no-deps
pip install huggingface_hub --no-deps
pip install accelerate --no-deps
pip install peft --no-deps
pip install bitsandbytes
pip install fastapi uvicorn
pip install sentencepiece
pip install langchain langchain-community faiss-cpu sentence-transformers
pip install langchain-huggingface
pip install tf-keras
### Chạy theo thứ tự sau để có vector db file chunks
clean_corpus.py  →  smart_chunker.py  →  build_vectorstore.py
      ↓                   ↓                      ↓
 corpus/clean/      corpus/chunks.jsonl       vectorstore/
---

### Bước 7 — Chạy server
python api.py

## Truy cập

| Mục đích         | URL                          |
|------------------|------------------------------|
| Giao diện web    | http://localhost:8000        |
| Swagger test API | http://localhost:8000/docs   |

## Test API nhanh bằng PowerShell

# Kiểm tra server sống
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method GET

# Gửi câu hỏi (không streaming)
Invoke-RestMethod -Uri "http://localhost:8000/generate" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"question":"Vượt đèn đỏ xe máy bị phạt bao nhiêu tiền?"}'

## Chạy lại lần sau
cd C:\DATN\Backend
venv\Scripts\activate
python api.py