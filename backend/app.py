from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_cors import CORS

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ai.face_recognition import encode_base64_and_save_to_db, recognize_face_from_base64
from config.setting import (
    DEBUG,
    HOST,
    PORT,
    SQLALCHEMY_TRACK_MODIFICATIONS,
    SQLALCHEMY_DATABASE_URI,
)
from database.models import Student, db

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS

CORS(app)
db.init_app(app)

try:
    from iot.camera import capture_image, image_to_base64
except Exception:
    capture_image = None
    image_to_base64 = None


@app.context_processor
def inject_template_globals() -> dict:
    """Biến dùng chung trong template (năm hiện tại cho footer)."""
    return {"now_year": datetime.now().year}


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200


@app.route("/", methods=["GET"])
def home():
    """Trang chủ: chuyển đến demo quét khuôn mặt."""
    return redirect(url_for("page_scan"))


@app.route("/scan", methods=["GET"])
def page_scan():
    """Trang chính: demo nhận diện khuôn mặt."""
    return render_template("pages/face_scan.html", active_nav="scan")


@app.route("/register/student", methods=["GET"])
def page_student_register():
    """Trang đăng ký sinh viên."""
    return render_template("pages/student_register.html", active_nav="student")


@app.route("/register/face", methods=["GET"])
def page_face_register():
    """Trang đăng ký khuôn mặt (camera + upload)."""
    return render_template("pages/face_register.html", active_nav="face")


@app.route("/face-register-ui", methods=["GET"])
def face_register_ui():
    """Tương thích URL cũ: chuyển sang trang đăng ký khuôn mặt mới."""
    return redirect(url_for("page_face_register"))


@app.route("/face-test-ui", methods=["GET"])
def face_test_ui():
    """Tương thích URL cũ: chuyển sang trang quét khuôn mặt."""
    return redirect(url_for("page_scan"))


@app.route("/students", methods=["POST"])
def create_student():
    """
    API tạo sinh viên mới.
    Request: { "student_id": "...", "name": "..." }
    """
    try:
        payload = request.get_json(silent=True) or {}
        student_id = str(payload.get("student_id", "")).strip().upper()
        name = str(payload.get("name", "")).strip()
        if not student_id or not name:
            return jsonify({"status": "fail", "message": "Thieu student_id hoac name."}), 400

        existed = Student.query.filter_by(student_id=student_id).first()
        if existed:
            return jsonify({"status": "fail", "message": "student_id da ton tai."}), 409

        student = Student(student_id=student_id, name=name, is_active=True)
        db.session.add(student)
        db.session.commit()
        return jsonify({"status": "success", "student_id": student_id, "name": name}), 201
    except Exception as exc:
        db.session.rollback()
        print(f"[BACKEND] Loi /students: {exc}", flush=True)
        return jsonify({"status": "fail", "message": "Loi he thong /students."}), 500


@app.route("/face-auth", methods=["POST"])
def face_auth():
    """
    API xác thực khuôn mặt.
    Request:
    - Thuong: { "image": "base64_string" }
    - Tu dong chup: { "auto_capture": true, "camera_index": 0, "preview_seconds": 2.5 }
    """
    try:
        payload = request.get_json(silent=True) or {}
        image_base64 = payload.get("image")
        auto_capture = bool(payload.get("auto_capture", False))

        # Ho tro luong backend tu chup anh tu camera khi khong gui image thu cong.
        if (not image_base64) and auto_capture:
            if not capture_image or not image_to_base64:
                return (
                    jsonify({"status": "fail", "message": "Khong tai duoc module camera IoT."}),
                    500,
                )

            camera_index = int(payload.get("camera_index", 0))
            preview_seconds = float(payload.get("preview_seconds", 2.5))
            frame = capture_image(preview_seconds=preview_seconds, camera_index=camera_index)
            if frame is None:
                return jsonify({"status": "fail", "message": "Khong chup duoc anh tu camera."}), 400

            image_base64 = image_to_base64(frame)
            if not image_base64:
                return jsonify({"status": "fail", "message": "Khong ma hoa duoc anh chup."}), 400

        if not image_base64:
            return jsonify({"status": "fail", "message": "Thieu truong image base64."}), 400

        student_id = recognize_face_from_base64(image_base64)
        if not student_id:
            return jsonify({"status": "fail", "message": "Khong nhan dien duoc."}), 401

        student = Student.query.filter_by(student_id=student_id, is_active=True).first()
        if not student:
            return (
                jsonify({"status": "fail", "message": "Khong tim thay sinh vien hop le."}),
                404,
            )

        return jsonify(
            {
                "status": "success",
                "student_id": student.student_id,
                "name": student.name,
            }
        ), 200
    except Exception as exc:
        print(f"[BACKEND] Loi /face-auth: {exc}", flush=True)
        return jsonify({"status": "fail", "message": "Loi he thong /face-auth."}), 500


@app.route("/face-register", methods=["POST"])
def face_register():
    """
    API đăng ký khuôn mặt qua backend.
    Request: { "student_id": "...", "image": "base64_string" }
    """
    try:
        payload = request.get_json(silent=True) or {}
        student_id = str(payload.get("student_id", "")).strip().upper()
        image_base64 = payload.get("image")
        if not student_id or not image_base64:
            return (
                jsonify({"status": "fail", "message": "Thieu student_id hoac image base64."}),
                400,
            )

        ok = encode_base64_and_save_to_db(student_id=student_id, base64_image=image_base64)
        if not ok:
            return (
                jsonify({"status": "fail", "message": "Dang ky khuon mat that bai."}),
                400,
            )

        return jsonify({"status": "success", "student_id": student_id}), 200
    except Exception as exc:
        print(f"[BACKEND] Loi /face-register: {exc}", flush=True)
        return jsonify({"status": "fail", "message": "Loi he thong /face-register."}), 500


@app.route("/qr-auth", methods=["POST"])
def qr_auth():
    """
    API xác thực QR.
    Request: { "qr_code": "student_id" }
    """
    try:
        payload = request.get_json(silent=True) or {}
        qr_code = payload.get("qr_code")
        if not qr_code:
            return jsonify({"status": "fail", "message": "Thieu truong qr_code."}), 400

        student = Student.query.filter_by(student_id=qr_code, is_active=True).first()
        if not student:
            return jsonify({"status": "fail", "message": "QR khong hop le."}), 401

        return jsonify({"status": "success", "student_id": student.student_id}), 200
    except Exception as exc:
        print(f"[BACKEND] Loi /qr-auth: {exc}", flush=True)
        return jsonify({"status": "fail", "message": "Loi he thong /qr-auth."}), 500


def main() -> None:
    with app.app_context():
        db.create_all()
    app.run(host=HOST, port=PORT, debug=DEBUG)


if __name__ == "__main__":
    main()
