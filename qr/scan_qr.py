from __future__ import annotations

from typing import Any, Optional

import cv2
import requests
from pyzbar.pyzbar import decode

from config.setting import API_BASE_URL, REQUEST_TIMEOUT

QR_AUTH_URL = f"{API_BASE_URL}/qr-auth"


def scan_qr_from_camera(camera_index: int = 0) -> Optional[str]:
    """Mở webcam và quét QR, trả về nội dung QR đầu tiên."""
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("[QR] Khong mo duoc camera.", flush=True)
        return None

    print("[QR] Dang quet... Nhan phim 'q' de thoat.", flush=True)
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[QR] Khong doc duoc frame.", flush=True)
                return None

            qr_codes = decode(frame)
            if qr_codes:
                qr_text = qr_codes[0].data.decode("utf-8")
                print(f"[QR] Da quet duoc: {qr_text}", flush=True)
                return qr_text

            cv2.imshow("QR Scanner", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                return None
    finally:
        cap.release()
        cv2.destroyAllWindows()


def send_qr_to_backend(qr_code: str) -> dict[str, Any]:
    """Gửi QR code lên backend API /qr-auth."""
    if not qr_code:
        return {"status": "fail", "message": "QR code trong."}

    try:
        response = requests.post(
            QR_AUTH_URL,
            json={"qr_code": qr_code},
            timeout=REQUEST_TIMEOUT,
        )
        return response.json()
    except requests.Timeout:
        return {"status": "fail", "message": "Timeout khi goi /qr-auth."}
    except requests.RequestException as exc:
        return {"status": "fail", "message": f"Loi ket noi backend: {exc}"}
    except ValueError:
        return {"status": "fail", "message": "Backend tra ve JSON khong hop le."}


def main() -> None:
    qr_code = scan_qr_from_camera()
    if not qr_code:
        print("[QR] Khong co du lieu QR de gui.", flush=True)
        return

    result = send_qr_to_backend(qr_code)
    print(f"[QR] Ket qua xac thuc: {result}", flush=True)


if __name__ == "__main__":
    main()
