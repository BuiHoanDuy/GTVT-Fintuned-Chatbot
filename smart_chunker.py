# smart_chunker.py
import re
from dataclasses import dataclass
from typing import List

@dataclass
class LawChunk:
    text: str
    source_file: str      # "nghi_dinh_100_2019.txt"
    dieu_number: str      # "Điều 5"
    full_ref: str         # "NĐ 100/2019, Điều 5, Khoản 2"

def extract_law_id(filename: str) -> str:
    """nghi_dinh_100_2019.txt → NĐ 100/2019/NĐ-CP"""
    mapping = {
        "nghi_dinh_100_2019": "Nghị định 100/2019/NĐ-CP",
        "nghi_dinh_123_2021": "Nghị định 123/2021/NĐ-CP",
        "luat_gtdb_2008":     "Luật GTĐB 2008",
    }
    key = filename.replace(".txt", "")
    return mapping.get(key, key)

def chunk_by_dieu(text: str, source_file: str, 
                   max_chars: int = 800) -> List[LawChunk]:
    """
    Split theo Điều, sau đó nếu Điều quá dài thì split tiếp theo Khoản.
    Mỗi chunk đều có prefix 'Theo [NĐ xxx], Điều Y:' để model biết nguồn.
    """
    law_id = extract_law_id(source_file)
    chunks = []
    
    # Tách theo "Điều X."
    dieu_pattern = re.compile(r'(?=\nĐiều \d+[\.\:])')
    dieu_blocks = dieu_pattern.split(text)
    
    for block in dieu_blocks:
        block = block.strip()
        if not block:
            continue
        
        # Lấy số điều
        m = re.match(r'Điều (\d+)', block)
        dieu_num = f"Điều {m.group(1)}" if m else "Điều ?"
        
        # Nếu block ngắn → giữ nguyên 1 chunk
        if len(block) <= max_chars:
            prefix = f"[Nguồn: {law_id}, {dieu_num}]\n"
            chunks.append(LawChunk(
                text=prefix + block,
                source_file=source_file,
                dieu_number=dieu_num,
                full_ref=f"{law_id}, {dieu_num}",
            ))
        else:
            # Block dài → split tiếp theo Khoản
            khoan_pattern = re.compile(r'(?=\nKhoản \d+[\.\:])')
            khoan_blocks = khoan_pattern.split(block)
            
            for kb in khoan_blocks:
                kb = kb.strip()
                if not kb:
                    continue
                
                mk = re.match(r'Khoản (\d+)', kb)
                khoan_ref = f"Khoản {mk.group(1)}" if mk else ""
                full_ref = f"{law_id}, {dieu_num}" + (f", {khoan_ref}" if khoan_ref else "")
                prefix = f"[Nguồn: {full_ref}]\n"
                
                chunks.append(LawChunk(
                    text=prefix + kb,
                    source_file=source_file,
                    dieu_number=dieu_num,
                    full_ref=full_ref,
                ))
    
    return chunks


# ── Chạy chunker trên toàn bộ corpus ──
import os, json

def build_chunks_jsonl(clean_dir: str = "./corpus/clean",
                        out_path: str = "./corpus/chunks.jsonl"):
    all_chunks = []
    
    for fname in os.listdir(clean_dir):
        if not fname.endswith(".txt"):
            continue
        with open(os.path.join(clean_dir, fname), encoding="utf-8") as f:
            text = f.read()
        
        chunks = chunk_by_dieu(text, fname)
        all_chunks.extend(chunks)
        print(f"  {fname}: {len(chunks)} chunks")
    
    with open(out_path, "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps({
                "text": c.text,
                "source": c.source_file,
                "ref": c.full_ref,
            }, ensure_ascii=False) + "\n")
    
    print(f"\n✅ Total: {len(all_chunks)} chunks → {out_path}")

if __name__ == "__main__":
    build_chunks_jsonl()