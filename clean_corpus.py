# clean_corpus.py
import re
import os

def clean_law_text(text: str) -> str:
    # 1. Xóa ký tự thừa từ HTML
    text = re.sub(r'\xa0', ' ', text)          # non-breaking space
    text = re.sub(r'\u200b', '', text)          # zero-width space
    
    # 2. Chuẩn hóa dòng trống — giữ tối đa 2 dòng liên tiếp
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 3. Xóa header/footer lặp lại của website
    text = re.sub(r'Tải về.*?\n', '', text)
    text = re.sub(r'In trang.*?\n', '', text)
    text = re.sub(r'Lược đồ.*?\n', '', text)
    
    # 4. Chuẩn hóa số điều khoản về 1 format thống nhất
    # "Điều 5." → "Điều 5."  (giữ nguyên)
    # "điều 5"  → "Điều 5"   (viết hoa chữ đầu)
    text = re.sub(r'\bđiều\s+(\d+)', r'Điều \1', text)
    text = re.sub(r'\bkhoản\s+(\d+)', r'Khoản \1', text)
    text = re.sub(r'\bđiểm\s+([a-z])\b', r'Điểm \1', text)
    
    # 5. Thêm metadata nghị định vào đầu mỗi điều để model có context
    # (xem thêm ở bước add_source_prefix)
    
    return text.strip()

def process_all(raw_dir: str = "./corpus/raw", 
                clean_dir: str = "./corpus/clean"):
    os.makedirs(clean_dir, exist_ok=True)
    
    for fname in os.listdir(raw_dir):
        if not fname.endswith(".txt"):
            continue
        
        with open(os.path.join(raw_dir, fname), encoding="utf-8") as f:
            raw = f.read()
        
        cleaned = clean_law_text(raw)
        
        out_path = os.path.join(clean_dir, fname)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(cleaned)
        
        print(f"✅ Cleaned: {fname}  {len(raw):,} → {len(cleaned):,} chars")

if __name__ == "__main__":
    process_all()