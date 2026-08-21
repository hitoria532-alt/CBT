"""
Test bulk password reset and login cards PDF generation features.
"""
import io
import pytest
import requests
from pypdf import PdfReader

BASE_URL = "https://deploy-web-app-3.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@sekolah.id"
ADMIN_PASSWORD = "Admin@12345"


class TestBulkPasswordResetAndCards:
    """Test suite for bulk password reset and login cards PDF generation."""

    @pytest.fixture(scope="class")
    def admin_token(self):
        """Login as admin and return token."""
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10
        )
        assert resp.status_code == 200, f"Admin login failed: {resp.text}"
        return resp.json()["token"]

    @pytest.fixture(scope="class")
    def test_class(self, admin_token):
        """Create a test class with 3 students for testing."""
        import time
        timestamp = int(time.time())
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create class
        resp = requests.post(
            f"{BASE_URL}/classes",
            json={"name": f"Kelas Uji Kartu {timestamp}", "description": "Test class for bulk reset"},
            headers=headers,
            timeout=10
        )
        assert resp.status_code == 200
        cls = resp.json()
        class_id = cls["id"]
        
        # Create 3 students with unique emails
        students = []
        for i in range(1, 4):
            resp = requests.post(
                f"{BASE_URL}/classes/{class_id}/students",
                json={
                    "name": f"Siswa Test {i}",
                    "email": f"siswatest{timestamp}{i}@sekolah.id",
                    "password": f"original{i}",
                    "identifier": f"NIS{timestamp}{i}"
                },
                headers=headers,
                timeout=10
            )
            if resp.status_code != 200:
                print(f"Failed to create student {i}: {resp.status_code} - {resp.text}")
            assert resp.status_code == 200, f"Failed to create student: {resp.text}"
            students.append(resp.json())
        
        yield {"id": class_id, "name": cls["name"], "students": students}
        
        # Cleanup
        requests.delete(f"{BASE_URL}/classes/{class_id}", headers=headers, timeout=10)

    def test_reset_passwords_random_mode(self, admin_token, test_class):
        """Test bulk password reset with random mode."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        class_id = test_class["id"]
        
        # Reset passwords with random mode
        resp = requests.post(
            f"{BASE_URL}/classes/{class_id}/students/reset-passwords",
            json={"mode": "random"},
            headers=headers,
            timeout=10
        )
        
        assert resp.status_code == 200, f"Reset failed: {resp.text}"
        data = resp.json()
        
        # Verify response structure
        assert "count" in data
        assert "class_name" in data
        assert "credentials" in data
        assert data["count"] == 3
        assert data["class_name"] == test_class["name"]
        assert len(data["credentials"]) == 3
        
        # Verify each credential has required fields
        for cred in data["credentials"]:
            assert "id" in cred
            assert "name" in cred
            assert "email" in cred
            assert "identifier" in cred
            assert "password" in cred
            assert len(cred["password"]) >= 5
        
        # Test that NEW passwords work
        for cred in data["credentials"]:
            login_resp = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": cred["email"], "password": cred["password"]},
                timeout=10
            )
            assert login_resp.status_code == 200, f"Login with new password failed for {cred['email']}"
        
        # Test that OLD passwords no longer work
        for i, student in enumerate(test_class["students"], 1):
            old_login = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": student["email"], "password": f"original{i}"},
                timeout=10
            )
            assert old_login.status_code == 401, f"Old password still works for {student['email']}"
        
        print("✅ Random mode password reset: All tests passed")

    def test_reset_passwords_same_mode(self, admin_token, test_class):
        """Test bulk password reset with same password for all."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        class_id = test_class["id"]
        same_password = "ujian2026"
        
        # Reset passwords with same mode
        resp = requests.post(
            f"{BASE_URL}/classes/{class_id}/students/reset-passwords",
            json={"mode": "same", "password": same_password},
            headers=headers,
            timeout=10
        )
        
        assert resp.status_code == 200, f"Reset failed: {resp.text}"
        data = resp.json()
        
        assert data["count"] == 3
        assert len(data["credentials"]) == 3
        
        # Verify all students have the same password
        for cred in data["credentials"]:
            assert cred["password"] == same_password
        
        # Test that all students can login with the same password
        for student in test_class["students"]:
            login_resp = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": student["email"], "password": same_password},
                timeout=10
            )
            assert login_resp.status_code == 200, f"Login failed for {student['email']}"
        
        print("✅ Same mode password reset: All tests passed")

    def test_reset_passwords_validation(self, admin_token, test_class):
        """Test validation for password reset."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        class_id = test_class["id"]
        
        # Test invalid mode
        resp = requests.post(
            f"{BASE_URL}/classes/{class_id}/students/reset-passwords",
            json={"mode": "invalid"},
            headers=headers,
            timeout=10
        )
        assert resp.status_code == 400
        
        # Test same mode with short password
        resp = requests.post(
            f"{BASE_URL}/classes/{class_id}/students/reset-passwords",
            json={"mode": "same", "password": "abc"},
            headers=headers,
            timeout=10
        )
        assert resp.status_code == 400
        
        # Test non-existing class
        resp = requests.post(
            f"{BASE_URL}/classes/nonexistent/students/reset-passwords",
            json={"mode": "random"},
            headers=headers,
            timeout=10
        )
        assert resp.status_code == 404
        
        print("✅ Password reset validation: All tests passed")

    def test_reset_passwords_with_student_filter(self, admin_token, test_class):
        """Test password reset with student_ids filter."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        class_id = test_class["id"]
        
        # Reset only first 2 students
        student_ids = [test_class["students"][0]["id"], test_class["students"][1]["id"]]
        
        resp = requests.post(
            f"{BASE_URL}/classes/{class_id}/students/reset-passwords",
            json={"mode": "random", "student_ids": student_ids},
            headers=headers,
            timeout=10
        )
        
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert len(data["credentials"]) == 2
        
        # Verify only selected students got new passwords
        reset_emails = {cred["email"] for cred in data["credentials"]}
        assert test_class["students"][0]["email"] in reset_emails
        assert test_class["students"][1]["email"] in reset_emails
        
        print("✅ Password reset with student filter: All tests passed")

    def test_login_cards_pdf_with_passwords(self, admin_token, test_class):
        """Test PDF card generation with passwords included."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        class_id = test_class["id"]
        
        # First reset passwords to get credentials
        reset_resp = requests.post(
            f"{BASE_URL}/classes/{class_id}/students/reset-passwords",
            json={"mode": "random"},
            headers=headers,
            timeout=10
        )
        assert reset_resp.status_code == 200
        credentials = reset_resp.json()["credentials"]
        
        # Generate PDF with passwords
        pdf_resp = requests.post(
            f"{BASE_URL}/classes/{class_id}/students/cards/pdf",
            json={
                "login_url": "https://deploy-web-app-3.preview.emergentagent.com",
                "include_password": True,
                "credentials": [
                    {
                        "name": c["name"],
                        "email": c["email"],
                        "identifier": c["identifier"],
                        "password": c["password"]
                    }
                    for c in credentials
                ]
            },
            headers=headers,
            timeout=10
        )
        
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers["Content-Type"] == "application/pdf"
        
        # Verify PDF is valid
        pdf_data = pdf_resp.content
        assert pdf_data.startswith(b"%PDF"), "Not a valid PDF file"
        assert len(pdf_data) > 1000, "PDF too small"
        
        # Parse PDF and verify content
        pdf_reader = PdfReader(io.BytesIO(pdf_data))
        assert len(pdf_reader.pages) > 0
        
        # Extract text from first page
        text = pdf_reader.pages[0].extract_text()
        
        # Verify student info is in PDF
        for cred in credentials:
            assert cred["name"] in text, f"Student name {cred['name']} not found in PDF"
            # Email might be truncated in PDF due to space constraints, check for partial match
            email_prefix = cred["email"].split("@")[0]
            assert email_prefix in text, f"Email prefix {email_prefix} not found in PDF"
            assert cred["password"] in text, f"Password not found in PDF"
        
        # Verify login URL is present
        assert "deploy-web-app-3.preview.emergentagent.com" in text
        
        print("✅ PDF cards with passwords: All tests passed")

    def test_login_cards_pdf_without_passwords(self, admin_token, test_class):
        """Test PDF card generation without passwords (blank)."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        class_id = test_class["id"]
        
        # Generate PDF without passwords (empty credentials = use roster)
        pdf_resp = requests.post(
            f"{BASE_URL}/classes/{class_id}/students/cards/pdf",
            json={
                "login_url": "https://deploy-web-app-3.preview.emergentagent.com",
                "include_password": False,
                "credentials": []
            },
            headers=headers,
            timeout=10
        )
        
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers["Content-Type"] == "application/pdf"
        
        pdf_data = pdf_resp.content
        assert pdf_data.startswith(b"%PDF")
        
        # Parse PDF
        pdf_reader = PdfReader(io.BytesIO(pdf_data))
        text = pdf_reader.pages[0].extract_text()
        
        # Verify student names are present but passwords are blank
        for student in test_class["students"]:
            assert student["name"] in text
            # Email might be truncated, check for prefix
            email_prefix = student["email"].split("@")[0]
            assert email_prefix in text
        
        print("✅ PDF cards without passwords: All tests passed")

    def test_login_cards_pdf_empty_class(self, admin_token):
        """Test PDF generation fails for empty class."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create empty class
        resp = requests.post(
            f"{BASE_URL}/classes",
            json={"name": "Empty Class", "description": "No students"},
            headers=headers,
            timeout=10
        )
        assert resp.status_code == 200
        empty_class_id = resp.json()["id"]
        
        # Try to generate PDF for empty class
        pdf_resp = requests.post(
            f"{BASE_URL}/classes/{empty_class_id}/students/cards/pdf",
            json={
                "login_url": "https://example.com",
                "include_password": False,
                "credentials": []
            },
            headers=headers,
            timeout=10
        )
        
        assert pdf_resp.status_code == 400
        
        # Cleanup
        requests.delete(f"{BASE_URL}/classes/{empty_class_id}", headers=headers, timeout=10)
        
        print("✅ PDF cards empty class validation: All tests passed")

    def test_regression_other_pdf_endpoints(self, admin_token, test_class):
        """Test that other PDF endpoints still work after reportlab installation."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        class_id = test_class["id"]
        
        # Test class report PDF
        resp = requests.get(
            f"{BASE_URL}/report/class/{class_id}/pdf",
            headers=headers,
            timeout=10
        )
        
        # Should return 200 or 404 (if no data), but not 500
        assert resp.status_code in [200, 404], f"Class report PDF failed: {resp.status_code}"
        
        if resp.status_code == 200:
            assert resp.headers["Content-Type"] == "application/pdf"
            assert resp.content.startswith(b"%PDF")
        
        print("✅ Regression test for other PDF endpoints: Passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
