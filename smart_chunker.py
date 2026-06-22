# smart_chunker.py
import re
import os
import json
from dataclasses import dataclass
from typing import List


# ──────────────────────────────────────────────
# Mapping loại văn bản & cơ quan ban hành
# ──────────────────────────────────────────────

LOAI_VAN_BAN = {
    'TT':    'Thông tư',
    'ND':    'Nghị định',
    'QD':    'Quyết định',
    'TTLT':  'Thông tư liên tịch',
    'CT':    'Chỉ thị',
    'NQ':    'Nghị quyết',
    'PL':    'Pháp lệnh',
    'QH':    'Luật',        # QH13, QH14, QH15...
    'UBTVQH': 'Nghị quyết UBTVQH',
}

CO_QUAN_BAN_HANH = {
    'BGTVT':  'Bộ Giao thông Vận tải',
    'BTC':    'Bộ Tài chính',
    'BCA':    'Bộ Công an',
    'BYT':    'Bộ Y tế',
    'BLDTBXH':'Bộ Lao động Thương binh và Xã hội',
    'BCT':    'Bộ Công Thương',
    'BNN':    'Bộ Nông nghiệp và Phát triển nông thôn',
    'BTNMT':  'Bộ Tài nguyên và Môi trường',
    'BXD':    'Bộ Xây dựng',
    'BGDDT':  'Bộ Giáo dục và Đào tạo',
    'BNV':    'Bộ Nội vụ',
    'BNG':    'Bộ Ngoại giao',
    'BTP':    'Bộ Tư pháp',
    'BKHDT':  'Bộ Kế hoạch và Đầu tư',
    'BKHCN':  'Bộ Khoa học và Công nghệ',
    'BTTTT':  'Bộ Thông tin và Truyền thông',
    'BQP':    'Bộ Quốc phòng',
    'CP':     'Chính phủ',
    'TTg':    'Thủ tướng Chính phủ',
    'UBND':   'Ủy ban Nhân dân',
    'NHNN':   'Ngân hàng Nhà nước',
    'TANDTC': 'Tòa án Nhân dân Tối cao',
    'VKSNDTC':'Viện Kiểm sát Nhân dân Tối cao',
}


# Mapping tên văn bản dạng gạch dưới tiếng Việt → (tên đầy đủ, ký hiệu)
LOAI_TEN_VIET = {
    'nghi_dinh':           ('Nghị định',          'NĐ-CP'),
    'thong_tu':            ('Thông tư',            'TT'),
    'quyet_dinh':          ('Quyết định',          'QĐ'),
    'thong_tu_lien_tich':  ('Thông tư liên tịch',  'TTLT'),
    'chi_thi':             ('Chỉ thị',             'CT'),
    'nghi_quyet':          ('Nghị quyết',          'NQ'),
    'phap_lenh':           ('Pháp lệnh',           'PL'),
    'luat':                ('Luật',                ''),
    'bo_luat':             ('Bộ luật',             ''),
}

# Chuẩn hóa ký hiệu loại VB từ tiếng Anh không dấu → có dấu
KY_HIEU_CHUAN = {
    'ND': 'NĐ', 'QD': 'QĐ', 'TT': 'TT',
    'TTLT': 'TTLT', 'CT': 'CT', 'NQ': 'NQ', 'PL': 'PL',
    'QH': 'QH',  # giữ nguyên, số khóa QH gắn liền: QH13, QH14...
}


