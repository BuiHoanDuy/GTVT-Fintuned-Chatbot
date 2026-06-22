#!/usr/bin/env python3
"""
Chuyển đổi hàng loạt file .docx sang .txt
Cách dùng:
  python docx_to_txt.py                         # chuyển tất cả .docx trong thư mục hiện tại
  python docx_to_txt.py --input /path/to/folder # chỉ định thư mục đầu vào
  python docx_to_txt.py --output /path/to/out   # chỉ định thư mục đầu ra
  python docx_to_txt.py --input . --output txt_files --recursive
"""

import argparse
import subprocess
import sys
from pathlib import Path


def convert_docx_to_txt(docx_path: Path, output_dir: Path) -> tuple[bool, str]:
    """Chuyển một file .docx sang .txt dùng pandoc."""
    txt_name = docx_path.stem + ".txt"
    txt_path = output_dir / txt_name

    try:
        result = subprocess.run(
            ["pandoc", str(docx_path), "-t", "plain", "--wrap=none", "-o", str(txt_path)],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            return True, str(txt_path)
        else:
            return False, result.stderr.strip()
    except FileNotFoundError:
        return False, "Không tìm thấy pandoc. Cài đặt: https://pandoc.org/installing.html"
    except subprocess.TimeoutExpired:
        return False, "Timeout khi xử lý file"
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(
        description="Chuyển đổi hàng loạt file .docx sang .txt"
    )
    parser.add_argument(
        "--input", "-i",
        default=".",
        help="Thư mục chứa file .docx (mặc định: thư mục hiện tại)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Thư mục lưu file .txt (mặc định: cùng thư mục với file gốc)"
    )
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        help="Tìm kiếm file .docx trong tất cả thư mục con"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Ghi đè file .txt nếu đã tồn tại (mặc định: bỏ qua)"
    )
    args = parser.parse_args()

    input_dir = Path(args.input).resolve()
    if not input_dir.exists():
        print(f"❌ Thư mục không tồn tại: {input_dir}")
        sys.exit(1)

    # Tìm tất cả file .docx
    pattern = "**/*.docx" if args.recursive else "*.docx"
    docx_files = sorted(input_dir.glob(pattern))

    # Lọc bỏ file tạm của Word (bắt đầu bằng ~$)
    docx_files = [f for f in docx_files if not f.name.startswith("~$")]

    if not docx_files:
        print(f"⚠️  Không tìm thấy file .docx nào trong: {input_dir}")
        sys.exit(0)

    print(f"📂 Thư mục đầu vào : {input_dir}")
    print(f"🔍 Tìm thấy        : {len(docx_files)} file .docx")

    # Thiết lập thư mục đầu ra
    if args.output:
        global_output_dir = Path(args.output).resolve()
        global_output_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Thư mục đầu ra  : {global_output_dir}")
    else:
        global_output_dir = None
        print(f"📁 Thư mục đầu ra  : cùng thư mục với file gốc")

    print("-" * 50)

    ok_count = 0
    skip_count = 0
    fail_count = 0

    for docx_path in docx_files:
        output_dir = global_output_dir if global_output_dir else docx_path.parent
        txt_path = output_dir / (docx_path.stem + ".txt")

        # Kiểm tra file đã tồn tại
        if txt_path.exists() and not args.overwrite:
            print(f"⏭️  Bỏ qua  : {docx_path.name}  (đã có {txt_path.name})")
            skip_count += 1
            continue

        print(f"🔄 Đang xử lý: {docx_path.name} ...", end=" ", flush=True)
        success, info = convert_docx_to_txt(docx_path, output_dir)

        if success:
            print(f"✅ → {txt_path.name}")
            ok_count += 1
        else:
            print(f"❌ Lỗi: {info}")
            fail_count += 1

    print("-" * 50)
    print(f"✅ Thành công : {ok_count}")
    print(f"⏭️  Bỏ qua    : {skip_count}")
    print(f"❌ Thất bại  : {fail_count}")
    print(f"📊 Tổng cộng : {len(docx_files)}")


if __name__ == "__main__":
    main()