#!/usr/bin/env python3
"""
Comprehensive backend API test for Indonesian CBT/Ujian Online platform
Tests all critical user-facing flows for admin, guru, and siswa roles
"""

import requests
import sys
import time
from datetime import datetime, timedelta

class CBTAPITester:
    def __init__(self, base_url="https://github-auto-build.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.guru_token = None
        self.siswa_token = None
        self.siswa2_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        
        # Store IDs for testing
        self.category_id = None
        self.question_id = None
        self.package_id = None
        self.session_id = None
        self.class_id = None
        self.attempt_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None, files=None, check_json=True):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        self.tests_run += 1
        print(f"\n🔍 Test {self.tests_run}: {name}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                if files:
                    response = requests.post(url, headers=headers, files=files, timeout=30)
                else:
                    headers['Content-Type'] = 'application/json'
                    response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                headers['Content-Type'] = 'application/json'
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ PASS - Status: {response.status_code}")
                if check_json and response.status_code not in [204]:
                    try:
                        return True, response.json()
                    except Exception:
                        return True, {}
                return True, {}
            else:
                print(f"❌ FAIL - Expected {expected_status}, got {response.status_code}")
                try:
                    print(f"   Response: {response.text[:200]}")
                except Exception:
                    pass
                self.failed_tests.append(f"{name} (expected {expected_status}, got {response.status_code})")
                return False, {}

        except Exception as e:
            print(f"❌ FAIL - Error: {str(e)}")
            self.failed_tests.append(f"{name} (error: {str(e)})")
            return False, {}

    def test_login(self, email, password, role_name):
        """Test login and get token"""
        print(f"\n{'='*60}")
        print(f"Testing {role_name} login: {email}")
        print('='*60)
        success, response = self.run_test(
            f"Login as {role_name}",
            "POST",
            "auth/login",
            200,
            data={"email": email, "password": password}
        )
        if success and 'token' in response:
            token = response['token']
            print(f"✅ Token obtained for {role_name}")
            return token
        return None

    def test_auth_me(self, token, role_name):
        """Test /auth/me endpoint"""
        success, response = self.run_test(
            f"Get current user info ({role_name})",
            "GET",
            "auth/me",
            200,
            token=token
        )
        return success

    def test_dashboard_stats(self, token):
        """Test admin dashboard stats"""
        print(f"\n{'='*60}")
        print("Testing Admin Dashboard")
        print('='*60)
        success, response = self.run_test(
            "Get dashboard stats",
            "GET",
            "dashboard/stats",
            200,
            token=token
        )
        if success:
            print(f"   Stats: {response}")
        return success

    def test_categories_crud(self, token):
        """Test category CRUD operations"""
        print(f"\n{'='*60}")
        print("Testing Kategori Materi CRUD")
        print('='*60)
        
        # List categories
        success, response = self.run_test(
            "List categories",
            "GET",
            "categories",
            200,
            token=token
        )
        
        # Create category
        success, response = self.run_test(
            "Create category",
            "POST",
            "categories",
            200,
            data={"name": "Test Matematika", "description": "Test category"},
            token=token
        )
        if success and 'id' in response:
            self.category_id = response['id']
            print(f"   Created category ID: {self.category_id}")
        
        # Update category
        if self.category_id:
            success, response = self.run_test(
                "Update category",
                "PUT",
                f"categories/{self.category_id}",
                200,
                data={"name": "Test Matematika Updated", "description": "Updated"},
                token=token
            )
        
        return success

    def test_questions_crud(self, token):
        """Test bank soal CRUD operations"""
        print(f"\n{'='*60}")
        print("Testing Bank Soal CRUD")
        print('='*60)
        
        # List questions
        success, response = self.run_test(
            "List questions",
            "GET",
            "questions",
            200,
            token=token
        )
        
        # Create PG question
        success, response = self.run_test(
            "Create PG question",
            "POST",
            "questions",
            200,
            data={
                "category_id": self.category_id,
                "type": "pg",
                "text": "Berapa hasil 2+2?",
                "options": ["3", "4", "5", "6"],
                "correct_answer": "1",
                "weight": 1.0
            },
            token=token
        )
        if success and 'id' in response:
            self.question_id = response['id']
            print(f"   Created question ID: {self.question_id}")
        
        # Create True/False question
        success, response = self.run_test(
            "Create True/False question",
            "POST",
            "questions",
            200,
            data={
                "category_id": self.category_id,
                "type": "truefalse",
                "text": "Bumi itu bulat",
                "correct_answer": "true",
                "weight": 1.0
            },
            token=token
        )
        
        # Create Essay question
        success, response = self.run_test(
            "Create Essay question",
            "POST",
            "questions",
            200,
            data={
                "category_id": self.category_id,
                "type": "essay",
                "text": "Jelaskan teorema Pythagoras",
                "weight": 2.0
            },
            token=token
        )
        
        # Update question
        if self.question_id:
            success, response = self.run_test(
                "Update question",
                "PUT",
                f"questions/{self.question_id}",
                200,
                data={
                    "category_id": self.category_id,
                    "type": "pg",
                    "text": "Berapa hasil 2+2? (Updated)",
                    "options": ["3", "4", "5", "6"],
                    "correct_answer": "1",
                    "weight": 1.5
                },
                token=token
            )
        
        # Test import template download
        success, response = self.run_test(
            "Download import template",
            "GET",
            "questions/import-template",
            200,
            token=token,
            check_json=False
        )
        
        return success

    def test_packages_crud(self, token):
        """Test paket soal CRUD operations"""
        print(f"\n{'='*60}")
        print("Testing Paket Soal CRUD")
        print('='*60)
        
        # List packages
        success, response = self.run_test(
            "List packages",
            "GET",
            "packages",
            200,
            token=token
        )
        
        # Get existing package for testing
        if response and len(response) > 0:
            existing_pkg = response[0]
            pkg_id = existing_pkg.get('id')
            
            # Test duplicate package
            if pkg_id:
                success, dup_response = self.run_test(
                    "Duplicate package",
                    "POST",
                    f"packages/{pkg_id}/duplicate",
                    200,
                    token=token
                )
                if success and 'id' in dup_response:
                    print(f"   Duplicated package ID: {dup_response['id']}")
        
        # Create new package
        success, response = self.run_test(
            "Create package",
            "POST",
            "packages",
            200,
            data={
                "title": "Test Package",
                "description": "Test package description",
                "category_id": self.category_id,
                "question_ids": [self.question_id] if self.question_id else [],
                "scoring_method": "percentage",
                "shuffle_questions": False,
                "shuffle_options": False,
                "is_public": True,
                "min_score": 0,
                "rounding": "2desimal"
            },
            token=token
        )
        if success and 'id' in response:
            self.package_id = response['id']
            print(f"   Created package ID: {self.package_id}")
        
        # Update package (toggle public)
        if self.package_id:
            success, response = self.run_test(
                "Update package (toggle public)",
                "PUT",
                f"packages/{self.package_id}",
                200,
                data={
                    "title": "Test Package Updated",
                    "description": "Updated description",
                    "category_id": self.category_id,
                    "question_ids": [self.question_id] if self.question_id else [],
                    "scoring_method": "weighted",
                    "shuffle_questions": True,
                    "shuffle_options": True,
                    "is_public": False,
                    "min_score": 40,
                    "rounding": "bulat"
                },
                token=token
            )
        
        return success

    def test_classes_crud(self, token):
        """Test manajemen kelas CRUD"""
        print(f"\n{'='*60}")
        print("Testing Manajemen Kelas CRUD")
        print('='*60)
        
        # List classes
        success, response = self.run_test(
            "List classes",
            "GET",
            "classes",
            200,
            token=token
        )
        
        # Create class
        success, response = self.run_test(
            "Create class",
            "POST",
            "classes",
            200,
            data={
                "name": "Kelas Test",
                "description": "Test class",
                "member_ids": []
            },
            token=token
        )
        if success and 'id' in response:
            self.class_id = response['id']
            print(f"   Created class ID: {self.class_id}")
        
        # Update class
        if self.class_id:
            success, response = self.run_test(
                "Update class",
                "PUT",
                f"classes/{self.class_id}",
                200,
                data={
                    "name": "Kelas Test Updated",
                    "description": "Updated class",
                    "member_ids": []
                },
                token=token
            )
        
        # Test export class xlsx
        if self.class_id:
            success, response = self.run_test(
                "Export class xlsx",
                "GET",
                f"export/class/{self.class_id}/xlsx",
                200,
                token=token,
                check_json=False
            )
        
        return success

    def test_sessions_crud(self, token):
        """Test sesi pelaksanaan CRUD"""
        print(f"\n{'='*60}")
        print("Testing Sesi Pelaksanaan CRUD")
        print('='*60)
        
        # List sessions
        success, response = self.run_test(
            "List sessions",
            "GET",
            "sessions",
            200,
            token=token
        )
        
        # Get existing session for exam flow
        if response and len(response) > 0:
            for sess in response:
                if sess.get('status') == 'berlangsung':
                    self.session_id = sess.get('id')
                    print(f"   Found active session ID: {self.session_id}")
                    break
        
        # Create session
        start_time = (datetime.now() + timedelta(hours=1)).isoformat()
        end_time = (datetime.now() + timedelta(hours=3)).isoformat()
        
        # Get a valid package_id for session creation
        valid_package_id = self.package_id
        if not valid_package_id:
            # Get first available package
            list_success, packages = self.run_test(
                "Get packages for session",
                "GET",
                "packages",
                200,
                token=token
            )
            if list_success and packages and len(packages) > 0:
                valid_package_id = packages[0].get('id')
        
        if valid_package_id:
            success, response = self.run_test(
                "Create session",
                "POST",
                "sessions",
                200,
                data={
                    "title": "Test Session",
                    "package_id": valid_package_id,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration_minutes": 60,
                    "kkm": 75,
                    "class_ids": [],
                    "announcement": "Test announcement"
                },
                token=token
            )
            if success and 'id' in response:
                new_session_id = response['id']
                print(f"   Created session ID: {new_session_id}")
            
            # Update session
            if self.session_id:
                success, response = self.run_test(
                    "Update session",
                    "PUT",
                    f"sessions/{self.session_id}",
                    200,
                    data={
                        "title": "Updated Session",
                        "package_id": valid_package_id,
                        "start_time": start_time,
                        "end_time": end_time,
                        "duration_minutes": 90,
                        "kkm": 70,
                        "class_ids": [],
                        "announcement": "Updated announcement"
                    },
                    token=token
                )
        else:
            print("⚠️  No valid package_id available, skipping session creation/update")
        
        return success

    def test_student_exam_flow(self, token):
        """Test student exam flow: start, answer, autosave, submit"""
        print(f"\n{'='*60}")
        print("Testing Student Exam Flow")
        print('='*60)
        
        if not self.session_id:
            print("⚠️  No active session found, skipping exam flow")
            return False
        
        # Start exam
        success, response = self.run_test(
            "Start exam",
            "POST",
            "exam/start",
            200,
            data={"session_id": self.session_id},
            token=token
        )
        if success and 'attempt_id' in response:
            self.attempt_id = response['attempt_id']
            questions = response.get('questions', [])
            print(f"   Started attempt ID: {self.attempt_id}")
            print(f"   Questions count: {len(questions)}")
            
            # Prepare answers
            answers = {}
            for q in questions:
                qid = q.get('id')
                qtype = q.get('type')
                if qtype == 'pg':
                    answers[qid] = "0"  # First option
                elif qtype == 'truefalse':
                    answers[qid] = "true"
                elif qtype == 'essay':
                    answers[qid] = "Ini adalah jawaban essay test"
            
            # Autosave progress
            success, response = self.run_test(
                "Autosave exam progress",
                "POST",
                f"exam/save/{self.session_id}",
                200,
                data={"answers": answers},
                token=token
            )
            
            # Submit exam
            success, response = self.run_test(
                "Submit exam",
                "POST",
                "exam/submit",
                200,
                data={
                    "session_id": self.session_id,
                    "answers": answers
                },
                token=token
            )
            if success:
                print(f"   Exam submitted successfully")
                if 'score' in response:
                    print(f"   Score: {response['score']}")
            
            return success
        
        return False

    def test_results_and_grading(self, admin_token, guru_token, siswa_token):
        """Test hasil & koreksi features"""
        print(f"\n{'='*60}")
        print("Testing Hasil & Koreksi")
        print('='*60)
        
        # Get results by session (admin/guru)
        if self.session_id:
            success, response = self.run_test(
                "Get results by session",
                "GET",
                f"results/session/{self.session_id}",
                200,
                token=admin_token
            )
        
        # Get my results (siswa)
        success, response = self.run_test(
            "Get my results (siswa)",
            "GET",
            "results/me",
            200,
            token=siswa_token
        )
        
        # Get result detail
        if self.attempt_id:
            success, response = self.run_test(
                "Get result detail",
                "GET",
                f"results/detail/{self.attempt_id}",
                200,
                token=admin_token
            )
            
            # Grade essay (if any)
            success, response = self.run_test(
                "Grade essay",
                "POST",
                f"results/grade/{self.attempt_id}",
                200,
                data={"scores": {}},
                token=guru_token
            )
            
            # Download kartu hasil PDF
            success, response = self.run_test(
                "Download kartu hasil PDF",
                "GET",
                f"results/detail/{self.attempt_id}/pdf",
                200,
                token=admin_token,
                check_json=False
            )
        
        # Test analytics
        if self.session_id:
            success, response = self.run_test(
                "Get session analytics (Analitik Butir)",
                "GET",
                f"analytics/session/{self.session_id}",
                200,
                token=admin_token
            )
        
        return success

    def test_leaderboards(self, admin_token, siswa_token):
        """Test peringkat kelas and angkatan"""
        print(f"\n{'='*60}")
        print("Testing Peringkat (Leaderboards)")
        print('='*60)
        
        # Global leaderboard (angkatan)
        success, response = self.run_test(
            "Get global leaderboard (angkatan)",
            "GET",
            "leaderboard/global",
            200,
            token=admin_token
        )
        
        # My leaderboard (siswa)
        success, response = self.run_test(
            "Get my leaderboard (siswa)",
            "GET",
            "leaderboard/me",
            200,
            token=siswa_token
        )
        
        # Class leaderboard
        if self.class_id:
            success, response = self.run_test(
                "Get class leaderboard",
                "GET",
                f"leaderboard/class/{self.class_id}",
                200,
                token=admin_token
            )
        
        # Export leaderboard xlsx
        success, response = self.run_test(
            "Export leaderboard xlsx",
            "GET",
            "export/leaderboard/xlsx",
            200,
            token=admin_token,
            check_json=False
        )
        
        return success

    def test_analytics(self, token):
        """Test analytics endpoints"""
        print(f"\n{'='*60}")
        print("Testing Analytics")
        print('='*60)
        
        # Analytics classes
        success, response = self.run_test(
            "Get analytics classes",
            "GET",
            "analytics/classes",
            200,
            token=token
        )
        
        # Analytics subjects
        success, response = self.run_test(
            "Get analytics subjects",
            "GET",
            "analytics/subjects",
            200,
            token=token
        )
        
        return success

    def test_pdfs(self, admin_token):
        """Test PDF downloads"""
        print(f"\n{'='*60}")
        print("Testing PDF Downloads")
        print('='*60)
        
        # Get a student ID for rapor
        success, response = self.run_test(
            "List users to get student ID",
            "GET",
            "users?role=siswa",
            200,
            token=admin_token
        )
        
        student_id = None
        if success and response and len(response) > 0:
            student_id = response[0].get('id')
        
        # Student rapor PDF
        if student_id:
            success, response = self.run_test(
                "Download student rapor PDF",
                "GET",
                f"report/student/{student_id}/pdf",
                200,
                token=admin_token,
                check_json=False
            )
        
        # Class rapor PDF
        if self.class_id:
            success, response = self.run_test(
                "Download class rapor PDF",
                "GET",
                f"report/class/{self.class_id}/pdf",
                200,
                token=admin_token,
                check_json=False
            )
        
        return success

    def test_settings(self, admin_token):
        """Test pengaturan sekolah and difficulty thresholds"""
        print(f"\n{'='*60}")
        print("Testing Pengaturan")
        print('='*60)
        
        # Get school settings
        success, response = self.run_test(
            "Get school settings",
            "GET",
            "settings/school",
            200,
            token=admin_token
        )
        
        # Update school settings
        success, response = self.run_test(
            "Update school settings",
            "PUT",
            "settings/school",
            200,
            data={
                "school_name": "Test School",
                "school_address": "Test Address",
                "theme_color": "green"
            },
            token=admin_token
        )
        
        # Get difficulty thresholds
        success, response = self.run_test(
            "Get difficulty thresholds",
            "GET",
            "settings/difficulty",
            200,
            token=admin_token
        )
        
        # Update difficulty thresholds
        success, response = self.run_test(
            "Update difficulty thresholds",
            "PUT",
            "settings/difficulty",
            200,
            data={
                "easy_min": 70,
                "medium_min": 40
            },
            token=admin_token
        )
        
        return success

    def test_notifications(self, siswa_token):
        """Test student notifications"""
        print(f"\n{'='*60}")
        print("Testing Notifications")
        print('='*60)
        
        success, response = self.run_test(
            "Get student notifications",
            "GET",
            "notifications",
            200,
            token=siswa_token
        )
        
        return success

    def test_users_crud(self, admin_token):
        """Test manajemen akun CRUD"""
        print(f"\n{'='*60}")
        print("Testing Manajemen Akun CRUD")
        print('='*60)
        
        # List users
        success, response = self.run_test(
            "List all users",
            "GET",
            "users",
            200,
            token=admin_token
        )
        
        # Create user
        success, response = self.run_test(
            "Create user",
            "POST",
            "users",
            200,
            data={
                "email": f"test_{int(time.time())}@test.com",
                "password": "test123",
                "name": "Test User",
                "role": "siswa",
                "identifier": "12345"
            },
            token=admin_token
        )
        
        test_user_id = None
        if success and 'id' in response:
            test_user_id = response['id']
            print(f"   Created user ID: {test_user_id}")
        
        # Update user
        if test_user_id:
            success, response = self.run_test(
                "Update user",
                "PUT",
                f"users/{test_user_id}",
                200,
                data={
                    "name": "Test User Updated"
                },
                token=admin_token
            )
        
        # Delete user
        if test_user_id:
            success, response = self.run_test(
                "Delete user",
                "DELETE",
                f"users/{test_user_id}",
                200,
                token=admin_token
            )
        
        return success

    def test_role_permissions(self, siswa_token):
        """Test role permission checks (siswa should get 403 on admin endpoints)"""
        print(f"\n{'='*60}")
        print("Testing Role Permissions")
        print('='*60)
        
        # Siswa trying to access admin endpoint (should fail with 403)
        success, response = self.run_test(
            "Siswa accessing admin endpoint (should be 403)",
            "GET",
            "users",
            403,
            token=siswa_token
        )
        
        # Siswa trying to create user (should fail with 403)
        success, response = self.run_test(
            "Siswa creating user (should be 403)",
            "POST",
            "users",
            403,
            data={
                "email": "test@test.com",
                "password": "test123",
                "name": "Test",
                "role": "siswa"
            },
            token=siswa_token
        )
        
        return success

    def cleanup(self, token):
        """Clean up test data"""
        print(f"\n{'='*60}")
        print("Cleaning up test data")
        print('='*60)
        
        # Delete test package
        if self.package_id:
            self.run_test(
                "Delete test package",
                "DELETE",
                f"packages/{self.package_id}",
                200,
                token=token
            )
        
        # Delete test question
        if self.question_id:
            self.run_test(
                "Delete test question",
                "DELETE",
                f"questions/{self.question_id}",
                200,
                token=token
            )
        
        # Delete test category
        if self.category_id:
            self.run_test(
                "Delete test category",
                "DELETE",
                f"categories/{self.category_id}",
                200,
                token=token
            )
        
        # Delete test class
        if self.class_id:
            self.run_test(
                "Delete test class",
                "DELETE",
                f"classes/{self.class_id}",
                200,
                token=token
            )

def main():
    print("="*60)
    print("CBT/Ujian Online - Comprehensive Backend API Test")
    print("="*60)
    
    tester = CBTAPITester()
    
    # Test credentials from /app/memory/test_credentials.md and PRD
    admin_email = "hitoria532@gmail.com"
    admin_password = "admin123"
    guru_email = "guru@sekolah.id"
    guru_password = "guru123"
    siswa_email = "siswa@sekolah.id"
    siswa_password = "siswa123"
    siswa2_email = "siswa2@sekolah.id"
    siswa2_password = "siswa123"
    
    # 1. Test login for all roles
    tester.admin_token = tester.test_login(admin_email, admin_password, "Admin")
    if not tester.admin_token:
        print("❌ Admin login failed, stopping tests")
        return 1
    
    tester.guru_token = tester.test_login(guru_email, guru_password, "Guru")
    if not tester.guru_token:
        print("❌ Guru login failed, stopping tests")
        return 1
    
    tester.siswa_token = tester.test_login(siswa_email, siswa_password, "Siswa")
    if not tester.siswa_token:
        print("❌ Siswa login failed, stopping tests")
        return 1
    
    tester.siswa2_token = tester.test_login(siswa2_email, siswa2_password, "Siswa2")
    if not tester.siswa2_token:
        print("⚠️  Siswa2 login failed, continuing with other tests")
    
    # 2. Test auth/me for all roles
    tester.test_auth_me(tester.admin_token, "Admin")
    tester.test_auth_me(tester.guru_token, "Guru")
    tester.test_auth_me(tester.siswa_token, "Siswa")
    
    # 3. Test admin dashboard
    tester.test_dashboard_stats(tester.admin_token)
    
    # 4. Test categories CRUD
    tester.test_categories_crud(tester.guru_token)
    
    # 5. Test questions CRUD
    tester.test_questions_crud(tester.guru_token)
    
    # 6. Test packages CRUD
    tester.test_packages_crud(tester.guru_token)
    
    # 7. Test classes CRUD
    tester.test_classes_crud(tester.admin_token)
    
    # 8. Test sessions CRUD
    tester.test_sessions_crud(tester.guru_token)
    
    # 9. Test student exam flow (if siswa2 token available)
    if tester.siswa2_token:
        tester.test_student_exam_flow(tester.siswa2_token)
    
    # 10. Test results and grading
    tester.test_results_and_grading(tester.admin_token, tester.guru_token, tester.siswa_token)
    
    # 11. Test leaderboards
    tester.test_leaderboards(tester.admin_token, tester.siswa_token)
    
    # 12. Test analytics
    tester.test_analytics(tester.admin_token)
    
    # 13. Test PDFs
    tester.test_pdfs(tester.admin_token)
    
    # 14. Test settings
    tester.test_settings(tester.admin_token)
    
    # 15. Test notifications
    tester.test_notifications(tester.siswa_token)
    
    # 16. Test users CRUD
    tester.test_users_crud(tester.admin_token)
    
    # 17. Test role permissions
    tester.test_role_permissions(tester.siswa_token)
    
    # 18. Cleanup
    tester.cleanup(tester.admin_token)
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Total tests run: {tester.tests_run}")
    print(f"Tests passed: {tester.tests_passed}")
    print(f"Tests failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run*100):.1f}%")
    
    if tester.failed_tests:
        print("\n❌ Failed tests:")
        for i, test in enumerate(tester.failed_tests, 1):
            print(f"   {i}. {test}")
    
    print("="*60)
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
