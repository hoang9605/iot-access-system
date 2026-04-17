from __future__ import annotations

import sys
from pathlib import Path

from flask import Flask

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ai.face_recognition import load_known_faces
from config.setting import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
from database.models import db


def create_app() -> Flask:
    """Tạo app tối giản chỉ để chạy context DB cho script encode."""
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    db.init_app(app)
    return app


def main() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        count = load_known_faces()
        print(f"[AI] Tong so khuon mat da luu vao DB: {count}", flush=True)


if __name__ == "__main__":
    main()
