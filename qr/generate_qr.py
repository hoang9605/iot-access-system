from __future__ import annotations

from pathlib import Path

import qrcode


def generate_student_qr(student_id: str, output_dir: str = "qr/output") -> Path:
    """Tạo QR chứa student_id và lưu ra file PNG."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    file_path = output_path / f"{student_id}.png"
    img = qrcode.make(student_id)
    img.save(file_path)
    print(f"[QR] Da tao QR: {file_path}", flush=True)
    return file_path


def main() -> None:
    student_id = input("Nhap student_id can tao QR: ").strip()
    if not student_id:
        print("[QR] student_id khong duoc de trong.", flush=True)
        return
    generate_student_qr(student_id)


if __name__ == "__main__":
    main()
