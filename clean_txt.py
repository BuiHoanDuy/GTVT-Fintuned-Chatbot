#!/usr/bin/env python3
"""
Làm sạch file .txt chuyển đổi từ văn bản pháp luật:
  1. Xóa ký tự thừa từ HTML (non-breaking space, zero-width space)
  2. Xóa header/footer lặp lại của website (Tải về, In trang, Lược đồ)
  3. Bỏ tất cả nội dung TRƯỚC "Điều 1"
  4. Bỏ dòng tiêu đề Chương và phụ đề cho đến khi gặp "Điều"
  5. Bỏ block "Nơi nhận" và tất cả dòng bên dưới
  6. Chuẩn hóa số điều/khoản/điểm về format thống nhất
  7. Xóa ký tự đặc biệt, giữ dấu câu thông thường
  8. Chuẩn hóa dòng trống (tối đa 2 dòng liên tiếp)

Cách dùng:
  python clean_txt.py                          # xử lý tất cả .txt trong thư mục hiện tại
  python clean_txt.py --input ./txt            # chỉ định thư mục đầu vào
  python clean_txt.py --output ./clean         # chỉ định thư mục đầu ra
  python clean_txt.py --input ./txt --inplace  # ghi đè luôn file gốc
"""

import argparse
import re
import sys
from pathlib import Path


# ──────────────────────────────────────────────
# BƯỚC 1 – Làm sạch ký tự HTML & chuẩn hóa cơ bản
# (từ clean_corpus.py)
# ──────────────────────────────────────────────

def clean_html_artifacts(text: str) -> str:
    """Xóa ký tự thừa phổ biến từ HTML."""
    text = re.sub(r'\xa0', ' ', text)    # non-breaking space → space thường
    text = re.sub(r'\u200b', '', text)   # zero-width space → xóa hẳn
    return text


def remove_website_headers(text: str) -> str:
    """Xóa các dòng header/footer lặp lại của website pháp luật."""
    text = re.sub(r'Tải về.*?\n', '', text)
    text = re.sub(r'In trang.*?\n', '', text)
    text = re.sub(r'Lược đồ.*?\n', '', text)
    return text


def normalize_dieu_khoan(text: str) -> str:
    """
    Chuẩn hóa cách viết điều/khoản/điểm về format thống nhất:
      'điều 5'   → 'Điều 5'
      'khoản 3'  → 'Khoản 3'
      'điểm a'   → 'Điểm a'
    """
    text = re.sub(r'\bđiều\s+(\d+)', r'Điều \1', text)
    text = re.sub(r'\bkhoản\s+(\d+)', r'Khoản \1', text)
    text = re.sub(r'\bđiểm\s+([a-z])\b', r'Điểm \1', text)
    return text


# ──────────────────────────────────────────────
# BƯỚC 2 – Loại bỏ phần nội dung không cần thiết
# (từ clean_txt.py)
# ──────────────────────────────────────────────

def remove_before_dieu1(text: str) -> str:
    """Bỏ tất cả nội dung trước 'Điều 1'."""
    match = re.search(r'(?i)(?=đi[eề]u\s+1\b)', text)
    if match:
        return text[match.start():]
    return text


def remove_chuong_headers(text: str) -> str:
    """
    Bỏ dòng 'Chương ...' (mọi dạng hoa/thường/La Mã/số)
    và các dòng tiêu đề phụ ngay sau, cho đến khi gặp dòng 'Điều'.
    """
    lines = text.splitlines()
    result = []
    skip = False

    for line in lines:
        stripped = line.strip()

        if re.match(r'(?i)^ch[uư][oơ]ng\b', stripped):
            skip = True
            continue

        if skip:
            if re.match(r'(?i)^đi[eề]u\b', stripped):
                skip = False
                result.append(line)
            continue  # bỏ tiêu đề phụ của chương

        result.append(line)

    return '\n'.join(result)


def remove_trailing_sections(text: str) -> str:
    """
    Cắt bỏ toàn bộ nội dung từ dòng đầu tiên khớp một trong các mẫu:
      - Dòng ngăn cách trang: bắt đầu & kết thúc bằng 3+ dấu - (vd: ---.:---)
      - 'Nơi nhận'
      - 'Phụ lục'
      - Chức danh ký tên: BỘ TRƯỞNG, KT. BỘ TRƯỞNG, THỨ TRƯỞNG, TL. BỘ TRƯỞNG,
        TỔNG CỤC TRƯỞNG, GIÁM ĐỐC, CHỦ TỊCH, HIỆU TRƯỞNG, v.v.
    Tất cả nội dung từ dòng đó trở đi đều bị xóa.
    """
    # Mẫu chức danh ký tên phổ biến trong văn bản pháp luật VN
    CHUC_DANH = re.compile(
        r'''(?ix)
        ^(
            k\.?t\.?\s+         # KT.
        )?
        (
            b[oộ]\s+tr[uưừ][oở]ng         # BỘ TRƯỞNG
            | th[uứ]\s+tr[uưừ][oở]ng      # THỨ TRƯỞNG
            | t\.?l\.?\s+b[oộ]\s+tr[uưừ][oở]ng  # TL. BỘ TRƯỞNG
            | t[oổ]ng\s+c[uụ]c\s+tr[uưừ][oở]ng    # TỔNG CỤC TRƯỞNG
            | c[uụ]c\s+tr[uưừ][oở]ng       # CỤC TRƯỞNG
            | gi[aá]m\s+[dđ][oố]c          # GIÁM ĐỐC
            | ph[oó]\s+gi[aá]m\s+[dđ][oố]c  # PHÓ GIÁM ĐỐC
            | ch[uủ]\s+t[iị]ch             # CHỦ TỊCH
            | ph[oó]\s+ch[uủ]\s+t[iị]ch  # PHÓ CHỦ TỊCH
            | hi[eệ]u\s+tr[uưừ][oở]ng     # HIỆU TRƯỞNG
            | vi[eệ]n\s+tr[uưừ][oở]ng     # VIỆN TRƯỞNG
            | ch[aá]nh\s+[aá]n            # CHÁNH ÁN
            | vi[eệ]n\s+ki[eể]m\s+s[aá]t # VIỆN KIỂM SÁT
        )\b
        ''',
    )

    lines = text.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()

        # Dòng ngăn cách: bắt đầu và kết thúc bằng 3+ dấu -
        if len(stripped) >= 5 and re.match(r'^[^a-zA-Z\u00C0-\u024F\u1E00-\u1EFF0-9]{5,}$', stripped) and stripped.count('-') + stripped.count('=') + stripped.count('_') + stripped.count('─') + stripped.count('━') >= 3:
            return '\n'.join(lines[:i])
        # Nơi nhận
        if re.match(r'(?i)^n[oơ]i\s+nh[aậ]n\b', stripped):
            return '\n'.join(lines[:i])
        # Phụ lục
        if re.match(r'(?i)^ph[uụ]\s+l[uụ]c\b', stripped):
            return '\n'.join(lines[:i])
        # Chức danh ký tên
        if CHUC_DANH.match(stripped):
            return '\n'.join(lines[:i])

    return text


