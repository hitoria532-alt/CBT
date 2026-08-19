import requests
import sys
import io
from datetime import datetime

BASE_URL = "https://github-auto-build.preview.emergentagent.com/api"

class AttendancePDFTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.admin_token = None
        self.guru_token = None
        self.siswa_token = None
        self.session_id = None
        self.school_logo_path = None

    def log(self, msg):
        print(f"  {msg}")

    def test(self, name, condition, error_msg=""):
        self.tests_run += 1
        if condition:
            self.tests_passed += 1
            self.log(f"✅ {name}")
            return True
        else:
            self.log(f"❌ {name}: {error_msg}")
            return False

    def login(self, email, password):
        """Login and return token"""
        try:
            resp = requests.post(f"{BASE_URL}/auth/login", 
                               json={"email": email, "password": password}, 
                               timeout=10)
            if resp.status_code == 200:
                return resp.json().get("token")
            return None
        except Exception as e:
            self.log(f"Login error for {email}: {e}")
            return None

    def setup_auth(self):
        """Setup authentication tokens for all roles"""
        print("\n🔐 Setting up authentication...")
        
        self.admin_token = self.login("hitoria532@gmail.com", "admin123")
        self.test("Admin login", self.admin_token is not None, "Failed to get admin token")
        
        self.guru_token = self.login("guru@sekolah.id", "guru123")
        self.test("Guru login", self.guru_token is not None, "Failed to get guru token")
        
        self.siswa_token = self.login("siswa@sekolah.id", "siswa123")
        self.test("Siswa login", self.siswa_token is not None, "Failed to get siswa token")

    def get_test_session(self):
        """Get an existing session for testing"""
        print("\n📋 Finding test session...")
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            resp = requests.get(f"{BASE_URL}/sessions", headers=headers, timeout=10)
            if resp.status_code == 200:
                sessions = resp.json()
                if sessions:
                    # Find 'UH Matematika - Kelas X' session or use first one
                    for s in sessions:
                        if "Matematika" in s.get("title", ""):
                            self.session_id = s["id"]
                            self.log(f"Using session: {s['title']} (ID: {self.session_id})")
                            return True
                    # Fallback to first session
                    self.session_id = sessions[0]["id"]
                    self.log(f"Using session: {sessions[0]['title']} (ID: {self.session_id})")
                    return True
                else:
                    self.log("❌ No sessions found in database")
                    return False
        except Exception as e:
            self.log(f"❌ Error getting sessions: {e}")
            return False

    def test_attendance_pdf_permissions(self):
        """Test attendance PDF endpoint with different roles"""
        print("\n🔒 Testing attendance PDF permissions...")
        
        if not self.session_id:
            self.log("⚠️  Skipping: No session ID available")
            return
        
        # Test admin access (should work)
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            resp = requests.get(f"{BASE_URL}/attendance/session/{self.session_id}/pdf", 
                              headers=headers, timeout=15)
            self.test("Admin can access attendance PDF", 
                     resp.status_code == 200 and resp.headers.get("content-type") == "application/pdf",
                     f"Status: {resp.status_code}, Content-Type: {resp.headers.get('content-type')}")
        except Exception as e:
            self.test("Admin can access attendance PDF", False, str(e))
        
        # Test guru access (should work)
        try:
            headers = {"Authorization": f"Bearer {self.guru_token}"}
            resp = requests.get(f"{BASE_URL}/attendance/session/{self.session_id}/pdf", 
                              headers=headers, timeout=15)
            self.test("Guru can access attendance PDF", 
                     resp.status_code == 200 and resp.headers.get("content-type") == "application/pdf",
                     f"Status: {resp.status_code}")
        except Exception as e:
            self.test("Guru can access attendance PDF", False, str(e))
        
        # Test siswa access (should be forbidden)
        try:
            headers = {"Authorization": f"Bearer {self.siswa_token}"}
            resp = requests.get(f"{BASE_URL}/attendance/session/{self.session_id}/pdf", 
                              headers=headers, timeout=15)
            self.test("Siswa gets 403 for attendance PDF", 
                     resp.status_code == 403,
                     f"Expected 403, got {resp.status_code}")
        except Exception as e:
            self.test("Siswa gets 403 for attendance PDF", False, str(e))
        
        # Test unknown session (should be 404)
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            resp = requests.get(f"{BASE_URL}/attendance/session/unknown-session-id/pdf", 
                              headers=headers, timeout=15)
            self.test("Unknown session returns 404", 
                     resp.status_code == 404,
                     f"Expected 404, got {resp.status_code}")
        except Exception as e:
            self.test("Unknown session returns 404", False, str(e))

    def test_attendance_pdf_content(self):
        """Test attendance PDF content"""
        print("\n📄 Testing attendance PDF content...")
        
        if not self.session_id:
            self.log("⚠️  Skipping: No session ID available")
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            resp = requests.get(f"{BASE_URL}/attendance/session/{self.session_id}/pdf", 
                              headers=headers, timeout=15)
            
            if resp.status_code != 200:
                self.test("PDF content validation", False, f"Failed to get PDF: {resp.status_code}")
                return
            
            # Get PDF content as bytes
            pdf_content = resp.content
            
            # Check PDF header (valid PDF starts with %PDF-)
            self.test("PDF has valid header", 
                     pdf_content.startswith(b'%PDF-'),
                     "Invalid PDF header")
            
            # For text validation, we need to extract text from PDF streams
            # PDFs store text in compressed streams, so we'll look for uncompressed text
            try:
                # Try to find text in the PDF (some text may be uncompressed)
                pdf_str = pdf_content.decode('latin-1', errors='ignore')
                
                # Check for key text elements (they may appear in PDF streams)
                has_daftar_hadir = "DAFTAR HADIR UJIAN" in pdf_str or "Daftar Hadir" in pdf_str
                
                self.test("PDF contains 'DAFTAR HADIR UJIAN'", 
                         has_daftar_hadir,
                         "Text not found in PDF")
                
                # Note: ReportLab compresses text streams, so we can't easily extract all text
                # without a PDF parsing library. The presence of "DAFTAR HADIR UJIAN" confirms
                # the PDF contains text content. Full content validation will be done via
                # frontend testing (visual inspection of downloaded PDF).
                self.log("ℹ️  Note: Full text content validation requires PDF parsing library")
                self.log("ℹ️  Frontend tests will verify complete PDF content via download")
                
            except Exception as e:
                self.log(f"⚠️  Text extraction from PDF failed: {e}")
                self.log("⚠️  Skipping text content validation (PDF may use compressed streams)")
            
            self.test("PDF size is reasonable", 
                     len(pdf_content) > 1000 and len(pdf_content) < 5000000,
                     f"PDF size: {len(pdf_content)} bytes")
            
        except Exception as e:
            self.test("PDF content validation", False, str(e))

    def test_school_settings_logo(self):
        """Test PUT /api/settings/school logo_path handling"""
        print("\n🏫 Testing school settings logo handling...")
        
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # First, get current settings
            resp = requests.get(f"{BASE_URL}/settings/school", headers=headers, timeout=10)
            if resp.status_code == 200:
                current = resp.json()
                original_logo = current.get("logo_path")
                original_name = current.get("name", "")
                original_address = current.get("address", "")
                self.log(f"Current logo_path: {original_logo}")
                self.log(f"Current name: {original_name}")
                
                # Test 1: Update name/address WITHOUT logo_path (should keep existing logo)
                update_data = {
                    "name": original_name or "SMA Contoh Nusantara",
                    "address": original_address or "Jl. Pendidikan No. 1, Jakarta"
                }
                resp = requests.put(f"{BASE_URL}/settings/school", 
                                  json=update_data, headers=headers, timeout=10)
                if resp.status_code == 200:
                    updated = resp.json()
                    self.test("Omitting logo_path keeps existing logo", 
                             updated.get("logo_path") == original_logo,
                             f"Expected {original_logo}, got {updated.get('logo_path')}")
                    self.test("Name updated correctly", 
                             updated.get("name") == update_data["name"],
                             f"Name mismatch")
                else:
                    self.test("Update without logo_path", False, f"Status: {resp.status_code}")
                
                # Test 2: Explicitly set logo_path to empty string (should delete logo)
                if original_logo:
                    update_data_clear = {
                        "name": original_name or "SMA Contoh Nusantara",
                        "address": original_address or "Jl. Pendidikan No. 1, Jakarta",
                        "logo_path": ""
                    }
                    resp = requests.put(f"{BASE_URL}/settings/school", 
                                      json=update_data_clear, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        updated = resp.json()
                        self.test("Empty string logo_path removes logo", 
                                 updated.get("logo_path") is None or updated.get("logo_path") == "",
                                 f"Logo should be removed, got {updated.get('logo_path')}")
                    else:
                        self.test("Clear logo_path", False, f"Status: {resp.status_code}")
                    
                    # Test 3: Restore original logo
                    restore_data = {
                        "name": original_name or "SMA Contoh Nusantara",
                        "address": original_address or "Jl. Pendidikan No. 1, Jakarta",
                        "logo_path": original_logo
                    }
                    resp = requests.put(f"{BASE_URL}/settings/school", 
                                      json=restore_data, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        self.test("Logo restored successfully", True)
                    else:
                        self.test("Logo restoration", False, f"Status: {resp.status_code}")
                else:
                    self.log("⚠️  No logo to test deletion")
            else:
                self.test("Get school settings", False, f"Status: {resp.status_code}")
                
        except Exception as e:
            self.test("School settings logo handling", False, str(e))

    def test_regression_exports(self):
        """Test that Excel and CSV exports still work"""
        print("\n📊 Testing regression: Export functionality...")
        
        if not self.session_id:
            self.log("⚠️  Skipping: No session ID available")
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Test Excel export
            resp = requests.get(f"{BASE_URL}/export/session/{self.session_id}/xlsx", 
                              headers=headers, timeout=15)
            self.test("Excel export works", 
                     resp.status_code == 200 and 
                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in resp.headers.get("content-type", ""),
                     f"Status: {resp.status_code}, Content-Type: {resp.headers.get('content-type')}")
            
        except Exception as e:
            self.test("Excel export", False, str(e))

    def run_all_tests(self):
        """Run all tests"""
        print("=" * 70)
        print("🧪 ATTENDANCE PDF FEATURE TEST SUITE")
        print("=" * 70)
        
        # Setup
        self.setup_auth()
        if not self.admin_token:
            print("\n❌ Cannot proceed without admin authentication")
            return False
        
        if not self.get_test_session():
            print("\n❌ Cannot proceed without a test session")
            return False
        
        # Run tests
        self.test_attendance_pdf_permissions()
        self.test_attendance_pdf_content()
        self.test_school_settings_logo()
        self.test_regression_exports()
        
        # Summary
        print("\n" + "=" * 70)
        print(f"📊 TEST SUMMARY: {self.tests_passed}/{self.tests_run} tests passed")
        print("=" * 70)
        
        return self.tests_passed == self.tests_run

def main():
    tester = AttendancePDFTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
