from __future__ import annotations

import base64
import sys
from pathlib import Path

from flask import Flask

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ai.face_recognition import encode_and_save_to_db, recognize_face_from_base64
from config.setting import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
from database.models import db


def _create_app() -> Flask:
    """Tạo app context để test độc lập module AI."""
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    db.init_app(app)
    return app


def test_register_and_recognize(student_id: str, image_path: str) -> None:
    """
    Test nhanh:
    1) Encode ảnh và lưu vào DB
    2) Đọc lại ảnh -> convert base64 -> nhận diện
    """
    app = _create_app()
    with app.app_context():
        db.create_all()

        ok = encode_and_save_to_db(student_id=student_id, image_path=image_path)
        print(f"[TEST-AI] Ket qua dang ky: {ok}", flush=True)
        if not ok:
            return

        image_bytes = Path(image_path).read_bytes()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        result = recognize_face_from_base64(base64_image)
        print(f"[TEST-AI] student_id nhan dien duoc: {result}", flush=True)


def main() -> None:
    student_id = input("Nhap student_id de test: ").strip()
    image_path = input("Nhap duong dan anh test: ").strip()
    if not student_id or not image_path:
        print("[TEST-AI] Thieu student_id hoac image_path.", flush=True)
        return

    test_register_and_recognize(student_id=student_id, image_path=image_path)


if __name__ == "__main__":
    main()
