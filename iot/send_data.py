from __future__ import annotations

from typing import Any

import requests

# Ưu tiên đọc cấu hình tập trung từ config/setting.py.
try:
    from config.setting import HOST, PORT
except Exception:
    HOST = "127.0.0.1"
    PORT = 5000

BASE_URL = f"http://{HOST}:{PORT}"
URL_FACE = f"{BASE_URL}/face-auth"
URL_QR = f"{BASE_URL}/qr-auth"
REQUEST_TIMEOUT = 10


def _handle_response(response: requests.Response) -> dict[str, Any]:
    """Chuẩn hóa dữ liệu trả về từ backend để phía IoT xử lý thống nhất."""
    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if response.ok:
        if isinstance(payload, dict):
            return payload
        return {"status": "success", "data": payload}

    message = (
        payload.get("message")
        if isinstance(payload, dict)
        else f"HTTP {response.status_code}"
    )
    return {"status": "fail", "message": message or f"HTTP {response.status_code}"}


def send_face_data(image_base64: str) -> dict[str, Any]:
    """Gửi ảnh base64 lên API `/face-auth` để xác thực khuôn mặt."""
    if not image_base64:
        return {"status": "fail", "message": "Image base64 trống."}

    try:
        print("[IOT] Dang gui anh len backend /face-auth ...", flush=True)
        response = requests.post(
            URL_FACE,
            json={"image": image_base64},
            timeout=REQUEST_TIMEOUT,
        )
        result = _handle_response(response)
        print(f"[IOT] Face API response: {result}", flush=True)
        return result
    except requests.Timeout:
        return {"status": "fail", "message": "Timeout khi goi /face-auth (10s)."}
    except requests.RequestException as exc:
        return {"status": "fail", "message": f"Loi ket noi backend: {exc}"}


def send_qr_data(qr_code_text: str) -> dict[str, Any]:
    """Giữ lại hàm QR để tương thích, gửi dữ liệu qua API `/qr-auth`."""
    if not qr_code_text:
        return {"status": "fail", "message": "QR code trống."}

    try:
        print("[IOT] Dang gui QR len backend /qr-auth ...", flush=True)
        response = requests.post(
            URL_QR,
            json={"qr_code": qr_code_text},
            timeout=REQUEST_TIMEOUT,
        )
        result = _handle_response(response)
        print(f"[IOT] QR API response: {result}", flush=True)
        return result
    except requests.Timeout:
        return {"status": "fail", "message": "Timeout khi goi /qr-auth (10s)."}
    except requests.RequestException as exc:
        return {"status": "fail", "message": f"Loi ket noi backend: {exc}"}