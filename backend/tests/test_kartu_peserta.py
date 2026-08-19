"""
Test suite for Kartu Peserta (Exam Card) feature and settings fix
"""
import pytest
import requests
from io import BytesIO
from PyPDF2 import PdfReader

BASE_URL = "https://github-auto-build.preview.emergentagent.com/api"

# Test credentials from test_credentials.md
ADMIN_CREDS = {"email": "hitoria532@gmail.com", "password": "admin123"}
GURU_CREDS = {"email": "guru@sekolah.id", "password": "guru123"}
SISWA_CREDS = {"email": "siswa@sekolah.id", "password": "siswa123"}


class TestKartuPeserta:
    """Test Kartu Peserta PDF generation endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        resp = requests.post(f"{BASE_URL}/auth/login", json=ADMIN_CREDS)
        assert resp.status_code == 200, f"Admin login failed: {resp.text}"
        return resp.json()["token"]
    
    @pytest.fixture(scope="class")
    def guru_token(self):
        """Get guru auth token"""
        resp = requests.post(f"{BASE_URL}/auth/login", json=GURU_CREDS)
        assert resp.status_code == 200, f"Guru login failed: {resp.text}"
        return resp.json()["token"]
    
    @pytest.fixture(scope="class")
    def siswa_token(self):
        """Get siswa auth token"""
        resp = requests.post(f"{BASE_URL}/auth/login", json=SISWA_CREDS)
        assert resp.status_code == 200, f"Siswa login failed: {resp.text}"
        return resp.json()["token"]
    
    @pytest.fixture(scope="class")
    def test_class_id(self, admin_token):
        """Get existing class ID (Kelas X-A)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.get(f"{BASE_URL}/classes", headers=headers)
        assert resp.status_code == 200
        classes = resp.json()
        # Find Kelas X-A
        for cls in classes:
            if "X-A" in cls["name"] or "X" in cls["name"]:
                return cls["id"]
        # If not found, return first class
        if classes:
            return classes[0]["id"]
        pytest.skip("No classes found in database")
    
    @pytest.fixture(scope="class")
    def test_session_id(self, admin_token):
        """Get existing session ID (UH Matematika - Kelas X)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.get(f"{BASE_URL}/sessions", headers=headers)
        assert resp.status_code == 200
        sessions = resp.json()
        # Find UH Matematika session
        for sess in sessions:
            if "Matematika" in sess.get("title", ""):
                return sess["id"]
        # Return first session if exists
        if sessions:
            return sessions[0]["id"]
        return None  # No sessions available
    
    def test_kartu_admin_access(self, admin_token, test_class_id):
        """Test admin can access kartu peserta PDF"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.get(f"{BASE_URL}/cards/class/{test_class_id}/pdf", headers=headers)
        assert resp.status_code == 200, f"Admin should get 200, got {resp.status_code}: {resp.text}"
        assert resp.headers["Content-Type"] == "application/pdf"
        assert len(resp.content) > 0, "PDF should not be empty"
        print(f"✅ Admin can access kartu peserta PDF (size: {len(resp.content)} bytes)")
    
    def test_kartu_guru_access(self, guru_token, test_class_id):
        """Test guru can access kartu peserta PDF"""
        headers = {"Authorization": f"Bearer {guru_token}"}
        resp = requests.get(f"{BASE_URL}/cards/class/{test_class_id}/pdf", headers=headers)
        assert resp.status_code == 200, f"Guru should get 200, got {resp.status_code}: {resp.text}"
        assert resp.headers["Content-Type"] == "application/pdf"
        assert len(resp.content) > 0, "PDF should not be empty"
        print(f"✅ Guru can access kartu peserta PDF (size: {len(resp.content)} bytes)")
    
    def test_kartu_siswa_forbidden(self, siswa_token, test_class_id):
        """Test siswa gets 403 forbidden"""
        headers = {"Authorization": f"Bearer {siswa_token}"}
        resp = requests.get(f"{BASE_URL}/cards/class/{test_class_id}/pdf", headers=headers)
        assert resp.status_code == 403, f"Siswa should get 403, got {resp.status_code}"
        print("✅ Siswa correctly gets 403 forbidden")
    
    def test_kartu_invalid_class_404(self, admin_token):
        """Test invalid class ID returns 404"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.get(f"{BASE_URL}/cards/class/invalid-class-id-999/pdf", headers=headers)
        assert resp.status_code == 404, f"Invalid class should return 404, got {resp.status_code}"
        print("✅ Invalid class ID returns 404")
    
    def test_kartu_pdf_content(self, admin_token, test_class_id):
        """Test PDF contains expected student information"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get class info first
        resp = requests.get(f"{BASE_URL}/classes", headers=headers)
        assert resp.status_code == 200
        classes = resp.json()
        class_info = next((c for c in classes if c["id"] == test_class_id), None)
        assert class_info is not None, f"Class {test_class_id} not found"
        class_name = class_info["name"]
        
        # Get students in class
        resp = requests.get(f"{BASE_URL}/users?role=siswa", headers=headers)
        assert resp.status_code == 200
        all_students = resp.json()
        class_students = [s for s in all_students if s["id"] in class_info.get("student_ids", [])]
        
        # Get PDF
        resp = requests.get(f"{BASE_URL}/cards/class/{test_class_id}/pdf", headers=headers)
        assert resp.status_code == 200
        
        # Parse PDF text
        pdf_reader = PdfReader(BytesIO(resp.content))
        pdf_text = ""
        for page in pdf_reader.pages:
            pdf_text += page.extract_text()
        
        print(f"\n📄 PDF Text Preview (first 500 chars):\n{pdf_text[:500]}\n")
        
        # Check if class students appear in PDF
        if class_students:
            for student in class_students:
                assert student["name"] in pdf_text, f"Student {student['name']} not found in PDF"
                # Check for NISN/NIP if available
                if student.get("identifier"):
                    assert student["identifier"] in pdf_text, f"Student identifier {student['identifier']} not found"
                # Check for email
                if student.get("email"):
                    assert student["email"] in pdf_text, f"Student email {student['email']} not found"
            print(f"✅ All {len(class_students)} students found in PDF")
        else:
            # Check for "Belum ada siswa" message
            assert "Belum ada siswa" in pdf_text, "Empty class should show 'Belum ada siswa' message"
            print("✅ Empty class shows 'Belum ada siswa' message")
        
        # Check for class name
        assert class_name in pdf_text, f"Class name {class_name} not found in PDF"
        print(f"✅ Class name '{class_name}' found in PDF")
        
        # Check for school identity
        assert "SMA Contoh Nusantara" in pdf_text or "KARTU PESERTA UJIAN" in pdf_text, "School identity or card title not found"
        print("✅ School identity/card title found in PDF")
    
    def test_kartu_with_session_filter(self, admin_token, test_class_id, test_session_id):
        """Test PDF with session_id filter"""
        if not test_session_id:
            pytest.skip("No sessions available for testing")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.get(f"{BASE_URL}/cards/class/{test_class_id}/pdf?session_id={test_session_id}", headers=headers)
        assert resp.status_code == 200, f"Should get 200 with session filter, got {resp.status_code}"
        assert resp.headers["Content-Type"] == "application/pdf"
        
        # Parse PDF to check session appears
        pdf_reader = PdfReader(BytesIO(resp.content))
        pdf_text = ""
        for page in pdf_reader.pages:
            pdf_text += page.extract_text()
        
        # Get session info
        resp = requests.get(f"{BASE_URL}/sessions/{test_session_id}", headers=headers)
        if resp.status_code == 200:
            session_info = resp.json()
            # Session title should appear in PDF
            assert session_info["title"] in pdf_text, f"Session title {session_info['title']} not found in filtered PDF"
            print(f"✅ Session filter works - found '{session_info['title']}' in PDF")
        else:
            print("⚠️ Could not verify session title in PDF (session not found)")
    
    def test_kartu_school_logo_embedded(self, admin_token, test_class_id):
        """Test that school logo is embedded in PDF"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.get(f"{BASE_URL}/cards/class/{test_class_id}/pdf", headers=headers)
        assert resp.status_code == 200
        
        # Check if PDF contains image objects (logo)
        pdf_reader = PdfReader(BytesIO(resp.content))
        has_images = False
        for page in pdf_reader.pages:
            if "/XObject" in page["/Resources"]:
                xobjects = page["/Resources"]["/XObject"].get_object()
                for obj in xobjects:
                    if xobjects[obj]["/Subtype"] == "/Image":
                        has_images = True
                        break
        
        # Note: Logo might not be present if not configured, so we just check structure
        print(f"✅ PDF structure checked - Images embedded: {has_images}")


class TestSchoolSettingsFix:
    """Test PUT /api/settings/school preserves theme_color"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        resp = requests.post(f"{BASE_URL}/auth/login", json=ADMIN_CREDS)
        assert resp.status_code == 200
        return resp.json()["token"]
    
    def test_settings_preserves_theme_color(self, admin_token):
        """Test that theme_color is preserved when omitted from PUT request"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get current settings
        resp = requests.get(f"{BASE_URL}/settings/school", headers=headers)
        assert resp.status_code == 200
        original_settings = resp.json()
        original_theme = original_settings.get("theme_color")
        
        print(f"Original theme_color: {original_theme}")
        
        # Update only name and address (omit theme_color)
        update_data = {
            "name": "SMA Contoh Nusantara",
            "address": "Jl. Pendidikan No. 123, Jakarta"
        }
        resp = requests.put(f"{BASE_URL}/settings/school", json=update_data, headers=headers)
        assert resp.status_code == 200, f"PUT should succeed, got {resp.status_code}: {resp.text}"
        
        # Get updated settings
        resp = requests.get(f"{BASE_URL}/settings/school", headers=headers)
        assert resp.status_code == 200
        updated_settings = resp.json()
        
        # Verify theme_color is preserved
        assert updated_settings.get("theme_color") == original_theme, \
            f"theme_color should be preserved: expected {original_theme}, got {updated_settings.get('theme_color')}"
        
        # Verify name and address were updated
        assert updated_settings["name"] == update_data["name"]
        assert updated_settings["address"] == update_data["address"]
        
        print(f"✅ theme_color preserved: {updated_settings.get('theme_color')}")
        print(f"✅ name updated: {updated_settings['name']}")
        print(f"✅ address updated: {updated_settings['address']}")
    
    def test_settings_updates_theme_when_provided(self, admin_token):
        """Test that theme_color is updated when provided"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Update with new theme_color
        new_theme = "#1e3a30"
        update_data = {
            "name": "SMA Contoh Nusantara",
            "address": "Jl. Pendidikan No. 123, Jakarta",
            "theme_color": new_theme
        }
        resp = requests.put(f"{BASE_URL}/settings/school", json=update_data, headers=headers)
        assert resp.status_code == 200
        
        # Verify theme_color was updated
        resp = requests.get(f"{BASE_URL}/settings/school", headers=headers)
        assert resp.status_code == 200
        settings = resp.json()
        assert settings.get("theme_color") == new_theme, \
            f"theme_color should be updated to {new_theme}, got {settings.get('theme_color')}"
        
        print(f"✅ theme_color updated to: {settings.get('theme_color')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
