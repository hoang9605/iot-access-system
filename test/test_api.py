from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.app import app
from database.models import Student, db


class TestAccessApi(unittest.TestCase):
    """Bộ test API xác thực ra vào theo kiến trúc Backend trung tâm."""

    @classmethod
    def setUpClass(cls) -> None:
        # Dùng DB in-memory để test độc lập, không ảnh hưởng dữ liệu thật.
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

        with app.app_context():
            db.drop_all()
            db.create_all()
            db.session.add_all(
                [
                    Student(student_id="SV001", name="Nguyen Van A", is_active=True),
                    Student(student_id="SV999", name="Disabled User", is_active=False),
                ]
            )
            db.session.commit()

    @classmethod
    def tearDownClass(cls) -> None:
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def setUp(self) -> None:
        self.client = app.test_client()

    def test_health_success(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_home_redirects_to_scan(self) -> None:
        response = self.client.get("/", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request.path, "/scan")

    def test_face_register_page_success(self) -> None:
        response = self.client.get("/register/face")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Đăng ký khuôn mặt".encode("utf-8"), response.data)

    def test_face_scan_page_success(self) -> None:
        response = self.client.get("/scan")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Quét khuôn mặt".encode("utf-8"), response.data)

    def test_legacy_ui_redirects(self) -> None:
        r1 = self.client.get("/face-register-ui", follow_redirects=True)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.request.path, "/register/face")
        r2 = self.client.get("/face-test-ui", follow_redirects=True)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.request.path, "/scan")

    def test_qr_auth_success(self) -> None:
        response = self.client.post("/qr-auth", json={"qr_code": "SV001"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "success", "student_id": "SV001"})

    def test_create_student_success(self) -> None:
        response = self.client.post(
            "/students",
            json={"student_id": "sv003", "name": "Le Van C"},
        )
        body = response.get_json()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["student_id"], "SV003")
        self.assertEqual(body["name"], "Le Van C")

    def test_create_student_missing_fields(self) -> None:
        response = self.client.post("/students", json={"student_id": "SV004"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["status"], "fail")

    def test_create_student_duplicate(self) -> None:
        response = self.client.post(
            "/students",
            json={"student_id": "sv001", "name": "Other Name"},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["status"], "fail")

    def test_qr_auth_missing_qr_code(self) -> None:
        response = self.client.post("/qr-auth", json={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["status"], "fail")

    def test_qr_auth_invalid_qr(self) -> None:
        response = self.client.post("/qr-auth", json={"qr_code": "SV_NOT_FOUND"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["status"], "fail")

    @patch("backend.app.recognize_face_from_base64", return_value="SV001")
    def test_face_auth_success(self, _mock_recognize) -> None:
        response = self.client.post("/face-auth", json={"image": "fake_base64"})
        body = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["student_id"], "SV001")
        self.assertEqual(body["name"], "Nguyen Van A")

    @patch("backend.app.recognize_face_from_base64", return_value=None)
    def test_face_auth_no_match(self, _mock_recognize) -> None:
        response = self.client.post("/face-auth", json={"image": "fake_base64"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["status"], "fail")

    def test_face_auth_missing_image(self) -> None:
        response = self.client.post("/face-auth", json={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["status"], "fail")

    @patch("backend.app.recognize_face_from_base64", return_value="SV_NOT_FOUND")
    def test_face_auth_student_not_found(self, _mock_recognize) -> None:
        response = self.client.post("/face-auth", json={"image": "fake_base64"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["status"], "fail")

    @patch("backend.app.encode_base64_and_save_to_db", return_value=True)
    def test_face_register_success(self, _mock_register) -> None:
        response = self.client.post(
            "/face-register",
            json={"student_id": "SV001", "image": "fake_base64"},
        )
        body = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["student_id"], "SV001")

    def test_face_register_missing_fields(self) -> None:
        response = self.client.post("/face-register", json={"student_id": "SV001"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["status"], "fail")

    @patch("backend.app.encode_base64_and_save_to_db", return_value=False)
    def test_face_register_fail(self, _mock_register) -> None:
        response = self.client.post(
            "/face-register",
            json={"student_id": "SV001", "image": "fake_base64"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["status"], "fail")


if __name__ == "__main__":
    unittest.main(verbosity=2)