def extract_law_id(filename: str) -> str:
    """
    Tự động parse tên file thành ký hiệu văn bản chuẩn.

    Hỗ trợ 2 định dạng:

    1. Dạng mã số:    01_2020_TT-BGTVT_433944  → Thông tư 01/2020/TT-BGTVT
                      100_2019_ND-CP_123456    → Nghị định 100/2019/NĐ-CP
                      15_2022_QD-TTg_987654    → Quyết định 15/2022/QĐ-TTg

    2. Dạng tên Việt: nghi_dinh_11_2010        → Nghị định 11/2010/NĐ-CP
                      thong_tu_01_2020         → Thông tư 01/2020/TT
                      thong_tu_lien_tich_32_2021 → Thông tư liên tịch 32/2021/TTLT

    Fallback: trả về tên gốc nếu không khớp cả hai.
    """
    stem = filename.replace('.txt', '').strip('_')

    # ── Dạng 2: tên tiếng Việt ──
    # Thử từ dài nhất trước để tránh nhầm "thong_tu_lien_tich" thành "thong_tu"
    for key in sorted(LOAI_TEN_VIET, key=len, reverse=True):
        prefix = key + '_'
        if stem.startswith(prefix):
            rest = stem[len(prefix):]

            # Dạng 2a: nghi_dinh_11_2010  → Nghị định 11/2010/NĐ-CP
            m = re.match(r'^(\d+)_(\d{4})$', rest)
            if m:
                so, nam = m.group(1), m.group(2)
                ten, ky_hieu = LOAI_TEN_VIET[key]
                if ky_hieu:
                    return f"{ten} {so}/{nam}/{ky_hieu}"
                else:
                    return f"{ten} {nam}"

            # Dạng 2b: nghi_dinh_36-CP_29051995  → Nghị định 36/CP
            # (văn bản cũ trước 2004, ký hiệu không có năm)
            m = re.match(r'^(\d+)-([A-Za-z]+)_(\d{8})$', rest)
            if m:
                so, cq, ngay = m.group(1), m.group(2), m.group(3)
                ten, _ = LOAI_TEN_VIET[key]
                return f"{ten} {so}/{cq}"

            # Dạng 2c: chi_thi_bgtvt → "Chỉ thị BGTVT" (tên file không có số/năm)
            ten, ky_hieu = LOAI_TEN_VIET[key]
            co_quan = CO_QUAN_BAN_HANH.get(rest.upper(), rest.upper())
            return f"{ten} {co_quan}" 

    # ── Dạng 1: mã số ──
    stem_clean = re.sub(r'_\d{5,}$', '', stem)  # bỏ ID cuối

    # Dạng 1a: Luật Quốc hội — 48_2014_QH13
    m_qh = re.match(r'^(\d+)_(\d{4})_(QH\d+)$', stem_clean, re.IGNORECASE)
    if m_qh:
        so_hieu = m_qh.group(1)
        nam     = m_qh.group(2)
        khoa_qh = m_qh.group(3).upper()   # QH13, QH14...
        return f"Luật số {so_hieu}/{nam}/{khoa_qh}"

    m = re.match(r'^(\d+)_(\d{4})_([A-Za-z]+(?:-[A-Za-z]+)*)$', stem_clean)
    if m:
        so_hieu     = m.group(1)
        nam         = m.group(2)
        loai_coquan = m.group(3)               # giữ nguyên case gốc

        # Trường hợp đặc biệt: QH13, QH14, QH15... (Quốc hội + số khóa liền nhau)
        qh_match = re.match(r'^(QH)(\d+)$', loai_coquan, re.IGNORECASE)
        if qh_match:
            loai_ten = 'Luật'
            ky_hieu_chuan = loai_coquan.upper()   # QH13, QH14...
            return f"{loai_ten} số {so_hieu}/{nam}/{ky_hieu_chuan}"

        parts     = loai_coquan.split('-')
        loai_code = parts[0].upper()
        cq_codes  = parts[1:] if len(parts) > 1 else []

        loai_ten      = LOAI_VAN_BAN.get(loai_code, loai_code)
        loai_ky_hieu  = KY_HIEU_CHUAN.get(loai_code, loai_code)
        ky_hieu_chuan = f"{loai_ky_hieu}-{'-'.join(cq_codes)}" if cq_codes else loai_ky_hieu

        return f"{loai_ten} {so_hieu}/{nam}/{ky_hieu_chuan}"

    # Dạng 1c: không có năm — 8_CT-BGTVT_585295 → Chỉ thị 8/CT-BGTVT
    m = re.match(r'^(\d+)_([A-Za-z]+(?:-[A-Za-z]+)*)$', stem_clean)
    if m:
        so_hieu     = m.group(1)
        loai_coquan = m.group(2)

        parts     = loai_coquan.split('-')
        loai_code = parts[0].upper()
        cq_codes  = parts[1:] if len(parts) > 1 else []

        loai_ten      = LOAI_VAN_BAN.get(loai_code, loai_code)
        loai_ky_hieu  = KY_HIEU_CHUAN.get(loai_code, loai_code)
        ky_hieu_chuan = f"{loai_ky_hieu}-{'-'.join(cq_codes)}" if cq_codes else loai_ky_hieu

        return f"{loai_ten} {so_hieu}/{ky_hieu_chuan}"

    # ── Fallback ──
    return stem


