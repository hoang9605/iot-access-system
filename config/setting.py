from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Nạp biến môi trường từ file .env (nếu có).
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Cấu hình backend.
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "5000"))
DEBUG = os.getenv("DEBUG", "1") == "1"

# Đường dẫn CSDL SQLite.
DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "library.db"
SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH.as_posix()}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Cấu hình AI Face.
AI_DATASET_DIR = BASE_DIR / "ai" / "dataset"
AI_ENCODING_FILE = BASE_DIR / "ai" / "encodings.pkl"
FACE_RECOGNITION_TOLERANCE = float(os.getenv("FACE_RECOGNITION_TOLERANCE", "0.55"))

# Cấu hình request của client modules.
API_BASE_URL = f"http://{HOST}:{PORT}"
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))
