from __future__ import annotations

from typing import Any

try:
    from iot.camera import capture_image, image_to_base64
    from iot.send_data import send_face_data
except ImportError:
    from camera import capture_image, image_to_base64
    from send_data import send_face_data


def run_test() -> dict[str, Any]:
    """
    Test độc lập cho luồng IoT:
    Camera -> base64 -> Backend /face-auth.
    """
    print("[TEST] Bat dau test camera + face-auth...", flush=True)

    frame = capture_image()
    if frame is None:
        result = {"status": "fail", "message": "Khong chup duoc anh tu camera."}
        print(f"[TEST] Ket qua: {result}", flush=True)
        return result

    image_base64 = image_to_base64(frame)
    if not image_base64:
        result = {"status": "fail", "message": "Convert base64 that bai."}
        print(f"[TEST] Ket qua: {result}", flush=True)
        return result

    result = send_face_data(image_base64)
    print(f"[TEST] Ket qua cuoi cung: {result}", flush=True)
    return result


def main() -> None:
    run_test()


if __name__ == "__main__":
    main()
