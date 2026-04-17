from __future__ import annotations

from flask import Flask

from config.setting import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
from database.models import Student, db


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    db.init_app(app)
    return app


def init_database() -> None:
    """Khởi tạo DB và thêm dữ liệu mẫu tối thiểu."""
    app = create_app()
    with app.app_context():
        db.create_all()
        if not Student.query.first():
            db.session.add_all(
                [
                    Student(student_id="SV001", name="Nguyen Van A", is_active=True),
                    Student(student_id="SV002", name="Tran Thi B", is_active=True),
                ]
            )
            db.session.commit()
            print("[DB] Da tao du lieu mau.", flush=True)
        else:
            print("[DB] Du lieu da ton tai, bo qua seed.", flush=True)


if __name__ == "__main__":
    init_database()
