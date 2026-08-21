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
        """Test school settings"""
        # Get settings (should be public)
        success, settings = self.run_test(
            "Get School Settings (Public)",
            "GET",
            "settings/school",
            200
        )
        if not success:
            return False
        
        # Update settings (admin only)
        success, _ = self.run_test(
            "Update School Settings",
            "PUT",
            "settings/school",
            200,
            data={
                "name": "Test School",
                "address": "Test Address",
                "logo_path": None,
                "theme_color": "green"
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
    
    # Test settings
    print("\n" + "=" * 60)
    print("SETTINGS TESTS")
    print("=" * 60)
    tester.test_school_settings()
    tester.test_difficulty_settings()
    tester.test_exam_lock_settings()
    
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
    tester.test_notifications()
    
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