# ──────────────────────────────────────────────
# Nhận diện loại & cấu trúc văn bản
# ──────────────────────────────────────────────

# Regex nhận diện các đơn vị cấu trúc
RE_DIEU      = re.compile(r'(?=\nĐiều \d+[\.\:]?)', re.IGNORECASE)
RE_DIEU_HEAD = re.compile(r'^Điều (\d+)', re.IGNORECASE)
RE_CHUONG    = re.compile(r'^(Chương\s+\w+[\s\S]*?)$', re.IGNORECASE | re.MULTILINE)
RE_MUC_SO    = re.compile(r'^(\d+\.\s+[^\n]+)', re.MULTILINE)   # 1. Tiêu đề mục…


def detect_doc_type(text: str) -> str:
    """Nhận diện loại văn bản từ nội dung đầu file."""
    upper = text[:600].upper()
    if 'CHỈ THỊ' in upper:
        return 'chi_thi'
    if 'PHÁP LỆNH' in upper or 'PHAP LENH' in upper:
        return 'phap_lenh'
    if 'NGHỊ ĐỊNH' in upper or 'NGHI DINH' in upper:
        return 'nghi_dinh'
    if 'THÔNG TƯ' in upper or 'THONG TU' in upper:
        return 'thong_tu'
    if 'QUYẾT ĐỊNH' in upper or 'QUYET DINH' in upper:
        return 'quyet_dinh'
    # Fallback: nếu có Điều thì dùng chunk theo Điều
    if RE_DIEU.search(text):
        return 'co_dieu'
    return 'chi_thi'   # mặc định dùng chunk theo mục số


def extract_chuong_map(text: str) -> dict:
    """Trả về dict {vị_trí_char: tên_chương} để tra chương gần nhất."""
    result = {}
    for m in RE_CHUONG.finditer(text):
        result[m.start()] = m.group(1).strip()
    return result


def find_nearest_chuong(pos: int, chuong_map: dict) -> str:
    """Tìm chương gần nhất (trước vị trí pos)."""
    label = ''
    for cp in sorted(chuong_map):
        if cp < pos:
            label = chuong_map[cp]
        else:
            break
    return label


# ──────────────────────────────────────────────
# Chunker
# ──────────────────────────────────────────────

@dataclass
class LawChunk:
    text:        str
    source_file: str   # "01_2020_TT-BGTVT_433944.txt"
    dieu_number: str   # "Điều 5" / "Mục 3" / "Phần mở đầu"
    full_ref:    str   # "Thông tư 01/2020/TT-BGTVT, Điều 5, Khoản 2"


# ── Chunk theo Điều (Pháp lệnh, Nghị định, Thông tư, Luật…) ──

def chunk_by_dieu(text: str, source_file: str,
                  min_chars: int = 80) -> List[LawChunk]:
    """
    Split theo Điều; giữ nguyên toàn bộ nội dung mỗi Điều dù dài.
    Mỗi chunk có prefix '[Nguồn: ...]' để model biết context.
    """
    law_id     = extract_law_id(source_file)
    chuong_map = extract_chuong_map(text)
    chunks     = []

    dieu_blocks = RE_DIEU.split(text)

    for block in dieu_blocks:
        block = block.strip()
        if not block or len(block) < min_chars:
            continue

        m        = RE_DIEU_HEAD.match(block)
        dieu_num = f"Điều {m.group(1)}" if m else "Điều ?"

        pos      = text.find(block[:60])
        base_ref = f"{law_id}, {dieu_num}"

        chunks.append(LawChunk(
            text=f"[Nguồn: {base_ref}]\n{block}",
            source_file=source_file,
            dieu_number=dieu_num,
            full_ref=base_ref,
        ))

    return chunks


