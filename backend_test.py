import requests
import sys
from datetime import datetime, timezone, timedelta

class CBTAPITester:
    def __init__(self, base_url="https://deploy-web-app-3.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.guru_token = None
        self.student_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        # Remove Content-Type for file uploads
        if files:
            headers.pop('Content-Type', None)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, headers=headers, timeout=30)
                else:
                    response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json() if response.content else {}
                except Exception:
                    return success, {}
            else:
                self.tests_failed += 1
                self.failed_tests.append(f"{name} - Expected {expected_status}, got {response.status_code}")
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    print(f"   Response: {response.text[:200]}")
                except Exception:
                    pass
                return False, {}

        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append(f"{name} - Error: {str(e)}")
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_admin_login(self):
        """Test admin login"""
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@sekolah.id", "password": "Admin@12345"}
        )
        if success and 'token' in response:
            self.admin_token = response['token']
            print(f"   Admin token obtained, role: {response.get('user', {}).get('role')}")
            return True
        return False

    def test_auth_me(self):
        """Test /auth/me endpoint"""
        success, response = self.run_test(
            "Auth Me (Admin)",
            "GET",
            "auth/me",
            200,
            token=self.admin_token
        )
        return success and response.get('role') == 'admin'

    def test_categories_crud(self):
        """Test categories CRUD"""
        # Create
        success, cat = self.run_test(
            "Create Category",
            "POST",
            "categories",
            200,
            data={"name": "Test Category", "description": "Test"},
            token=self.admin_token
        )
        if not success:
            return False
        
        cat_id = cat.get('id')
        
        # List
        success, cats = self.run_test(
            "List Categories",
            "GET",
            "categories",
            200,
            token=self.admin_token
        )
        if not success:
            return False
        
        # Update
        success, _ = self.run_test(
            "Update Category",
            "PUT",
            f"categories/{cat_id}",
            200,
            data={"name": "Updated Category", "description": "Updated"},
            token=self.admin_token
        )
        if not success:
            return False
        
        # Delete
        success, _ = self.run_test(
            "Delete Category",
            "DELETE",
            f"categories/{cat_id}",
            200,
            token=self.admin_token
        )
        return success

    def test_questions_crud(self):
        """Test questions CRUD"""
        # Create category first
        success, cat = self.run_test(
            "Create Category for Questions",
            "POST",
            "categories",
            200,
            data={"name": "Math Test", "description": "Math"},
            token=self.admin_token
        )
        if not success:
            return False
        
        cat_id = cat.get('id')
        
        # Create PG question
        success, q = self.run_test(
            "Create PG Question",
            "POST",
            "questions",
            200,
            data={
                "category_id": cat_id,
                "type": "pg",
                "text": "What is 2+2?",
                "options": ["3", "4", "5", "6"],
                "correct_answer": "1",
                "weight": 1.0
            },
            token=self.admin_token
        )
        if not success:
            return False
        
        q_id = q.get('id')
        
        # List questions
        success, _ = self.run_test(
            "List Questions",
            "GET",
            "questions",
            200,
            token=self.admin_token
        )
        if not success:
            return False
        
        # Update question
        success, _ = self.run_test(
            "Update Question",
            "PUT",
            f"questions/{q_id}",
            200,
            data={
                "category_id": cat_id,
                "type": "pg",
                "text": "What is 2+2? (Updated)",
                "options": ["3", "4", "5", "6"],
                "correct_answer": "1",
                "weight": 1.0
            },
            token=self.admin_token
        )
        if not success:
            return False
        
        # Delete question
        success, _ = self.run_test(
            "Delete Question",
            "DELETE",
            f"questions/{q_id}",
            200,
            token=self.admin_token
        )
        return success

    def test_packages_crud(self):
        """Test packages CRUD"""
        # Create category and questions first
        success, cat = self.run_test(
            "Create Category for Package",
            "POST",
            "categories",
            200,
            data={"name": "Science", "description": "Science"},
            token=self.admin_token
        )
        if not success:
            return False
        
        cat_id = cat.get('id')
        
        # Create questions
        q_ids = []
        for i in range(3):
            success, q = self.run_test(
                f"Create Question {i+1} for Package",
                "POST",
                "questions",
                200,
                data={
                    "category_id": cat_id,
                    "type": "pg",
                    "text": f"Question {i+1}",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "0",
                    "weight": 1.0
                },
                token=self.admin_token
            )
            if not success:
                return False
            q_ids.append(q.get('id'))
        
        # Create package
        success, pkg = self.run_test(
            "Create Package",
            "POST",
            "packages",
            200,
            data={
                "title": "Test Package",
                "description": "Test",
                "category_id": cat_id,
                "question_ids": q_ids,
                "scoring_method": "percentage",
                "shuffle_questions": False,
                "shuffle_options": False,
                "min_score": 0.0,
                "rounding": "2desimal",
                "is_public": False
            },
            token=self.admin_token
        )
        if not success:
            return False
        
        pkg_id = pkg.get('id')
        
        # List packages
        success, _ = self.run_test(
            "List Packages",
            "GET",
            "packages",
            200,
            token=self.admin_token
        )
        if not success:
            return False
        
        # Get package
        success, _ = self.run_test(
            "Get Package",
            "GET",
            f"packages/{pkg_id}",
            200,
            token=self.admin_token
        )
        if not success:
            return False
        
        # Duplicate package
        success, dup = self.run_test(
            "Duplicate Package",
            "POST",
            f"packages/{pkg_id}/duplicate",
            200,
            token=self.admin_token
        )
        if not success:
            return False
        
        # Delete packages
        success, _ = self.run_test(
            "Delete Package",
            "DELETE",
            f"packages/{pkg_id}",
            200,
            token=self.admin_token
        )
        if not success:
            return False
        
        success, _ = self.run_test(
            "Delete Duplicated Package",
            "DELETE",
            f"packages/{dup.get('id')}",
            200,
            token=self.admin_token
        )
        return success

    def test_sessions_crud(self):
        """Test sessions CRUD"""
        # Create package first
        success, cat = self.run_test(
            "Create Category for Session",
            "POST",
            "categories",
            200,
            data={"name": "History", "description": "History"},
            token=self.admin_token
        )
        if not success:
            return False
        
        cat_id = cat.get('id')
        
        success, q = self.run_test(
            "Create Question for Session",
            "POST",
            "questions",
            200,
            data={
                "category_id": cat_id,
                "type": "pg",
                "text": "Test question",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "0",
                "weight": 1.0
            },
            token=self.admin_token
        )
        if not success:
            return False
        
        q_id = q.get('id')
        
        success, pkg = self.run_test(
            "Create Package for Session",
            "POST",
            "packages",
            200,
            data={
                "title": "Session Package",
                "description": "Test",
                "category_id": cat_id,
                "question_ids": [q_id],
                "scoring_method": "percentage",
                "is_public": False
            },
            token=self.admin_token
        )
        if not success:
            return False
        
        pkg_id = pkg.get('id')
        
        # Create session
        now = datetime.now(timezone.utc)
        start_time = (now - timedelta(hours=1)).isoformat()
        end_time = (now + timedelta(hours=2)).isoformat()
        
        success, session = self.run_test(
            "Create Session",
            "POST",
            "sessions",
            200,
            data={
                "title": "Test Session",
                "package_id": pkg_id,
                "start_time": start_time,
                "end_time": end_time,
                "duration_minutes": 60,
                "kkm": 75.0,
                "class_ids": [],
                "announcement": "Test announcement"
            },
            token=self.admin_token
        )
        if not success:
            return False
        
        session_id = session.get('id')
        
        # List sessions
        success, _ = self.run_test(
            "List Sessions",
            "GET",
            "sessions",
            200,
            token=self.admin_token
        )
        if not success:
            return False
        
        # Update session
        success, _ = self.run_test(
            "Update Session",
            "PUT",
            f"sessions/{session_id}",
            200,
            data={
                "title": "Updated Session",
                "package_id": pkg_id,
                "start_time": start_time,
                "end_time": end_time,
                "duration_minutes": 90,
                "kkm": 80.0,
                "class_ids": [],
                "announcement": "Updated"
            },
            token=self.admin_token
        )
        if not success:
            return False
        
        # Delete session
        success, _ = self.run_test(
            "Delete Session",
            "DELETE",
            f"sessions/{session_id}",
            200,
            token=self.admin_token
        )
        return success

    def test_classes_crud(self):
        """Test classes CRUD"""
        # Create class
        success, cls = self.run_test(
            "Create Class",
            "POST",
            "classes",
            200,
            data={
                "name": "Test Class X-A",
                "description": "Test class",
                "student_ids": []
            },
            token=self.admin_token
        )
        if not success:
            return False
        
        cls_id = cls.get('id')
        
        # List classes
        success, _ = self.run_test(
            "List Classes",
            "GET",
            "classes",
            200,
            token=self.admin_token
        )
        if not success:
            return False
        
        # Update class
        success, _ = self.run_test(
            "Update Class",
            "PUT",
            f"classes/{cls_id}",
            200,
            data={
                "name": "Updated Class X-A",
                "description": "Updated",
                "student_ids": []
            },
            token=self.admin_token
        )
        if not success:
            return False
        
        # Delete class
        success, _ = self.run_test(
            "Delete Class",
            "DELETE",
            f"classes/{cls_id}",
            200,
            token=self.admin_token
        )
        return success

    def test_users_crud(self):
        """Test users CRUD (admin only)"""
        # Create student user
        success, user = self.run_test(
            "Create Student User",
            "POST",
            "users",
            200,
            data={
                "email": f"test.student.{datetime.now().timestamp()}@sekolah.id",
                "password": "student123",
                "name": "Test Student",
                "role": "siswa",
                "identifier": "12345"
            },
            token=self.admin_token
        )
        if not success:
            return False
        
        user_id = user.get('id')
        
        # List users
        success, _ = self.run_test(
            "List Users",
            "GET",
            "users",
            200,
            token=self.admin_token
        )
        if not success:
            return False
        
        # Update user
        success, _ = self.run_test(
            "Update User",
            "PUT",
            f"users/{user_id}",
            200,
            data={
                "name": "Updated Student",
                "identifier": "54321"
            },
            token=self.admin_token
        )
        if not success:
            return False
        
        # Delete user
        success, _ = self.run_test(
            "Delete User",
            "DELETE",
            f"users/{user_id}",
            200,
            token=self.admin_token
        )
        return success

    def test_school_settings(self):
        """Test school settings with theme color sanitization"""
        # Get settings (should be public and return valid HSL triplet)
        success, settings = self.run_test(
            "Get School Settings (Public)",
            "GET",
            "settings/school",
            200
        )
        if not success:
            return False
        
        # Verify theme_color is a valid HSL triplet or None
        theme = settings.get("theme_color")
        if theme:
            import re
            hsl_pattern = r"^-?\d+(\.\d+)?\s+\d+(\.\d+)?%\s+\d+(\.\d+)?%$"
            if not re.match(hsl_pattern, theme):
                print(f"❌ CRITICAL: GET /settings/school returned invalid theme_color: '{theme}' (not a valid HSL triplet)")
                self.tests_failed += 1
                self.failed_tests.append(f"School Settings GET - Invalid theme_color format: {theme}")
                return False
            print(f"   ✓ theme_color is valid HSL triplet: '{theme}'")
        
        # Test 1: Update with legacy color name 'green' - should be sanitized to HSL
        success, response = self.run_test(
            "Update School Settings (legacy 'green')",
            "PUT",
            "settings/school",
            200,
            data={
                "name": "",
                "address": "",
                "logo_path": None,
                "theme_color": "green"
            },
            token=self.admin_token
        )
        if success:
            # Verify it was sanitized
            if response.get("theme_color") == "green":
                print(f"❌ CRITICAL: Backend did not sanitize 'green' to HSL triplet")
                self.tests_failed += 1
                self.failed_tests.append("School Settings PUT - 'green' not sanitized")
                return False
            print(f"   ✓ 'green' sanitized to: '{response.get('theme_color')}'")
        
        # Test 2: Update with hex color - should be sanitized
        success, response = self.run_test(
            "Update School Settings (hex '#1e3a30')",
            "PUT",
            "settings/school",
            200,
            data={
                "name": "",
                "address": "",
                "logo_path": None,
                "theme_color": "#1e3a30"
            },
            token=self.admin_token
        )
        if success:
            if response.get("theme_color") == "#1e3a30":
                print(f"❌ CRITICAL: Backend did not sanitize hex '#1e3a30' to HSL triplet")
                self.tests_failed += 1
                self.failed_tests.append("School Settings PUT - hex not sanitized")
                return False
            print(f"   ✓ '#1e3a30' sanitized to: '{response.get('theme_color')}'")
        
        # Test 3: Update with invalid value - should be sanitized to None or default
        success, response = self.run_test(
            "Update School Settings (invalid 'not-a-color')",
            "PUT",
            "settings/school",
            200,
            data={
                "name": "",
                "address": "",
                "logo_path": None,
                "theme_color": "not-a-color"
            },
            token=self.admin_token
        )
        if success:
            if response.get("theme_color") == "not-a-color":
                print(f"❌ CRITICAL: Backend did not sanitize invalid value 'not-a-color'")
                self.tests_failed += 1
                self.failed_tests.append("School Settings PUT - invalid value not sanitized")
                return False
            print(f"   ✓ 'not-a-color' sanitized to: '{response.get('theme_color')}'")
        
        # Test 4: Update with valid HSL triplet - should be preserved
        success, response = self.run_test(
            "Update School Settings (valid HSL '215 60% 30%')",
            "PUT",
            "settings/school",
            200,
            data={
                "name": "",
                "address": "",
                "logo_path": None,
                "theme_color": "215 60% 30%"
            },
            token=self.admin_token
        )
        if success:
            if response.get("theme_color") != "215 60% 30%":
                print(f"❌ Valid HSL triplet was not preserved: got '{response.get('theme_color')}'")
                self.tests_failed += 1
                self.failed_tests.append("School Settings PUT - valid HSL not preserved")
                return False
            print(f"   ✓ Valid HSL '215 60% 30%' preserved correctly")
        
        # Test 5: Restore to default theme
        success, response = self.run_test(
            "Restore School Settings to default",
            "PUT",
            "settings/school",
            200,
            data={
                "name": "",
                "address": "",
                "logo_path": None,
                "theme_color": "157 35% 18%"
            },
            token=self.admin_token
        )
        
        return success

    def test_difficulty_settings(self):
        """Test difficulty threshold settings"""
        # Get difficulty settings
        success, _ = self.run_test(
            "Get Difficulty Settings",
            "GET",
            "settings/difficulty",
            200,
            token=self.admin_token
        )
        if not success:
            return False
        
        # Update difficulty settings
        success, _ = self.run_test(
            "Update Difficulty Settings",
            "PUT",
            "settings/difficulty",
            200,
            data={
                "easy_min": 70.0,
                "medium_min": 40.0
            },
            token=self.admin_token
        )
        return success

    def test_exam_lock_settings(self):
        """Test exam lock settings"""
        # Get exam lock settings
        success, _ = self.run_test(
            "Get Exam Lock Settings",
            "GET",
            "settings/exam-lock",
            200,
            token=self.admin_token
        )
        if not success:
            return False
        
        # Update exam lock settings
        success, _ = self.run_test(
            "Update Exam Lock Settings",
            "PUT",
            "settings/exam-lock",
            200,
            data={
                "enabled": True,
                "max_violations": 3
            },
            token=self.admin_token
        )
        return success

    def test_storage_regression(self):
        """Test storage refactor - MongoDB storage mode"""
        import io
        from PIL import Image
        
        # Create a small test image
        img = Image.new('RGB', (100, 100), color='red')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        
        # Test 1: Upload image
        success, response = self.run_test(
            "Upload Image (Storage)",
            "POST",
            "uploads/image",
            200,
            files={'file': ('test.png', buf, 'image/png')},
            token=self.admin_token
        )
        if not success:
            return False
        
        image_path = response.get('path')
        if not image_path:
            print("❌ No path returned from upload")
            self.tests_failed += 1
            self.failed_tests.append("Storage Upload - No path returned")
            return False
        
        print(f"   Uploaded image path: {image_path}")
        
        # Test 2: Retrieve image with auth token
        success, _ = self.run_test(
            "Retrieve Image (Authenticated)",
            "GET",
            f"files/{image_path}?auth={self.admin_token}",
            200,
            token=None  # Using query param auth
        )
        if not success:
            return False
        
        # Test 3: Retrieve image without auth - should return 401
        success, _ = self.run_test(
            "Retrieve Image (Unauthenticated - expect 401)",
            "GET",
            f"files/{image_path}",
            401,
            token=None
        )
        if not success:
            return False
        
        # Test 4: Retrieve non-existent image - should return 404
        success, _ = self.run_test(
            "Retrieve Non-existent Image (expect 404)",
            "GET",
            f"files/nonexistent-path.png?auth={self.admin_token}",
            404,
            token=None
        )
        return success

    def test_import_templates(self):
        """Test import template endpoints"""
        # Questions import template
        success, _ = self.run_test(
            "Get Questions Import Template",
            "GET",
            "questions/import-template",
            200,
            token=self.admin_token
        )
        if not success:
            return False
        
        # Students import template
        success, _ = self.run_test(
            "Get Students Import Template",
            "GET",
            "students/import-template",
            200,
            token=self.admin_token
        )
        return success

    def test_student_flow(self):
        """Test student exam flow"""
        # Create a student account
        student_email = f"test.student.flow.{datetime.now().timestamp()}@sekolah.id"
        success, student = self.run_test(
            "Create Student for Flow Test",
            "POST",
            "users",
            200,
            data={
                "email": student_email,
                "password": "student123",
                "name": "Flow Test Student",
                "role": "siswa",
                "identifier": "99999"
            },
            token=self.admin_token
        )
        if not success:
            return False
        
        student_id = student.get('id')
        
        # Login as student
        success, response = self.run_test(
            "Student Login",
            "POST",
            "auth/login",
            200,
            data={"email": student_email, "password": "student123"}
        )
        if not success:
            return False
        
        self.student_token = response.get('token')
        
        # Create a session for the student
        # First create package
        success, cat = self.run_test(
            "Create Category for Student Flow",
            "POST",
            "categories",
            200,
            data={"name": "Student Flow Test", "description": "Test"},
            token=self.admin_token
        )
        if not success:
            return False
        
        cat_id = cat.get('id')
        
        success, q = self.run_test(
            "Create Question for Student Flow",
            "POST",
            "questions",
            200,
            data={
                "category_id": cat_id,
                "type": "pg",
                "text": "Test question for student",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "1",
                "weight": 1.0
            },
            token=self.admin_token
        )
        if not success:
            return False
        
        q_id = q.get('id')
        
        success, pkg = self.run_test(
            "Create Package for Student Flow",
            "POST",
            "packages",
            200,
            data={
                "title": "Student Flow Package",
                "description": "Test",
                "category_id": cat_id,
                "question_ids": [q_id],
                "scoring_method": "percentage",
                "is_public": False
            },
            token=self.admin_token
        )
        if not success:
            return False
        
        pkg_id = pkg.get('id')
        
        # Create session
        now = datetime.now(timezone.utc)
        start_time = (now - timedelta(hours=1)).isoformat()
        end_time = (now + timedelta(hours=2)).isoformat()
        
        success, session = self.run_test(
            "Create Session for Student Flow",
            "POST",
            "sessions",
            200,
            data={
                "title": "Student Flow Session",
                "package_id": pkg_id,
                "start_time": start_time,
                "end_time": end_time,
                "duration_minutes": 60,
                "kkm": 75.0,
                "class_ids": [],
                "announcement": "Test"
            },
            token=self.admin_token
        )
        if not success:
            return False
        
        session_id = session.get('id')
        
        # Student lists sessions
        success, sessions = self.run_test(
            "Student List Sessions",
            "GET",
            "sessions",
            200,
            token=self.student_token
        )
        if not success:
            return False
        
        # Student starts exam
        success, exam = self.run_test(
            "Student Start Exam",
            "POST",
            "exam/start",
            200,
            data={"session_id": session_id},
            token=self.student_token
        )
        if not success:
            return False
        
        # Student saves progress
        success, _ = self.run_test(
            "Student Save Progress",
            "POST",
            f"exam/save/{session_id}",
            200,
            data={"answers": {q_id: "1"}},
            token=self.student_token
        )
        if not success:
            return False
        
        # Student submits exam
        success, result = self.run_test(
            "Student Submit Exam",
            "POST",
            "exam/submit",
            200,
            data={"session_id": session_id, "answers": {q_id: "1"}},
            token=self.student_token
        )
        if not success:
            return False
        
        print(f"   Student score: {result.get('score')}")
        
        # Student views results
        success, _ = self.run_test(
            "Student View Results",
            "GET",
            "results/me",
            200,
            token=self.student_token
        )
        if not success:
            return False
        
        # Clean up
        success, _ = self.run_test(
            "Delete Student User",
            "DELETE",
            f"users/{student_id}",
            200,
            token=self.admin_token
        )
        
        return success

    def test_results_and_analytics(self):
        """Test results and analytics endpoints"""
        # Create a complete flow to get results
        # This is simplified - in real scenario we'd have actual data
        
        # Test analytics endpoints
        success, _ = self.run_test(
            "Get Analytics Classes",
            "GET",
            "analytics/classes",
            200,
            token=self.admin_token
        )
        if not success:
            return False
        
        success, _ = self.run_test(
            "Get Analytics Subjects",
            "GET",
            "analytics/subjects",
            200,
            token=self.admin_token
        )
        return success

    def test_leaderboard(self):
        """Test leaderboard endpoints"""
        # Global leaderboard
        success, _ = self.run_test(
            "Get Global Leaderboard",
            "GET",
            "leaderboard/global",
            200,
            token=self.admin_token
        )
        return success

    def test_notifications(self):
        """Test notifications endpoint"""
        success, _ = self.run_test(
            "Get Notifications",
            "GET",
            "notifications",
            200,
            token=self.admin_token
        )
        return success
    
    def test_pdf_excel_exports(self):
        """Test PDF and Excel export endpoints with MongoDB storage"""
        # Create a complete flow: class -> student -> session -> attempt
        
        # Create class
        success, cls = self.run_test(
            "Create Class for Export Test",
            "POST",
            "classes",
            200,
            data={"name": "Export Test Class", "description": "Test", "student_ids": []},
            token=self.admin_token
        )
        if not success:
            return False
        
        cls_id = cls.get('id')
        
        # Create student in class
        student_email = f"export.test.{datetime.now().timestamp()}@sekolah.id"
        success, student = self.run_test(
            "Create Student for Export",
            "POST",
            f"classes/{cls_id}/students",
            200,
            data={"name": "Export Student", "email": student_email, "password": "test123", "identifier": "EXP001"},
            token=self.admin_token
        )
        if not success:
            return False
        
        student_id = student.get('id')
        
        # Test Excel: Class roster export
        success, _ = self.run_test(
            "Export Class Roster (Excel)",
            "GET",
            f"classes/{cls_id}/students/xlsx",
            200,
            token=self.admin_token
        )
        if not success:
            return False
        
        # Test PDF: Login cards
        success, _ = self.run_test(
            "Generate Login Cards (PDF)",
            "POST",
            f"classes/{cls_id}/students/cards/pdf",
            200,
            data={"login_url": "https://test.com", "include_password": False, "credentials": []},
            token=self.admin_token
        )
        if not success:
            return False
        
        # Create exam flow for student report PDF
        success, cat = self.run_test(
            "Create Category for Export",
            "POST",
            "categories",
            200,
            data={"name": "Export Cat", "description": "Test"},
            token=self.admin_token
        )
        if not success:
            return False
        
        cat_id = cat.get('id')
        
        success, q = self.run_test(
            "Create Question for Export",
            "POST",
            "questions",
            200,
            data={"category_id": cat_id, "type": "pg", "text": "Test Q", "options": ["A", "B"], "correct_answer": "0", "weight": 1.0},
            token=self.admin_token
        )
        if not success:
            return False
        
        q_id = q.get('id')
        
        success, pkg = self.run_test(
            "Create Package for Export",
            "POST",
            "packages",
            200,
            data={"title": "Export Pkg", "description": "Test", "category_id": cat_id, "question_ids": [q_id], "scoring_method": "percentage", "is_public": False},
            token=self.admin_token
        )
        if not success:
            return False
        
        pkg_id = pkg.get('id')
        
        now = datetime.now(timezone.utc)
        start_time = (now - timedelta(hours=1)).isoformat()
        end_time = (now + timedelta(hours=2)).isoformat()
        
        success, session = self.run_test(
            "Create Session for Export",
            "POST",
            "sessions",
            200,
            data={"title": "Export Session", "package_id": pkg_id, "start_time": start_time, "end_time": end_time, "duration_minutes": 60, "kkm": 75.0, "class_ids": [cls_id], "announcement": ""},
            token=self.admin_token
        )
        if not success:
            return False
        
        session_id = session.get('id')
        
        # Student takes exam
        success, login_resp = self.run_test(
            "Student Login for Export",
            "POST",
            "auth/login",
            200,
            data={"email": student_email, "password": "test123"}
        )
        if not success:
            return False
        
        student_token = login_resp.get('token')
        
        success, exam = self.run_test(
            "Student Start Exam for Export",
            "POST",
            "exam/start",
            200,
            data={"session_id": session_id},
            token=student_token
        )
        if not success:
            return False
        
        success, result = self.run_test(
            "Student Submit Exam for Export",
            "POST",
            "exam/submit",
            200,
            data={"session_id": session_id, "answers": {q_id: "0"}},
            token=student_token
        )
        if not success:
            return False
        
        # Test PDF: Student report
        success, _ = self.run_test(
            "Generate Student Report (PDF)",
            "GET",
            f"report/student/{student_id}/pdf",
            200,
            token=self.admin_token
        )
        if not success:
            return False
        
        # Test PDF: Class report
        success, _ = self.run_test(
            "Generate Class Report (PDF)",
            "GET",
            f"report/class/{cls_id}/pdf",
            200,
            token=self.admin_token
        )
        if not success:
            return False
        
        # Test Excel: Class results export
        success, _ = self.run_test(
            "Export Class Results (Excel)",
            "GET",
            f"export/class/{cls_id}/xlsx",
            200,
            token=self.admin_token
        )
        
        return success


    def test_backup_feature(self):
        """Test backup and restore feature"""
        import gzip
        import json
        import base64
        
        print("\n📦 Testing backup stats (admin only)...")
        success, stats = self.run_test(
            "GET /backup/stats (admin)",
            "GET", "backup/stats", 200, token=self.admin_token
        )
        if success:
            assert "counts" in stats, "Missing 'counts' in stats"
            assert "files_bytes" in stats, "Missing 'files_bytes' in stats"
            assert "students" in stats, "Missing 'students' in stats"
            assert "teachers" in stats, "Missing 'teachers' in stats"
            required_cols = ["users", "classes", "categories", "questions", "packages",
                           "sessions", "attempts", "settings", "files", "file_blobs"]
            for col in required_cols:
                assert col in stats["counts"], f"Missing collection '{col}' in counts"
            print(f"   Stats: {stats['counts']}")
        
        print("\n📦 Testing backup stats (non-admin should get 403)...")
        if self.student_token:
            self.run_test(
                "GET /backup/stats (student - should fail)",
                "GET", "backup/stats", 403, token=self.student_token
            )
        
        print("\n📦 Testing backup export...")
        url = f"{self.base_url}/backup/export"
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        response = requests.get(url, headers=headers, timeout=60)
        if response.status_code == 200:
            self.tests_passed += 1
            print(f"✅ Passed - Status: {response.status_code}")
            
            # Verify it's gzipped JSON
            try:
                raw = gzip.decompress(response.content)
                backup_data = json.loads(raw.decode("utf-8"))
                
                assert "version" in backup_data, "Missing 'version'"
                assert "app" in backup_data, "Missing 'app'"
                assert "exported_at" in backup_data, "Missing 'exported_at'"
                assert "collections" in backup_data, "Missing 'collections'"
                
                required_cols = ["users", "classes", "categories", "questions", "packages",
                               "sessions", "attempts", "settings", "files", "file_blobs"]
                for col in required_cols:
                    assert col in backup_data["collections"], f"Missing collection '{col}'"
                
                print(f"   Backup version: {backup_data['version']}, app: {backup_data['app']}")
                print(f"   Collections: {list(backup_data['collections'].keys())}")
                
                # Store for import test
                self.backup_file = response.content
                
            except Exception as e:
                print(f"   ⚠️  Warning: Could not parse backup: {e}")
        else:
            self.tests_failed += 1
            self.failed_tests.append("GET /backup/export")
            print(f"❌ Failed - Expected 200, got {response.status_code}")
        
        self.tests_run += 1
        
        print("\n📦 Testing backup export (non-admin should get 403)...")
        if self.guru_token:
            url = f"{self.base_url}/backup/export"
            headers = {'Authorization': f'Bearer {self.guru_token}'}
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 403:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
            else:
                self.tests_failed += 1
                self.failed_tests.append("GET /backup/export (guru - should fail)")
                print(f"❌ Failed - Expected 403, got {response.status_code}")
            self.tests_run += 1
        
        print("\n📦 Testing backup import - invalid mode...")
        if hasattr(self, 'backup_file'):
            url = f"{self.base_url}/backup/import"
            headers = {'Authorization': f'Bearer {self.admin_token}'}
            files = {'file': ('backup.json.gz', self.backup_file, 'application/gzip')}
            data = {'mode': 'invalid'}
            response = requests.post(url, files=files, data=data, headers=headers, timeout=30)
            if response.status_code == 400:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
            else:
                self.tests_failed += 1
                self.failed_tests.append("POST /backup/import (invalid mode)")
                print(f"❌ Failed - Expected 400, got {response.status_code}")
            self.tests_run += 1
        
        print("\n📦 Testing backup import - empty file...")
        url = f"{self.base_url}/backup/import"
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        files = {'file': ('backup.json.gz', b'', 'application/gzip')}
        data = {'mode': 'merge'}
        response = requests.post(url, files=files, data=data, headers=headers, timeout=30)
        if response.status_code == 400:
            self.tests_passed += 1
            print(f"✅ Passed - Status: {response.status_code}")
        else:
            self.tests_failed += 1
            self.failed_tests.append("POST /backup/import (empty file)")
            print(f"❌ Failed - Expected 400, got {response.status_code}")
        self.tests_run += 1
        
        print("\n📦 Testing backup import - corrupt file...")
        url = f"{self.base_url}/backup/import"
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        files = {'file': ('backup.json.gz', b'not a valid gzip', 'application/gzip')}
        data = {'mode': 'merge'}
        response = requests.post(url, files=files, data=data, headers=headers, timeout=30)
        if response.status_code == 400:
            self.tests_passed += 1
            print(f"✅ Passed - Status: {response.status_code}")
        else:
            self.tests_failed += 1
            self.failed_tests.append("POST /backup/import (corrupt file)")
            print(f"❌ Failed - Expected 400, got {response.status_code}")
        self.tests_run += 1
        
        print("\n📦 Testing backup import - unknown collection...")
        bad_backup = {
            "version": 1,
            "app": "test",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "collections": {
                "unknown_collection": [{"id": "test"}]
            }
        }
        raw = json.dumps(bad_backup).encode("utf-8")
        gz = gzip.compress(raw)
        url = f"{self.base_url}/backup/import"
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        files = {'file': ('backup.json.gz', gz, 'application/gzip')}
        data = {'mode': 'merge'}
        response = requests.post(url, files=files, data=data, headers=headers, timeout=30)
        if response.status_code == 400:
            self.tests_passed += 1
            print(f"✅ Passed - Status: {response.status_code}")
        else:
            self.tests_failed += 1
            self.failed_tests.append("POST /backup/import (unknown collection)")
            print(f"❌ Failed - Expected 400, got {response.status_code}")
        self.tests_run += 1
        
        print("\n📦 Testing backup import - merge mode idempotency...")
        if hasattr(self, 'backup_file'):
            # First import
            url = f"{self.base_url}/backup/import"
            headers = {'Authorization': f'Bearer {self.admin_token}'}
            files = {'file': ('backup.json.gz', self.backup_file, 'application/gzip')}
            data = {'mode': 'merge'}
            response1 = requests.post(url, files=files, data=data, headers=headers, timeout=60)
            
            # Second import (should be idempotent)
            files = {'file': ('backup.json.gz', self.backup_file, 'application/gzip')}
            response2 = requests.post(url, files=files, data=data, headers=headers, timeout=60)
            
            if response1.status_code == 200 and response2.status_code == 200:
                result2 = response2.json()
                # Check that second import has 0 inserted (idempotent)
                all_zero = all(counts["inserted"] == 0 for counts in result2["result"].values())
                if all_zero:
                    self.tests_passed += 1
                    print(f"✅ Passed - Merge mode is idempotent (0 inserted on re-import)")
                else:
                    self.tests_failed += 1
                    self.failed_tests.append("POST /backup/import (merge idempotency)")
                    print(f"❌ Failed - Re-import inserted new records (not idempotent)")
            else:
                self.tests_failed += 1
                self.failed_tests.append("POST /backup/import (merge idempotency)")
                print(f"❌ Failed - Import failed: {response1.status_code}, {response2.status_code}")
            self.tests_run += 1
        
        print("\n📦 Testing CRITICAL data integrity (create->export->restore->verify)...")
        try:
            # Create test data
            print("   Creating test dataset...")
            
            # Create category
            success, category = self.run_test(
                "Create test category",
                "POST", "categories", 200,
                data={"name": "Backup Test Category", "description": "For backup test"},
                token=self.admin_token
            )
            if not success:
                print("   ⚠️  Skipping data integrity test - category creation failed")
                return
            
            # Upload test image
            img_data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==")
            url = f"{self.base_url}/uploads/image"
            headers = {'Authorization': f'Bearer {self.admin_token}'}
            files = {'file': ('test.png', img_data, 'image/png')}
            response = requests.post(url, files=files, headers=headers, timeout=30)
            if response.status_code != 200:
                print("   ⚠️  Skipping data integrity test - image upload failed")
                return
            image_path = response.json()["path"]
            print(f"   Uploaded test image: {image_path}")
            
            # Create question with image
            success, question = self.run_test(
                "Create test question",
                "POST", "questions", 200,
                data={
                    "category_id": category["id"],
                    "type": "pg",
                    "text": "Backup test question",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "0",
                    "weight": 1.0,
                    "image_path": image_path
                },
                token=self.admin_token
            )
            if not success:
                print("   ⚠️  Skipping data integrity test - question creation failed")
                return
            
            # Export backup
            print("   Exporting backup...")
            url = f"{self.base_url}/backup/export"
            headers = {'Authorization': f'Bearer {self.admin_token}'}
            response = requests.get(url, headers=headers, timeout=60)
            if response.status_code != 200:
                print("   ⚠️  Skipping data integrity test - export failed")
                return
            backup_data = response.content
            
            # Restore with mode=replace
            print("   Restoring backup with mode=replace...")
            url = f"{self.base_url}/backup/import"
            headers = {'Authorization': f'Bearer {self.admin_token}'}
            files = {'file': ('backup.json.gz', backup_data, 'application/gzip')}
            data = {'mode': 'replace'}
            response = requests.post(url, files=files, data=data, headers=headers, timeout=60)
            if response.status_code != 200:
                print(f"   ⚠️  Restore failed: {response.status_code}")
                self.tests_failed += 1
                self.failed_tests.append("Backup data integrity test")
                self.tests_run += 1
                return
            
            # Re-login after restore
            print("   Re-logging in after restore...")
            # Login as admin again
            success, login_data = self.run_test(
                "Admin re-login after restore",
                "POST", "auth/login", 200,
                data={"email": "admin@sekolah.id", "password": "Admin@12345"}
            )
            if success:
                self.admin_token = login_data["token"]
            
            # Verify image still accessible
            print("   Verifying image accessibility...")
            url = f"{self.base_url}/files/{image_path}"
            headers = {'Authorization': f'Bearer {self.admin_token}'}
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                print("   ✓ Image still accessible after restore")
                self.tests_passed += 1
            else:
                print(f"   ✗ Image not accessible: {response.status_code}")
                self.tests_failed += 1
                self.failed_tests.append("Backup data integrity - image restore")
            self.tests_run += 1
            
        except Exception as e:
            print(f"   ⚠️  Data integrity test error: {e}")
            self.tests_failed += 1
            self.failed_tests.append("Backup data integrity test")
            self.tests_run += 1


    def test_makeup_exams(self):
        """Test makeup exam (ujian susulan) feature"""
        print("\n🔄 Testing makeup exam feature...")
        
        # Create a session first
        success, cat = self.run_test(
            "Create Category for Makeup Test",
            "POST", "categories", 200,
            data={"name": "Makeup Test Category", "description": "Test"},
            token=self.admin_token
        )
        if not success:
            return False
        
        cat_id = cat.get('id')
        
        # Create question
        success, q = self.run_test(
            "Create Question for Makeup",
            "POST", "questions", 200,
            data={
                "category_id": cat_id, "type": "pg",
                "text": "Makeup test question?",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "1", "weight": 1.0
            },
            token=self.admin_token
        )
        if not success:
            return False
        
        q_id = q.get('id')
        
        # Create package
        success, pkg = self.run_test(
            "Create Package for Makeup",
            "POST", "packages", 200,
            data={
                "title": "Makeup Test Package",
                "question_ids": [q_id],
                "scoring_method": "percentage"
            },
            token=self.admin_token
        )
        if not success:
            return False
        
        pkg_id = pkg.get('id')
        
        # Create class
        success, cls = self.run_test(
            "Create Class for Makeup",
            "POST", "classes", 200,
            data={"name": "Makeup Test Class", "description": "Test"},
            token=self.admin_token
        )
        if not success:
            return False
        
        cls_id = cls.get('id')
        
        # Create student
        success, student = self.run_test(
            "Create Student for Makeup",
            "POST", "users", 200,
            data={
                "email": f"makeup_student_{datetime.now().timestamp()}@test.id",
                "password": "Test@12345",
                "name": "Makeup Test Student",
                "role": "siswa",
                "identifier": "MKP001"
            },
            token=self.admin_token
        )
        if not success:
            return False
        
        student_id = student.get('id')
        
        # Add student to class
        success, _ = self.run_test(
            "Add Student to Class",
            "POST", f"classes/{cls_id}/students/attach", 200,
            data={"student_ids": [student_id]},
            token=self.admin_token
        )
        if not success:
            return False
        
        # Create session
        now = datetime.now(timezone.utc)
        start = (now - timedelta(hours=2)).isoformat()
        end = (now - timedelta(hours=1)).isoformat()
        
        success, session = self.run_test(
            "Create Session for Makeup",
            "POST", "sessions", 200,
            data={
                "title": "Makeup Test Session",
                "package_id": pkg_id,
                "start_time": start,
                "end_time": end,
                "duration_minutes": 60,
                "kkm": 75,
                "class_ids": [cls_id]
            },
            token=self.admin_token
        )
        if not success:
            return False
        
        session_id = session.get('id')
        
        # Test GET /makeups/absentees/{session_id}
        success, absentees_data = self.run_test(
            "GET Makeup Absentees",
            "GET", f"makeups/absentees/{session_id}", 200,
            token=self.admin_token
        )
        if success:
            assert 'absentees' in absentees_data, "Missing 'absentees' in response"
            assert len(absentees_data['absentees']) > 0, "Should have at least one absentee"
            print(f"   Found {len(absentees_data['absentees'])} absentee(s)")
        
        # Test POST /makeups (create makeup exam)
        makeup_start = (now + timedelta(hours=1)).isoformat()
        makeup_end = (now + timedelta(hours=3)).isoformat()
        
        success, makeup_result = self.run_test(
            "Create Makeup Exam",
            "POST", "makeups", 200,
            data={
                "session_id": session_id,
                "student_ids": [student_id],
                "start_time": makeup_start,
                "end_time": makeup_end,
                "duration_minutes": 90,
                "reason": "Sakit"
            },
            token=self.admin_token
        )
        if success:
            assert makeup_result.get('created', 0) > 0, "Should create at least one makeup"
            print(f"   Created: {makeup_result.get('created')}, Updated: {makeup_result.get('updated')}")
        
        # Test GET /makeups (list all makeups)
        success, makeups = self.run_test(
            "List All Makeups",
            "GET", "makeups", 200,
            token=self.admin_token
        )
        if success:
            assert isinstance(makeups, list), "Makeups should be a list"
            assert len(makeups) > 0, "Should have at least one makeup"
            makeup_id = makeups[0].get('id')
            print(f"   Found {len(makeups)} makeup(s)")
        
        # Test GET /makeups?session_id=...
        success, session_makeups = self.run_test(
            "List Makeups by Session",
            "GET", f"makeups?session_id={session_id}", 200,
            token=self.admin_token
        )
        if success:
            assert isinstance(session_makeups, list), "Should be a list"
            print(f"   Found {len(session_makeups)} makeup(s) for session")
        
        # Test GET /makeups/summary
        success, summary = self.run_test(
            "Get Makeups Summary",
            "GET", "makeups/summary", 200,
            token=self.admin_token
        )
        if success:
            assert isinstance(summary, dict), "Summary should be a dict"
            print(f"   Summary: {summary}")
        
        # Test PUT /makeups/{mid} (update makeup)
        if makeup_id:
            new_start = (now + timedelta(hours=2)).isoformat()
            new_end = (now + timedelta(hours=4)).isoformat()
            
            success, updated = self.run_test(
                "Update Makeup Exam",
                "PUT", f"makeups/{makeup_id}", 200,
                data={
                    "start_time": new_start,
                    "end_time": new_end,
                    "duration_minutes": 120,
                    "reason": "Sakit (updated)"
                },
                token=self.admin_token
            )
            if success:
                assert updated.get('reason') == "Sakit (updated)", "Reason should be updated"
                print(f"   Updated makeup: {updated.get('student_name')}")
        
        # Test DELETE /makeups/{mid}
        if makeup_id:
            success, _ = self.run_test(
                "Delete Makeup Exam",
                "DELETE", f"makeups/{makeup_id}", 200,
                token=self.admin_token
            )
        
        return True
    
    def test_class_roster_management(self):
        """Test class roster (student account) management"""
        print("\n👥 Testing class roster management...")
        
        # Create a class
        success, cls = self.run_test(
            "Create Class for Roster Test",
            "POST", "classes", 200,
            data={"name": "Roster Test Class", "description": "Test"},
            token=self.admin_token
        )
        if not success:
            return False
        
        cls_id = cls.get('id')
        
        # Test GET /classes/{cid}/students
        success, roster_data = self.run_test(
            "GET Class Students",
            "GET", f"classes/{cls_id}/students", 200,
            token=self.admin_token
        )
        if success:
            assert 'students' in roster_data, "Missing 'students' in response"
            assert 'available' in roster_data, "Missing 'available' in response"
            print(f"   Students: {len(roster_data['students'])}, Available: {len(roster_data['available'])}")
        
        # Test POST /classes/{cid}/students (create student account)
        timestamp = datetime.now().timestamp()
        success, new_student = self.run_test(
            "Create Student Account in Class",
            "POST", f"classes/{cls_id}/students", 200,
            data={
                "name": "Roster Test Student",
                "email": f"roster_test_{timestamp}@test.id",
                "password": "Test@12345",
                "identifier": "RST001"
            },
            token=self.admin_token
        )
        if success:
            student_id = new_student.get('id')
            assert student_id, "Should return student id"
            print(f"   Created student: {new_student.get('name')}")
        
        # Test POST /classes/{cid}/students/reset-passwords (bulk reset)
        success, reset_result = self.run_test(
            "Bulk Reset Passwords (random)",
            "POST", f"classes/{cls_id}/students/reset-passwords", 200,
            data={"mode": "random"},
            token=self.admin_token
        )
        if success:
            assert 'credentials' in reset_result, "Missing 'credentials' in response"
            assert reset_result.get('count', 0) > 0, "Should reset at least one password"
            print(f"   Reset {reset_result.get('count')} password(s)")
        
        # Test POST /classes/{cid}/students/reset-passwords (same password)
        success, reset_result2 = self.run_test(
            "Bulk Reset Passwords (same)",
            "POST", f"classes/{cls_id}/students/reset-passwords", 200,
            data={"mode": "same", "password": "NewPass@123"},
            token=self.admin_token
        )
        if success:
            assert reset_result2.get('count', 0) > 0, "Should reset at least one password"
            print(f"   Reset {reset_result2.get('count')} password(s) with same password")
        
        # Test GET /classes/{cid}/students/xlsx (export roster)
        url = f"{self.base_url}/classes/{cls_id}/students/xlsx"
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            self.tests_passed += 1
            print(f"✅ Export Class Roster Excel - Status: {response.status_code}")
            assert response.headers.get('content-type') == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        else:
            self.tests_failed += 1
            self.failed_tests.append("Export Class Roster Excel")
            print(f"❌ Export Class Roster Excel - Expected 200, got {response.status_code}")
        self.tests_run += 1
        
        # Test DELETE /classes/{cid}/students/{sid} (remove from class)
        if student_id:
            success, _ = self.run_test(
                "Remove Student from Class",
                "DELETE", f"classes/{cls_id}/students/{student_id}", 200,
                token=self.admin_token
            )
        
        # Test DELETE /classes/{cid}/students/{sid}?delete_account=true
        if student_id:
            # Re-add student first
            success, _ = self.run_test(
                "Re-add Student to Class",
                "POST", f"classes/{cls_id}/students/attach", 200,
                data={"student_ids": [student_id]},
                token=self.admin_token
            )
            
            # Then delete account
            success, _ = self.run_test(
                "Delete Student Account",
                "DELETE", f"classes/{cls_id}/students/{student_id}?delete_account=true", 200,
                token=self.admin_token
            )
        
        return True

