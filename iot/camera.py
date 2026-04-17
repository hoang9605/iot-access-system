from __future__ import annotations

import base64
import time
from typing import Any, Optional

import cv2
import sys

try:
    from iot.send_data import send_face_data
except ImportError:
    from send_data import send_face_data


def _print_safe(message: str) -> None:
    """
    In stdout an toàn trên Windows terminal.

    Tránh UnicodeEncodeError khi console dùng encoding cp1252/cp850 nhưng nội dung có tiếng Việt.
    Listener sẽ đọc stdout của `camera.py`, nên vẫn giữ format "SUCCESS_FACE: ..." / "FAIL: ...".
    """

    try:
        sys.stdout.buffer.write((message + "\n").encode("utf-8", errors="replace"))
        sys.stdout.flush()
    except Exception:
        try:
            print(message, flush=True)
        except Exception:
            pass


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


def capture_image_when_stable(
    camera_index: int = 0,
    stable_seconds: float = 0.7,
    max_seconds: float = 8.0,
    motion_threshold: float = 1.2,
) -> Optional[Any]:
    """
    Bật camera NGAY và chỉ chụp khi khung hình ổn định (người đã đứng yên).

    Ý tưởng:
    - Luôn hiển thị live preview ngay khi mở camera.
    - Ước lượng mức "chuyển động" bằng sai khác giữa 2 frame liên tiếp (grayscale + blur).
    - Khi motion thấp liên tục trong stable_seconds => coi như đứng yên => chụp.
    - Nếu quá max_seconds vẫn chưa ổn định => chụp frame hiện tại để tránh treo.

    Tham số:
    - motion_threshold: ngưỡng "mức chuyển động" (giá trị trung bình absdiff). Tăng nếu quá nhạy.
    """

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        _print_safe("FAIL: Không mở được camera.")
        return None

    start = time.time()
    last_gray = None
    stable_since: Optional[float] = None
    last_frame: Optional[Any] = None
    window_name = "Security Gate"
    try:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    except Exception:
        pass

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                _print_safe("FAIL: Không đọc được frame từ camera.")
                return None

            last_frame = frame
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            motion_level = None
            if last_gray is not None:
                diff = cv2.absdiff(last_gray, gray)
                motion_level = float(diff.mean())

                if motion_level <= motion_threshold:
                    if stable_since is None:
                        stable_since = time.time()
                else:
                    stable_since = None

            last_gray = gray

            # Live preview luôn bật ngay khi có người lại gần.
            overlay = "Dang quan sat (dung yen de chup)"
            if motion_level is not None:
                overlay += f" | motion={motion_level:.2f}"
            cv2.putText(
                frame,
                overlay,
                (12, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )
            cv2.imshow(window_name, frame)
            cv2.waitKey(1)

            now = time.time()
            if stable_since is not None and (now - stable_since) >= stable_seconds:
                return last_frame

            if (now - start) >= max_seconds:
                return last_frame
    except Exception as exc:
        _print_safe(f"FAIL: Lỗi khi quan sát ổn định: {exc}")
        return None
    finally:
        cap.release()
        cv2.destroyAllWindows()


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
    # Bật camera ngay khi trigger, chụp khi người đứng yên.
    frame = capture_image_when_stable()
    if frame is None:
        return {"status": "fail", "message": "Camera Error"}

    image_base64 = image_to_base64(frame)
    if not image_base64:
        return {"status": "fail", "message": "Encode Image Error"}

    result = send_face_data(image_base64)
    if result.get("status") == "success":
        _print_safe(f"SUCCESS_FACE: {result.get('name', 'Unknown')}")
    else:
        _print_safe(f"FAIL: {result.get('message', 'Unauthorized')}")
    return result


def main() -> None:
    """Điểm chạy độc lập cho module camera."""
    process_security_gate()


if __name__ == "__main__":
    main()