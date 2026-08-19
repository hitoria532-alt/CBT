#!/usr/bin/env python3
"""Backend API tests for Indonesian Excel import features."""
import sys
import requests
from io import BytesIO
import pandas as pd

BASE_URL = "https://github-auto-build.preview.emergentagent.com/api"

class ImportTestRunner:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.admin_token = None
        self.guru_token = None
        self.temp_categories = []
        self.temp_questions = []
        self.temp_users = []
        self.temp_classes = []

    def log(self, msg, level="INFO"):
        prefix = {"INFO": "ℹ️", "PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}.get(level, "•")
        print(f"{prefix} {msg}")

    def test(self, name, fn):
        """Run a test function."""
        self.tests_run += 1
        self.log(f"Testing: {name}")
        try:
            fn()
            self.tests_passed += 1
            self.log(f"PASSED: {name}", "PASS")
            return True
        except AssertionError as e:
            self.log(f"FAILED: {name} - {e}", "FAIL")
            return False
        except Exception as e:
            self.log(f"ERROR: {name} - {e}", "FAIL")
            return False

    def login(self, email, password):
        """Login and return token."""
        r = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
        return r.json()["token"]

    def cleanup(self):
        """Clean up temporary test data."""
        if not self.admin_token:
            return
        
        # Delete temp questions
        for qid in self.temp_questions:
            try:
                requests.delete(f"{BASE_URL}/questions/{qid}", 
                              headers={"Authorization": f"Bearer {self.admin_token}"})
            except Exception:
                pass
        
        # Delete temp categories
        for cid in self.temp_categories:
            try:
                requests.delete(f"{BASE_URL}/categories/{cid}", 
                              headers={"Authorization": f"Bearer {self.admin_token}"})
            except Exception:
                pass
        
        # Delete temp users
        for uid in self.temp_users:
            try:
                requests.delete(f"{BASE_URL}/users/{uid}", 
                              headers={"Authorization": f"Bearer {self.admin_token}"})
            except Exception:
                pass
        
        # Delete temp classes
        for cid in self.temp_classes:
            try:
                requests.delete(f"{BASE_URL}/classes/{cid}", 
                              headers={"Authorization": f"Bearer {self.admin_token}"})
            except Exception:
                pass

    def _test_login_admin(self):
        self.admin_token = self.login("hitoria532@gmail.com", "admin123")
        assert self.admin_token, "Admin token is empty"

    def _test_login_guru(self):
        self.guru_token = self.login("guru@sekolah.id", "guru123")
        assert self.guru_token, "Guru token is empty"

    def _test_question_import_indonesian_headers(self):
        """Test question import with Indonesian headers (NO, BUTIR SOAL, A-E, KUNCI, BOBOT, MAPEL)"""
        # Create Excel file with Indonesian headers
        data = {
            'NO': [1, 2, 3, 4, 5],
            'BUTIR SOAL': [
                'Berapa hasil 2 + 2?',
                'Matahari terbit dari timur',
                'Jelaskan proses fotosintesis',
                'Ibu kota Indonesia adalah Jakarta',
                'Siapa presiden pertama Indonesia?'
            ],
            'A': ['3', '', '', '', 'Soekarno'],
            'B': ['4', '', '', '', 'Soeharto'],
            'C': ['5', '', '', '', 'Habibie'],
            'D': ['6', '', '', '', 'Megawati'],
            'E': ['7', '', '', '', 'SBY'],
            'KUNCI': ['B', 'benar', '', 'benar', 'Soekarno'],  # Mix of formats
            'BOBOT': [1, 1, 2, 1, 1],
            'MAPEL': ['Matematika', 'IPA', 'IPA', 'IPA', 'IPS']
        }
        df = pd.DataFrame(data)
        
        # Save to Excel
        excel_buffer = BytesIO()
        df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        
        # Upload
        files = {'file': ('test_soal.xlsx', excel_buffer, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        r = requests.post(f"{BASE_URL}/questions/import", files=files,
                         headers={"Authorization": f"Bearer {self.admin_token}"})
        assert r.status_code == 200, f"Import failed: {r.status_code} {r.text}"
        
        result = r.json()
        self.log(f"Import result: {result['imported']} imported, {len(result.get('errors', []))} errors")
        assert result['imported'] == 5, f"Expected 5 questions imported, got {result['imported']}"
        assert len(result.get('errors', [])) == 0, f"Got errors: {result.get('errors')}"
        
        # Verify questions were created
        r = requests.get(f"{BASE_URL}/questions", headers={"Authorization": f"Bearer {self.admin_token}"})
        questions = r.json()
        
        # Find our imported questions
        imported_q = [q for q in questions if q['text'] in [
            'Berapa hasil 2 + 2?',
            'Matahari terbit dari timur',
            'Jelaskan proses fotosintesis',
            'Ibu kota Indonesia adalah Jakarta',
            'Siapa presiden pertama Indonesia?'
        ]]
        
        assert len(imported_q) == 5, f"Expected 5 questions in DB, found {len(imported_q)}"
        
        # Store for cleanup
        self.temp_questions.extend([q['id'] for q in imported_q])
        
        # Verify types were inferred correctly
        q1 = next(q for q in imported_q if q['text'] == 'Berapa hasil 2 + 2?')
        assert q1['type'] == 'pg', f"Q1 should be pg, got {q1['type']}"
        assert q1['correct_answer'] == '1', f"Q1 correct should be '1' (B), got {q1['correct_answer']}"
        
        q2 = next(q for q in imported_q if q['text'] == 'Matahari terbit dari timur')
        assert q2['type'] == 'truefalse', f"Q2 should be truefalse, got {q2['type']}"
        assert q2['correct_answer'] == 'true', f"Q2 correct should be 'true', got {q2['correct_answer']}"
        
        q3 = next(q for q in imported_q if q['text'] == 'Jelaskan proses fotosintesis')
        assert q3['type'] == 'essay', f"Q3 should be essay, got {q3['type']}"
        
        q4 = next(q for q in imported_q if q['text'] == 'Ibu kota Indonesia adalah Jakarta')
        assert q4['type'] == 'truefalse', f"Q4 should be truefalse (benar key), got {q4['type']}"
        
        q5 = next(q for q in imported_q if q['text'] == 'Siapa presiden pertama Indonesia?')
        assert q5['type'] == 'pg', f"Q5 should be pg, got {q5['type']}"
        # Verify literal answer text mapping
        assert q5['correct_answer'] == '0', f"Q5 correct should be '0' (A=Soekarno), got {q5['correct_answer']}"
        
        # Verify categories were auto-created
        r = requests.get(f"{BASE_URL}/categories", headers={"Authorization": f"Bearer {self.admin_token}"})
        categories = r.json()
        cat_names = [c['name'] for c in categories]
        
        assert 'Matematika' in cat_names, "Matematika category not created"
        assert 'IPA' in cat_names, "IPA category not created"
        assert 'IPS' in cat_names, "IPS category not created"
        
        # Store for cleanup
        new_cats = [c for c in categories if c['name'] in ['Matematika', 'IPA', 'IPS']]
        self.temp_categories.extend([c['id'] for c in new_cats])

    def _test_question_import_official_template(self):
        """Test question import with official template columns"""
        data = {
            'type': ['pg', 'truefalse', 'essay'],
            'text': ['Test PG Question', 'Test TF Question', 'Test Essay Question'],
            'option_a': ['Option A', '', ''],
            'option_b': ['Option B', '', ''],
            'option_c': ['Option C', '', ''],
            'option_d': ['Option D', '', ''],
            'option_e': ['Option E', '', ''],
            'correct': ['E', 'true', ''],
            'weight': [1, 1, 2],
            'category': ['Test Category', 'Test Category', 'Test Category'],
            'image_url': ['', '', '']
        }
        df = pd.DataFrame(data)
        
        excel_buffer = BytesIO()
        df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        
        files = {'file': ('test_official.xlsx', excel_buffer, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        r = requests.post(f"{BASE_URL}/questions/import", files=files,
                         headers={"Authorization": f"Bearer {self.admin_token}"})
        assert r.status_code == 200, f"Import failed: {r.status_code} {r.text}"
        
        result = r.json()
        assert result['imported'] == 3, f"Expected 3 questions imported, got {result['imported']}"
        
        # Verify correct answer E works
        r = requests.get(f"{BASE_URL}/questions", headers={"Authorization": f"Bearer {self.admin_token}"})
        questions = r.json()
        test_pg = next((q for q in questions if q['text'] == 'Test PG Question'), None)
        assert test_pg, "Test PG Question not found"
        assert test_pg['correct_answer'] == '4', f"Correct answer should be '4' (E), got {test_pg['correct_answer']}"
        
        self.temp_questions.append(test_pg['id'])

    def _test_account_import_nisn_generation(self):
        """Test account import with NISN-based email/password generation"""
        data = {
            'NO': [1, 2],
            'NAMA': ['Test Siswa 1', 'Test Siswa 2'],
            'NISN': ['1234567890', '0987654321'],
            'KELAS': ['Kelas Test-A', 'Kelas Test-A']
        }
        df = pd.DataFrame(data)
        
        excel_buffer = BytesIO()
        df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        
        files = {'file': ('test_akun.xlsx', excel_buffer, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        r = requests.post(f"{BASE_URL}/users/import", files=files,
                         headers={"Authorization": f"Bearer {self.admin_token}"})
        assert r.status_code == 200, f"Import failed: {r.status_code} {r.text}"
        
        result = r.json()
        self.log(f"Account import result: {result['imported']} imported, {result['updated']} updated")
        assert result['imported'] == 2, f"Expected 2 accounts imported, got {result['imported']}"
        assert 'notes' in result, "Notes field missing from response"
        
        # Verify notes contain email generation info
        notes_text = ' '.join(result.get('notes', []))
        assert '1234567890@siswa.sekolah.id' in notes_text, "Email generation note not found"
        
        # Verify accounts were created with generated emails
        r = requests.get(f"{BASE_URL}/users?role=siswa", headers={"Authorization": f"Bearer {self.admin_token}"})
        users = r.json()
        
        test_users = [u for u in users if u['name'] in ['Test Siswa 1', 'Test Siswa 2']]
        assert len(test_users) == 2, f"Expected 2 test users, found {len(test_users)}"
        
        user1 = next(u for u in test_users if u['name'] == 'Test Siswa 1')
        assert user1['email'] == '1234567890@siswa.sekolah.id', f"Email should be NISN-based, got {user1['email']}"
        assert user1['identifier'] == '1234567890', f"NISN should be stored, got {user1['identifier']}"
        
        self.temp_users.extend([u['id'] for u in test_users])
        
        # Verify login with NISN as password
        try:
            token = self.login('1234567890@siswa.sekolah.id', '1234567890')
            assert token, "Login with NISN password failed"
            self.log("✓ Login with NISN password successful")
        except Exception as e:
            raise AssertionError(f"Login with NISN password failed: {e}")
        
        # Verify class was auto-created
        r = requests.get(f"{BASE_URL}/classes", headers={"Authorization": f"Bearer {self.admin_token}"})
        classes = r.json()
        
        test_class = next((c for c in classes if c['name'] == 'Kelas Test-A'), None)
        assert test_class, "Kelas Test-A not auto-created"
        assert test_class['student_count'] == 2, f"Class should have 2 students, got {test_class['student_count']}"
        
        self.temp_classes.append(test_class['id'])

    def _test_account_import_existing_update(self):
        """Test that existing emails are updated, not duplicated"""
        # First import
        data = {
            'nama': ['Update Test User'],
            'email': ['updatetest@test.com'],
            'password': ['pass123'],
            'role': ['siswa'],
            'identifier': ['TEST001'],
            'kelas': ['']
        }
        df = pd.DataFrame(data)
        excel_buffer = BytesIO()
        df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        
        files = {'file': ('test1.xlsx', excel_buffer, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        r = requests.post(f"{BASE_URL}/users/import", files=files,
                         headers={"Authorization": f"Bearer {self.admin_token}"})
        assert r.status_code == 200
        result1 = r.json()
        assert result1['imported'] == 1
        
        # Second import with same email but different name
        data2 = {
            'nama': ['Updated Name'],
            'email': ['updatetest@test.com'],
            'password': ['newpass123'],
            'role': ['guru'],
            'identifier': ['TEST002'],
            'kelas': ['']
        }
        df2 = pd.DataFrame(data2)
        excel_buffer2 = BytesIO()
        df2.to_excel(excel_buffer2, index=False, engine='openpyxl')
        excel_buffer2.seek(0)
        
        files2 = {'file': ('test2.xlsx', excel_buffer2, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        r2 = requests.post(f"{BASE_URL}/users/import", files=files2,
                          headers={"Authorization": f"Bearer {self.admin_token}"})
        assert r2.status_code == 200
        result2 = r2.json()
        assert result2['updated'] == 1, f"Expected 1 updated, got {result2['updated']}"
        assert result2['imported'] == 0, f"Expected 0 imported (should update), got {result2['imported']}"
        
        # Verify only one user exists with that email
        r = requests.get(f"{BASE_URL}/users", headers={"Authorization": f"Bearer {self.admin_token}"})
        users = r.json()
        matching = [u for u in users if u['email'] == 'updatetest@test.com']
        assert len(matching) == 1, f"Expected 1 user, found {len(matching)} (duplicated)"
        assert matching[0]['name'] == 'Updated Name', "Name should be updated"
        assert matching[0]['role'] == 'guru', "Role should be updated"
        
        self.temp_users.append(matching[0]['id'])

    def _test_guru_permission_denied(self):
        """Test that guru gets 403 on import endpoints"""
        # Test user import
        data = {'nama': ['Test'], 'email': ['test@test.com'], 'password': ['test'], 'role': ['siswa'], 'identifier': [''], 'kelas': ['']}
        df = pd.DataFrame(data)
        excel_buffer = BytesIO()
        df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        
        files = {'file': ('test.xlsx', excel_buffer, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        r = requests.post(f"{BASE_URL}/users/import", files=files,
                         headers={"Authorization": f"Bearer {self.guru_token}"})
        assert r.status_code == 403, f"Expected 403 for guru on user import, got {r.status_code}"
        
        # Test template download
        r2 = requests.get(f"{BASE_URL}/users/import-template",
                         headers={"Authorization": f"Bearer {self.guru_token}"})
        assert r2.status_code == 403, f"Expected 403 for guru on template, got {r2.status_code}"

    def _test_template_includes_kelas(self):
        """Test that user import template includes kelas column"""
        r = requests.get(f"{BASE_URL}/users/import-template",
                        headers={"Authorization": f"Bearer {self.admin_token}"})
        assert r.status_code == 200
        
        content = r.content.decode('utf-8')
        assert 'kelas' in content.lower(), "Template should include 'kelas' column"

    def run_all_tests(self):
        """Run all import feature tests."""
        self.log("=" * 70)
        self.log("BACKEND API TESTS - Indonesian Excel Import Features")
        self.log("=" * 70)

        try:
            # Authentication
            self.log("\n--- Authentication ---")
            self.test("Login as admin", self._test_login_admin)
            self.test("Login as guru", self._test_login_guru)

            # Question Import Tests
            self.log("\n--- Question Import Tests ---")
            self.test("Question import with Indonesian headers (NO, BUTIR SOAL, A-E, KUNCI, BOBOT, MAPEL)",
                     self._test_question_import_indonesian_headers)
            self.test("Question import with official template (type, option_a-e, correct=E)",
                     self._test_question_import_official_template)

            # Account Import Tests
            self.log("\n--- Account Import Tests ---")
            self.test("Account import with NISN generation (NO, NAMA, NISN, KELAS)",
                     self._test_account_import_nisn_generation)
            self.test("Account import updates existing emails (no duplication)",
                     self._test_account_import_existing_update)

            # Permission Tests
            self.log("\n--- Permission Tests ---")
            self.test("Guru gets 403 on user import endpoints",
                     self._test_guru_permission_denied)

            # Template Tests
            self.log("\n--- Template Tests ---")
            self.test("User import template includes kelas column",
                     self._test_template_includes_kelas)

        finally:
            # Cleanup
            self.log("\n--- Cleanup ---")
            self.cleanup()
            self.log("Cleanup completed")

        # Summary
        self.log("\n" + "=" * 70)
        self.log(f"RESULTS: {self.tests_passed}/{self.tests_run} tests passed")
        self.log("=" * 70)
        
        return 0 if self.tests_passed == self.tests_run else 1


if __name__ == "__main__":
    runner = ImportTestRunner()
    sys.exit(runner.run_all_tests())