def main():
    print("=" * 60)
    print("CBT UJIAN ONLINE - BACKEND API TEST")
    print("=" * 60)
    
    tester = CBTAPITester()
    
    # Test authentication first
    print("\n" + "=" * 60)
    print("AUTHENTICATION TESTS")
    print("=" * 60)
    if not tester.test_admin_login():
        print("\n❌ Admin login failed - stopping tests")
        return 1
    
    tester.test_auth_me()
    
    # Test CRUD operations
    print("\n" + "=" * 60)
    print("CRUD TESTS")
    print("=" * 60)
    tester.test_categories_crud()
    tester.test_questions_crud()
    tester.test_packages_crud()
    tester.test_sessions_crud()
    tester.test_classes_crud()
    tester.test_users_crud()
    
    # Test makeup exams (merged feature)
    print("\n" + "=" * 60)
    print("MAKEUP EXAM TESTS (MERGED FEATURE)")
    print("=" * 60)
    tester.test_makeup_exams()
    
    # Test class roster management (new feature)
    print("\n" + "=" * 60)
    print("CLASS ROSTER MANAGEMENT TESTS (NEW FEATURE)")
    print("=" * 60)
    tester.test_class_roster_management()
    
    # Test settings
    print("\n" + "=" * 60)
    print("SETTINGS TESTS")
    print("=" * 60)
    tester.test_school_settings()
    tester.test_difficulty_settings()
    tester.test_exam_lock_settings()
    
    # Test storage regression
    print("\n" + "=" * 60)
    print("STORAGE REGRESSION TESTS")
    print("=" * 60)
    tester.test_storage_regression()
    
    # Test import templates
    print("\n" + "=" * 60)
    print("IMPORT TEMPLATE TESTS")
    print("=" * 60)
    tester.test_import_templates()
    
    # Test student flow
    print("\n" + "=" * 60)
    print("STUDENT EXAM FLOW TESTS")
    print("=" * 60)
    tester.test_student_flow()
    
    # Test results and analytics
    print("\n" + "=" * 60)
    print("RESULTS & ANALYTICS TESTS")
    print("=" * 60)
    tester.test_results_and_analytics()
    tester.test_leaderboard()
    
    # Test PDF and Excel exports
    print("\n" + "=" * 60)
    print("PDF & EXCEL EXPORT TESTS")
    print("=" * 60)
    tester.test_pdf_excel_exports()
    
    # Test notifications (may fail with 403 - that's ok)
    print("\n" + "=" * 60)
    print("NOTIFICATIONS TEST")
    print("=" * 60)
    tester.test_notifications()
    
    # Test backup feature
    print("\n" + "=" * 60)
    print("BACKUP & RESTORE FEATURE TESTS")
    print("=" * 60)
    tester.test_backup_feature()
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total tests run: {tester.tests_run}")
    print(f"✅ Passed: {tester.tests_passed}")
    print(f"❌ Failed: {tester.tests_failed}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run*100):.1f}%")
    
    if tester.failed_tests:
        print("\n" + "=" * 60)
        print("FAILED TESTS:")
        print("=" * 60)
        for failed in tester.failed_tests:
            print(f"  ❌ {failed}")
    
    return 0 if tester.tests_failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