# ──────────────────────────────────────────────
# BƯỚC 3 – Làm sạch ký tự & khoảng trắng
# ──────────────────────────────────────────────

def remove_special_chars(text: str) -> str:
    """
    Xóa ký tự đặc biệt, giữ lại:
      - Chữ cái Unicode (tiếng Việt đầy đủ)
      - Chữ số
      - Dấu câu thông thường: . , ; : ! ? ( ) [ ] - / %
      - Khoảng trắng và xuống dòng
    """
    cleaned = re.sub(r'[^\w\s.,;:!?()\[\]\-/%\n]', '', text, flags=re.UNICODE)
    lines = [line.strip() for line in cleaned.splitlines()]
    return '\n'.join(lines)


def normalize_blank_lines(text: str) -> str:
    """Giữ tối đa 2 dòng trống liên tiếp."""
    return re.sub(r'\n{3,}', '\n\n', text)


# ──────────────────────────────────────────────
# PIPELINE TỔNG HỢP
# ──────────────────────────────────────────────

def clean_text(text: str) -> str:
    """Áp dụng toàn bộ pipeline theo thứ tự."""
    # --- Từ clean_corpus.py ---
    text = clean_html_artifacts(text)
    text = remove_website_headers(text)

    # --- Loại bỏ phần không cần ---
    text = remove_before_dieu1(text)
    text = remove_chuong_headers(text)
    text = remove_trailing_sections(text)

    # --- Chuẩn hóa nội dung (từ clean_corpus.py) ---
    text = normalize_dieu_khoan(text)

    # --- Làm sạch ký tự & khoảng trắng ---
    text = remove_special_chars(text)
    text = normalize_blank_lines(text)

    return text.strip()


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Làm sạch file .txt văn bản pháp luật"
    )
    parser.add_argument('--input', '-i', default='./txt',
                        help='Thư mục chứa file .txt (mặc định: ./txt)')
    parser.add_argument('--output', '-o', default='./clean',
                        help='Thư mục lưu file đã làm sạch (mặc định: ./clean)')
    parser.add_argument('--inplace', action='store_true',
                        help='Ghi đè luôn file gốc')
    parser.add_argument('--overwrite', action='store_true',
                        help='Ghi đè nếu file đầu ra đã tồn tại')
    args = parser.parse_args()

    input_dir = Path(args.input).resolve()
    if not input_dir.exists():
        print(f"❌ Thư mục không tồn tại: {input_dir}")
        sys.exit(1)

    txt_files = sorted(input_dir.glob('*.txt'))
    if not txt_files:
        print(f"⚠️  Không tìm thấy file .txt nào trong: {input_dir}")
        sys.exit(0)

    output_dir: Path | None = None
    if args.inplace:
        print("📂 Chế độ: ghi đè file gốc (inplace)")
    else:
        output_dir = Path(args.output).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Thư mục đầu ra: {output_dir}")

    print(f"🔍 Tìm thấy: {len(txt_files)} file .txt")
    print('-' * 50)

    ok = skip = fail = 0

    for txt_path in txt_files:
        if args.inplace:
            out_path = txt_path
        else:
            assert output_dir is not None
            out_path = output_dir / txt_path.name

        if out_path.exists() and not args.inplace and not args.overwrite:
            print(f"⏭️  Bỏ qua  : {txt_path.name}")
            skip += 1
            continue

        print(f"🔄 Đang xử lý: {txt_path.name} ...", end=' ', flush=True)
        try:
            raw = txt_path.read_text(encoding='utf-8')
            cleaned = clean_text(raw)
            out_path.write_text(cleaned, encoding='utf-8')
            print(f"✅  {len(raw):,} → {len(cleaned):,} ký tự")
            ok += 1
        except Exception as e:
            print(f"❌ Lỗi: {e}")
            fail += 1

    print('-' * 50)
    print(f"✅ Thành công : {ok}")
    print(f"⏭️  Bỏ qua    : {skip}")
    print(f"❌ Thất bại  : {fail}")
    print(f"📊 Tổng cộng : {len(txt_files)}")


if __name__ == '__main__':
    main()