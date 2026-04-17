from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Student(db.Model):
    """Model sinh viên dùng cho xác thực ra vào."""

    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    face_image_path = db.Column(db.String(255), nullable=True)
    # Lưu embedding khuôn mặt dưới dạng bytes (pickle của vector numpy).
    face_encoding = db.Column(db.LargeBinary, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self) -> dict[str, str]:
        return {
            "student_id": self.student_id,
            "name": self.name,
        }
