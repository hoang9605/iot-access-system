from __future__ import annotations

import base64
from pathlib import Path

import requests

from config.setting import API_BASE_URL, REQUEST_TIMEOUT


def test_face_auth_with_image(image_path: str) -> dict:
    """Đọc ảnh từ máy, convert base64 và gọi API /face-auth."""
    path = Path(image_path)
    if not path.exists():
        return {"status": "fail", "message": f"Khong tim thay file: {image_path}"}

    try:
        image_base64 = base64.b64encode(path.read_bytes()).decode("utf-8")
        response = requests.post(
            f"{API_BASE_URL}/face-auth",
            json={"image": image_base64},
            timeout=REQUEST_TIMEOUT,
        )
        return response.json()
    except requests.Timeout:
        return {"status": "fail", "message": "Timeout khi goi /face-auth."}
    except requests.RequestException as exc:
        return {"status": "fail", "message": f"Loi ket noi backend: {exc}"}
    except ValueError:
        return {"status": "fail", "message": "Backend tra ve JSON khong hop le."}


def main() -> None:
    image_path = input("Nhap duong dan anh can test nhan dien: ").strip()
    if not image_path:
        print("[TEST] Ban chua nhap duong dan anh.", flush=True)
        return

    result = test_face_auth_with_image(image_path)
    print(f"[TEST] Ket qua /face-auth: {result}", flush=True)


if __name__ == "__main__":
    main()
