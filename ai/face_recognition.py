from __future__ import annotations

import base64
import pickle
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import numpy as np
from PIL import Image

from config.setting import AI_DATASET_DIR, FACE_RECOGNITION_TOLERANCE
from database.models import Student, db


def _get_face_recognition_lib() -> Any:
    """
    Import thư viện face_recognition một cách an toàn.
    Tránh nhầm với file local cùng tên trong thư mục ai/.
    """
    import importlib

    module = importlib.import_module("face_recognition")
    if not hasattr(module, "face_encodings"):
        raise ImportError("Khong tim thay thu vien face_recognition hop le.")
    return module


def _decode_base64_to_rgb(base64_image: str) -> Optional[np.ndarray]:
    """Giải mã ảnh base64 thành ảnh RGB (numpy array)."""
    try:
        raw_bytes = base64.b64decode(base64_image)
        image = Image.open(BytesIO(raw_bytes)).convert("RGB")
        return np.array(image)
    except Exception as exc:
        print(f"[AI] Loi decode base64: {exc}", flush=True)
        return None


def load_known_faces() -> int:
    """
    Load toàn bộ ảnh trong dataset, encode khuôn mặt và lưu vào DB.

    Quy ước tên file: <student_id>.jpg hoặc <student_id>_anything.jpg.
    Trả về số lượng bản ghi được cập nhật face_encoding.
    """
    try:
        fr = _get_face_recognition_lib()
    except ImportError as exc:
        print(f"[AI] {exc}", flush=True)
        return 0

    dataset_dir = Path(AI_DATASET_DIR)
    if not dataset_dir.exists():
        print(f"[AI] Khong tim thay dataset: {dataset_dir}", flush=True)
        return 0

    updated_count = 0
    image_paths = list(dataset_dir.glob("*.*"))
    if not image_paths:
        print("[AI] Dataset rong, khong co anh de encode.", flush=True)
        return 0

    for image_path in image_paths:
        student_id = image_path.stem.split("_")[0]
        try:
            student = Student.query.filter_by(student_id=student_id).first()
            if not student:
                print(f"[AI] Bo qua {image_path.name}: khong co student_id={student_id} trong DB.", flush=True)
                continue

            image = fr.load_image_file(str(image_path))
            encodings = fr.face_encodings(image)
            if not encodings:
                print(f"[AI] Bo qua {image_path.name}: khong tim thay khuon mat.", flush=True)
                continue

            student.face_encoding = pickle.dumps(encodings[0])
            student.face_image_path = str(image_path)
            updated_count += 1
            print(f"[AI] Da encode: {student_id}", flush=True)
        except Exception as exc:
            print(f"[AI] Loi encode {image_path.name}: {exc}", flush=True)

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        print(f"[AI] Loi commit DB: {exc}", flush=True)
        return 0

    print(f"[AI] Hoan tat encode dataset. So luong cap nhat: {updated_count}", flush=True)
    return updated_count


def recognize_face_from_base64(base64_image: str) -> Optional[str]:
    """
    Nhận ảnh base64 từ backend và trả về student_id nếu nhận diện thành công.
    """
    if not base64_image:
        return None

    try:
        fr = _get_face_recognition_lib()
    except ImportError as exc:
        print(f"[AI] {exc}", flush=True)
        return None

    image_rgb = _decode_base64_to_rgb(base64_image)
    if image_rgb is None:
        return None

    try:
        unknown_encodings = fr.face_encodings(image_rgb)
        if not unknown_encodings:
            print("[AI] Anh dau vao khong co khuon mat.", flush=True)
            return None
        unknown_encoding = unknown_encodings[0]

        students = Student.query.filter(Student.face_encoding.isnot(None), Student.is_active.is_(True)).all()
        if not students:
            print("[AI] DB chua co du lieu face_encoding.", flush=True)
            return None

        known_encodings: list[np.ndarray] = []
        known_student_ids: list[str] = []
        for student in students:
            try:
                known_encodings.append(pickle.loads(student.face_encoding))
                known_student_ids.append(student.student_id)
            except Exception:
                continue

        if not known_encodings:
            return None

        distances = fr.face_distance(known_encodings, unknown_encoding)
        best_idx = int(np.argmin(distances))
        best_distance = float(distances[best_idx])
        if best_distance <= FACE_RECOGNITION_TOLERANCE:
            return known_student_ids[best_idx]
        return None
    except Exception as exc:
        print(f"[AI] Loi nhan dien khuon mat: {exc}", flush=True)
        return None


def encode_and_save_to_db(student_id: str, image_path: str) -> bool:
    """
    Đăng ký khuôn mặt mới cho student_id từ file ảnh, sau đó lưu encoding vào DB.
    """
    if not student_id or not image_path:
        print("[AI] Thieu student_id hoac image_path.", flush=True)
        return False

    try:
        fr = _get_face_recognition_lib()
    except ImportError as exc:
        print(f"[AI] {exc}", flush=True)
        return False

    try:
        student = Student.query.filter_by(student_id=student_id).first()
        if not student:
            print(f"[AI] Khong tim thay student_id={student_id} trong DB.", flush=True)
            return False

        image = fr.load_image_file(image_path)
        encodings = fr.face_encodings(image)
        if not encodings:
            print("[AI] Anh dang ky khong co khuon mat hop le.", flush=True)
            return False

        student.face_encoding = pickle.dumps(encodings[0])
        student.face_image_path = image_path
        db.session.commit()
        print(f"[AI] Dang ky khuon mat thanh cong cho {student_id}.", flush=True)
        return True
    except Exception as exc:
        db.session.rollback()
        print(f"[AI] Loi encode_and_save_to_db: {exc}", flush=True)
        return False


def encode_base64_and_save_to_db(student_id: str, base64_image: str) -> bool:
    """
    Đăng ký khuôn mặt mới từ ảnh base64 và lưu face_encoding vào DB.
    """
    if not student_id or not base64_image:
        print("[AI] Thieu student_id hoac base64_image.", flush=True)
        return False

    try:
        fr = _get_face_recognition_lib()
    except ImportError as exc:
        print(f"[AI] {exc}", flush=True)
        return False

    image_rgb = _decode_base64_to_rgb(base64_image)
    if image_rgb is None:
        return False

    try:
        student = Student.query.filter_by(student_id=student_id).first()
        if not student:
            print(f"[AI] Khong tim thay student_id={student_id} trong DB.", flush=True)
            return False

        encodings = fr.face_encodings(image_rgb)
        if not encodings:
            print("[AI] Anh dang ky khong co khuon mat hop le.", flush=True)
            return False

        student.face_encoding = pickle.dumps(encodings[0])
        db.session.commit()
        print(f"[AI] Dang ky khuon mat qua base64 thanh cong cho {student_id}.", flush=True)
        return True
    except Exception as exc:
        db.session.rollback()
        print(f"[AI] Loi encode_base64_and_save_to_db: {exc}", flush=True)
        return False