# ── Chunk theo mục số cấp 1 (Chỉ thị, Quyết định dạng mục…) ──

def chunk_by_section(text: str, source_file: str,
                     min_chars: int = 80) -> List[LawChunk]:
    """
    Split theo mục số cấp 1 (1. … 2. … 3. …).
    Giữ nguyên toàn bộ nội dung mỗi mục dù dài.
    """
    law_id = extract_law_id(source_file)
    chunks = []

    parts = RE_MUC_SO.split(text)
    # parts = [phần mở đầu, "1. Tiêu đề", nội dung, "2. Tiêu đề", nội dung …]

    # Phần mở đầu (trước mục 1)
    intro = parts[0].strip()
    if len(intro) >= min_chars:
        ref = f"{law_id}, Phần mở đầu"
        chunks.append(LawChunk(
            text=f"[Nguồn: {ref}]\n{intro}",
            source_file=source_file,
            dieu_number="Phần mở đầu",
            full_ref=ref,
        ))

    # Các mục số
    i = 1
    while i < len(parts) - 1:
        sec_header = parts[i].strip()       # "1. Tên mục"
        sec_body   = parts[i + 1].strip()   # nội dung mục
        full_block = f"{sec_header}\n{sec_body}"
        ref        = f"{law_id}, {sec_header[:80]}"
        dieu_num   = sec_header[:80]

        if len(full_block) >= min_chars:
            chunks.append(LawChunk(
                text=f"[Nguồn: {ref}]\n{full_block}",
                source_file=source_file,
                dieu_number=dieu_num,
                full_ref=ref,
            ))
        i += 2

    return chunks


# ── Router: chọn chunker phù hợp theo loại văn bản ──

def chunk_file(source_file: str, text: str,
               min_chars: int = 80) -> List[LawChunk]:
    """
    Tự động chọn chiến lược chunk dựa trên loại văn bản.

    - Pháp lệnh / Nghị định / Thông tư / Luật / Quyết định (có Điều):
        → chunk_by_dieu
    - Chỉ thị / văn bản dạng mục số (không có Điều hoặc ít Điều):
        → chunk_by_section
    """
    doc_type = detect_doc_type(text)

    if doc_type in ('phap_lenh', 'nghi_dinh', 'thong_tu', 'co_dieu'):
        return chunk_by_dieu(text, source_file, min_chars)

    if doc_type in ('chi_thi', 'quyet_dinh'):
        # Nếu vẫn có Điều (QĐ dạng ban hành kèm quy định) → ưu tiên chunk_by_dieu
        if RE_DIEU.search(text):
            return chunk_by_dieu(text, source_file, min_chars)
        return chunk_by_section(text, source_file, min_chars)

    # Fallback chung
    if RE_DIEU.search(text):
        return chunk_by_dieu(text, source_file, min_chars)
    return chunk_by_section(text, source_file, min_chars)


# ──────────────────────────────────────────────
# Build chunks.jsonl
# ──────────────────────────────────────────────

def build_chunks_jsonl(clean_dir: str = './txt',
                       out_path:  str = './chithi/chunks.jsonl',
                       min_chars: int = 80):
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    all_chunks = []

    for fname in sorted(os.listdir(clean_dir)):
        if not fname.endswith('.txt'):
            continue
        with open(os.path.join(clean_dir, fname), encoding='utf-8') as f:
            text = f.read()

        chunks = chunk_file(fname, text, min_chars)
        all_chunks.extend(chunks)
        print(f"  {fname:45s} → {extract_law_id(fname):40s}  ({len(chunks)} chunks)")

    with open(out_path, 'w', encoding='utf-8') as f:
        for c in all_chunks:
            f.write(json.dumps({
                'text':   c.text,
                'source': c.source_file,
                'ref':    c.full_ref,
            }, ensure_ascii=False) + '\n')

    print(f"\n✅ Total: {len(all_chunks)} chunks → {out_path}")


if __name__ == '__main__':
    build_chunks_jsonl()