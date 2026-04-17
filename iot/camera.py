from __future__ import annotations

import base64
import time
from typing import Any, Optional

import cv2

try:
    from iot.send_data import send_face_data
except ImportError:
    from send_data import send_face_data


def capture_image(preview_seconds: float = 2.5, camera_index: int = 0) -> Optional[Any]:
    """
    Mở webcam và chụp 1 khung hình cuối sau thời gian preview.
    Trả về frame (numpy array) hoặc None nếu thất bại.
    """
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("FAIL: Không mở được camera.", flush=True)
        return None

    frame: Optional[Any] = None
    try:
        # Preview ngắn để người dùng chuẩn bị trước khi chụp.
        start_time = time.time()
        while (time.time() - start_time) < preview_seconds:
            ret, img = cap.read()
            if not ret:
                print("FAIL: Không đọc được frame từ camera.", flush=True)
                return None
            frame = img
            cv2.imshow("Security Gate - Chuan bi chup", frame)
            cv2.waitKey(1)
    except Exception as exc:
        print(f"FAIL: Lỗi khi chụp ảnh: {exc}", flush=True)
        return None
    finally:
        cap.release()
        cv2.destroyAllWindows()

    if frame is None:
        print("FAIL: Không có ảnh đầu vào.", flush=True)
    return frame


def image_to_base64(frame: Any) -> Optional[str]:
    """
    Chuyển frame OpenCV sang chuỗi base64 thuần (không kèm data header).
    """
    try:
        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            print("FAIL: Mã hóa ảnh JPG thất bại.", flush=True)
            return None
        return base64.b64encode(buffer).decode("utf-8")
    except Exception as exc:
        print(f"FAIL: Lỗi khi convert ảnh sang base64: {exc}", flush=True)
        return None


def process_security_gate() -> dict[str, Any]:
    """
    Luồng IoT chuẩn: Chụp ảnh -> convert base64 -> gọi API /face-auth.
    """
    frame = capture_image()
    if frame is None:
        return {"status": "fail", "message": "Camera Error"}

    image_base64 = image_to_base64(frame)
    if not image_base64:
        return {"status": "fail", "message": "Encode Image Error"}

    result = send_face_data(image_base64)
    if result.get("status") == "success":
        print(f"SUCCESS_FACE: {result.get('name', 'Unknown')}", flush=True)
    else:
        print(f"FAIL: {result.get('message', 'Unauthorized')}", flush=True)
    return result


def main() -> None:
    """Điểm chạy độc lập cho module camera."""
    process_security_gate()


if __name__ == "__main__":
    main()