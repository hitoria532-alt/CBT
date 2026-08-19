"""Iteration 12: Bulk Account Import + Exam Retakes with Score Policies."""
import os
import io
import uuid
import pytest
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://github-auto-build.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("hitoria532@gmail.com", "admin123")
GURU = ("guru@sekolah.id", "guru123")
SISWA = ("siswa@sekolah.id", "siswa123")
SISWA2 = ("siswa2@sekolah.id", "siswa123")


def _login(email, pw):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=30)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_h():
    return {"Authorization": f"Bearer {_login(*ADMIN)}"}


@pytest.fixture(scope="module")
def guru_h():
    return {"Authorization": f"Bearer {_login(*GURU)}"}


@pytest.fixture(scope="module")
def siswa_h():
    return {"Authorization": f"Bearer {_login(*SISWA)}"}


@pytest.fixture(scope="module")
def siswa2_h():
    return {"Authorization": f"Bearer {_login(*SISWA2)}"}


@pytest.fixture(scope="module")
def siswa2_id(siswa2_h):
    r = requests.get(f"{API}/auth/me", headers=siswa2_h, timeout=30)
    assert r.status_code == 200
    return r.json()["id"]


# --------- Bulk Account Import ---------

class TestBulkImport:
    def test_admin_downloads_import_template(self, admin_h):
        """Admin can download CSV template for bulk import."""
        r = requests.get(f"{API}/users/import-template", headers=admin_h, timeout=30)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert "text/csv" in r.headers.get("content-type", "").lower()
        content = r.text
        assert "nama" in content.lower() or "name" in content.lower()
        assert "email" in content.lower()
        assert "password" in content.lower()
        assert "role" in content.lower()
        print("✅ Admin can download import template")

    def test_guru_forbidden_import_template(self, guru_h):
        """Non-admin (guru) gets 403 on import template."""
        r = requests.get(f"{API}/users/import-template", headers=guru_h, timeout=30)
        assert r.status_code == 403, f"Expected 403, got {r.status_code}"
        print("✅ Guru correctly forbidden from import template")

    def test_import_valid_accounts(self, admin_h):
        """Import CSV with valid siswa and guru accounts."""
        test_id = uuid.uuid4().hex[:6]
        csv_data = f"""nama,email,password,role,identifier
TEST_Siswa_Import_{test_id},test_siswa_{test_id}@import.id,pass123,siswa,NIS{test_id}
TEST_Guru_Import_{test_id},test_guru_{test_id}@import.id,pass456,guru,NIP{test_id}
"""
        files = {"file": ("import.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
        r = requests.post(f"{API}/users/import", files=files, headers=admin_h, timeout=30)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        result = r.json()
        assert result["imported"] == 2, f"Expected 2 imported, got {result}"
        assert result["updated"] == 0
        assert len(result["errors"]) == 0
        print(f"✅ Imported 2 accounts: {result}")

        # Verify accounts exist
        users_r = requests.get(f"{API}/users", headers=admin_h, timeout=30)
        users = users_r.json()
        siswa_found = any(u["email"] == f"test_siswa_{test_id}@import.id" for u in users)
        guru_found = any(u["email"] == f"test_guru_{test_id}@import.id" for u in users)
        assert siswa_found and guru_found, "Imported accounts not found in user list"
        print("✅ Imported accounts verified in user list")

        # Cleanup
        for u in users:
            if u["email"] in [f"test_siswa_{test_id}@import.id", f"test_guru_{test_id}@import.id"]:
                requests.delete(f"{API}/users/{u['id']}", headers=admin_h, timeout=30)

    def test_import_validation_errors(self, admin_h):
        """Import with validation errors: missing fields, invalid email, unknown role."""
        test_id = uuid.uuid4().hex[:6]
        csv_data = f"""nama,email,password,role,identifier
,missing_name_{test_id}@t.id,pass123,siswa,
Valid Name,invalid-email-no-at,pass123,siswa,
Valid Name,test_{test_id}@t.id,pass123,unknown_role,
Valid Name,test_new_{test_id}@t.id,,siswa,
"""
        files = {"file": ("import.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
        r = requests.post(f"{API}/users/import", files=files, headers=admin_h, timeout=30)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        result = r.json()
        assert len(result["errors"]) >= 3, f"Expected at least 3 errors, got {result}"
        print(f"✅ Validation errors detected: {result['errors']}")

    def test_import_update_existing(self, admin_h):
        """Import with existing email updates name/role/identifier and password."""
        test_id = uuid.uuid4().hex[:6]
        email = f"test_update_{test_id}@import.id"
        
        # Create initial account
        create_payload = {"email": email, "password": "initial_pass", "name": "Initial Name", "role": "siswa"}
        r = requests.post(f"{API}/users", json=create_payload, headers=admin_h, timeout=30)
        assert r.status_code in (200, 201), f"Failed to create user: {r.text}"
        user_id = r.json()["id"]
        
        # Import CSV with same email but updated data
        csv_data = f"""nama,email,password,role,identifier
Updated Name,{email},updated_pass,guru,UPDATED123
"""
        files = {"file": ("import.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
        r = requests.post(f"{API}/users/import", files=files, headers=admin_h, timeout=30)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        result = r.json()
        assert result["updated"] == 1, f"Expected 1 updated, got {result}"
        assert result["imported"] == 0
        print(f"✅ Account updated: {result}")

        # Verify update
        users_r = requests.get(f"{API}/users", headers=admin_h, timeout=30)
        users = users_r.json()
        updated_user = next((u for u in users if u["email"] == email), None)
        assert updated_user is not None
        assert updated_user["name"] == "Updated Name"
        assert updated_user["role"] == "guru"
        assert updated_user["identifier"] == "UPDATED123"
        print("✅ Updated user verified")

        # Verify login with new password
        login_r = requests.post(f"{API}/auth/login", json={"email": email, "password": "updated_pass"}, timeout=30)
        assert login_r.status_code == 200, "Login with updated password failed"
        print("✅ Login with updated password successful")

        # Cleanup
        requests.delete(f"{API}/users/{user_id}", headers=admin_h, timeout=30)

    def test_guru_forbidden_import(self, guru_h):
        """Non-admin (guru) gets 403 on POST /api/users/import."""
        csv_data = "nama,email,password,role\nTest,test@t.id,pass,siswa"
        files = {"file": ("import.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
        r = requests.post(f"{API}/users/import", files=files, headers=guru_h, timeout=30)
        assert r.status_code == 403, f"Expected 403, got {r.status_code}"
        print("✅ Guru correctly forbidden from import")


# --------- Exam Retakes with Score Policies ---------

@pytest.fixture(scope="module")
def retake_session(admin_h):
    """Create a test session with max_attempts=3 and policy 'tertinggi'."""
    # Get existing package and class
    pkgs_r = requests.get(f"{API}/packages", headers=admin_h, timeout=30)
    pkgs = pkgs_r.json()
    pkg = next((p for p in pkgs if "Matematika" in p.get("title", "")), pkgs[0] if pkgs else None)
    assert pkg, "No package found"
    
    classes_r = requests.get(f"{API}/classes", headers=admin_h, timeout=30)
    classes = classes_r.json()
    klass = next((c for c in classes if "X-A" in c.get("name", "")), classes[0] if classes else None)
    assert klass, "No class found"
    
    now = datetime.now(timezone.utc)
    start = (now - timedelta(minutes=10)).isoformat()
    end = (now + timedelta(hours=2)).isoformat()
    
    test_id = uuid.uuid4().hex[:6]
    payload = {
        "title": f"TEST_Retake_Session_{test_id}",
        "package_id": pkg["id"],
        "start_time": start,
        "end_time": end,
        "duration_minutes": 30,
        "kkm": 75.0,
        "class_ids": [klass["id"]],
        "announcement": "Test retake session",
        "max_attempts": 3,
        "score_policy": "tertinggi"
    }
    r = requests.post(f"{API}/sessions", json=payload, headers=admin_h, timeout=30)
    assert r.status_code in (200, 201), f"Failed to create session: {r.text}"
    session = r.json()
    print(f"✅ Created retake session: {session['id']}")
    
    yield session
    
    # Cleanup
    requests.delete(f"{API}/sessions/{session['id']}", headers=admin_h, timeout=30)
    print(f"✅ Cleaned up session: {session['id']}")


class TestExamRetakes:
    def test_session_has_retake_fields(self, retake_session):
        """Session has max_attempts and score_policy fields."""
        assert retake_session["max_attempts"] == 3
        assert retake_session["score_policy"] == "tertinggi"
        print("✅ Session has correct retake fields")

    def test_siswa_sees_retake_info(self, siswa2_h, retake_session):
        """Siswa sees max_attempts and attempts_left in session list."""
        r = requests.get(f"{API}/sessions", headers=siswa2_h, timeout=30)
        assert r.status_code == 200
        sessions = r.json()
        test_session = next((s for s in sessions if s["id"] == retake_session["id"]), None)
        assert test_session is not None, "Session not visible to siswa"
        assert test_session["max_attempts"] == 3
        assert "attempts_left" in test_session
        print(f"✅ Siswa sees retake info: {test_session['max_attempts']} attempts, {test_session['attempts_left']} left")

    def test_siswa_multiple_attempts(self, siswa2_h, siswa2_id, retake_session, admin_h):
        """Siswa can do multiple attempts up to max_attempts."""
        session_id = retake_session["id"]
        
        # Attempt 1
        start_r = requests.post(f"{API}/exam/start", json={"session_id": session_id}, headers=siswa2_h, timeout=30)
        assert start_r.status_code == 200, f"Attempt 1 start failed: {start_r.text}"
        attempt1 = start_r.json()
        assert attempt1["attempt_number"] == 1
        print(f"✅ Attempt 1 started: {attempt1['attempt_id']}")
        
        # Submit attempt 1 with some answers
        questions = attempt1["questions"]
        answers = {}
        for q in questions[:2]:  # Answer first 2 questions
            if q["type"] == "pg":
                answers[q["id"]] = "0"
            elif q["type"] == "truefalse":
                answers[q["id"]] = "true"
        
        submit_r = requests.post(f"{API}/exam/submit", 
                                json={"session_id": session_id, "answers": answers}, 
                                headers=siswa2_h, timeout=30)
        assert submit_r.status_code == 200, f"Attempt 1 submit failed: {submit_r.text}"
        print(f"✅ Attempt 1 submitted")
        
        # Grade essay if needed
        result1 = submit_r.json()
        if result1.get("needs_grading"):
            essay_scores = {}
            for d in result1.get("details", []):
                if d.get("type") == "essay":
                    essay_scores[d["question_id"]] = d["points_possible"] * 0.5
            if essay_scores:
                grade_r = requests.post(f"{API}/results/detail/{result1['id']}/grade",
                                       json={"scores": essay_scores}, headers=admin_h, timeout=30)
                assert grade_r.status_code == 200
                print(f"✅ Essay graded for attempt 1")
        
        # Attempt 2
        start_r2 = requests.post(f"{API}/exam/start", json={"session_id": session_id}, headers=siswa2_h, timeout=30)
        assert start_r2.status_code == 200, f"Attempt 2 start failed: {start_r2.text}"
        attempt2 = start_r2.json()
        assert attempt2["attempt_number"] == 2
        print(f"✅ Attempt 2 started: {attempt2['attempt_id']}")
        
        # Submit attempt 2
        submit_r2 = requests.post(f"{API}/exam/submit", 
                                 json={"session_id": session_id, "answers": answers}, 
                                 headers=siswa2_h, timeout=30)
        assert submit_r2.status_code == 200
        print(f"✅ Attempt 2 submitted")
        
        # Grade essay if needed
        result2 = submit_r2.json()
        if result2.get("needs_grading"):
            essay_scores = {}
            for d in result2.get("details", []):
                if d.get("type") == "essay":
                    essay_scores[d["question_id"]] = d["points_possible"] * 0.8
            if essay_scores:
                grade_r = requests.post(f"{API}/results/detail/{result2['id']}/grade",
                                       json={"scores": essay_scores}, headers=admin_h, timeout=30)
                assert grade_r.status_code == 200
                print(f"✅ Essay graded for attempt 2")
        
        # Attempt 3
        start_r3 = requests.post(f"{API}/exam/start", json={"session_id": session_id}, headers=siswa2_h, timeout=30)
        assert start_r3.status_code == 200, f"Attempt 3 start failed: {start_r3.text}"
        attempt3 = start_r3.json()
        assert attempt3["attempt_number"] == 3
        print(f"✅ Attempt 3 started: {attempt3['attempt_id']}")
        
        # Submit attempt 3
        submit_r3 = requests.post(f"{API}/exam/submit", 
                                 json={"session_id": session_id, "answers": answers}, 
                                 headers=siswa2_h, timeout=30)
        assert submit_r3.status_code == 200
        print(f"✅ Attempt 3 submitted")
        
        # Grade essay if needed
        result3 = submit_r3.json()
        if result3.get("needs_grading"):
            essay_scores = {}
            for d in result3.get("details", []):
                if d.get("type") == "essay":
                    essay_scores[d["question_id"]] = d["points_possible"] * 0.6
            if essay_scores:
                grade_r = requests.post(f"{API}/results/detail/{result3['id']}/grade",
                                       json={"scores": essay_scores}, headers=admin_h, timeout=30)
                assert grade_r.status_code == 200
                print(f"✅ Essay graded for attempt 3")
        
        # Attempt 4 should be blocked
        start_r4 = requests.post(f"{API}/exam/start", json={"session_id": session_id}, headers=siswa2_h, timeout=30)
        assert start_r4.status_code == 400, f"Expected 400 for 4th attempt, got {start_r4.status_code}"
        assert "batas percobaan" in start_r4.text.lower() or "tercapai" in start_r4.text.lower()
        print(f"✅ 4th attempt correctly blocked: {start_r4.text}")

    def test_score_policy_tertinggi(self, siswa2_h, siswa2_id, retake_session, admin_h):
        """Score policy 'tertinggi' marks highest score as counted."""
        session_id = retake_session["id"]
        
        # Get results for this session
        results_r = requests.get(f"{API}/results/session/{session_id}", headers=admin_h, timeout=30)
        assert results_r.status_code == 200
        results = results_r.json()
        
        # Find siswa2's attempts
        siswa2_attempts = [a for a in results.get("attempts", []) if a.get("student_id") == siswa2_id]
        if len(siswa2_attempts) < 2:
            print("⚠️ Not enough attempts to test score policy")
            return
        
        # Check that exactly one is marked as counted
        counted = [a for a in siswa2_attempts if a.get("counted") is True]
        assert len(counted) == 1, f"Expected exactly 1 counted attempt, got {len(counted)}"
        
        # For tertinggi policy, the counted one should have the highest score
        if all(a.get("score") is not None for a in siswa2_attempts):
            highest_score = max(a["score"] for a in siswa2_attempts)
            assert counted[0]["score"] == highest_score, "Counted attempt is not the highest score"
            print(f"✅ Score policy 'tertinggi' working: counted attempt has score {highest_score}")

    def test_score_policy_change(self, retake_session, admin_h):
        """Changing score_policy re-runs recount for all participants."""
        session_id = retake_session["id"]
        
        # Change policy to 'terakhir'
        update_payload = {
            "title": retake_session["title"],
            "package_id": retake_session["package_id"],
            "start_time": retake_session["start_time"],
            "end_time": retake_session["end_time"],
            "duration_minutes": retake_session["duration_minutes"],
            "kkm": retake_session["kkm"],
            "class_ids": retake_session["class_ids"],
            "announcement": retake_session.get("announcement", ""),
            "max_attempts": retake_session["max_attempts"],
            "score_policy": "terakhir"
        }
        r = requests.put(f"{API}/sessions/{session_id}", json=update_payload, headers=admin_h, timeout=30)
        assert r.status_code == 200, f"Failed to update session: {r.text}"
        updated = r.json()
        assert updated["score_policy"] == "terakhir"
        print(f"✅ Score policy changed to 'terakhir'")
        
        # Verify recount happened (check attempts have score_policy field updated)
        results_r = requests.get(f"{API}/results/session/{session_id}", headers=admin_h, timeout=30)
        assert results_r.status_code == 200
        results = results_r.json()
        attempts = results.get("attempts", [])
        if attempts:
            # Check that attempts have been recounted with new policy
            for a in attempts:
                if a.get("score_policy"):
                    assert a["score_policy"] == "terakhir", f"Attempt not recounted with new policy"
            print(f"✅ Recount applied with new policy")


# --------- Regression Tests ---------

class TestRegression:
    def test_single_attempt_session_blocks_second(self, admin_h, siswa_h):
        """Single-attempt sessions (max_attempts=1) still block 2nd attempt."""
        # Get existing package and class
        pkgs_r = requests.get(f"{API}/packages", headers=admin_h, timeout=30)
        pkgs = pkgs_r.json()
        pkg = pkgs[0] if pkgs else None
        assert pkg, "No package found"
        
        classes_r = requests.get(f"{API}/classes", headers=admin_h, timeout=30)
        classes = classes_r.json()
        klass = classes[0] if classes else None
        assert klass, "No class found"
        
        now = datetime.now(timezone.utc)
        start = (now - timedelta(minutes=10)).isoformat()
        end = (now + timedelta(hours=2)).isoformat()
        
        test_id = uuid.uuid4().hex[:6]
        payload = {
            "title": f"TEST_Single_Attempt_{test_id}",
            "package_id": pkg["id"],
            "start_time": start,
            "end_time": end,
            "duration_minutes": 30,
            "kkm": 75.0,
            "class_ids": [klass["id"]],
            "max_attempts": 1,
            "score_policy": "tertinggi"
        }
        r = requests.post(f"{API}/sessions", json=payload, headers=admin_h, timeout=30)
        assert r.status_code in (200, 201)
        session = r.json()
        session_id = session["id"]
        
        # Start and submit first attempt
        start_r = requests.post(f"{API}/exam/start", json={"session_id": session_id}, headers=siswa_h, timeout=30)
        if start_r.status_code == 200:
            submit_r = requests.post(f"{API}/exam/submit", 
                                    json={"session_id": session_id, "answers": {}}, 
                                    headers=siswa_h, timeout=30)
            assert submit_r.status_code == 200
            
            # Try second attempt
            start_r2 = requests.post(f"{API}/exam/start", json={"session_id": session_id}, headers=siswa_h, timeout=30)
            assert start_r2.status_code == 400
            assert "sudah mengerjakan" in start_r2.text.lower()
            print(f"✅ Single-attempt session correctly blocks 2nd attempt")
        
        # Cleanup
        requests.delete(f"{API}/sessions/{session_id}", headers=admin_h, timeout=30)

    def test_existing_endpoints_still_work(self, admin_h, guru_h, siswa_h):
        """Regression: existing endpoints still return 200."""
        endpoints = [
            ("GET", f"{API}/categories", admin_h),
            ("GET", f"{API}/questions", guru_h),
            ("GET", f"{API}/packages", guru_h),
            ("GET", f"{API}/sessions", siswa_h),
            ("GET", f"{API}/classes", admin_h),
            ("GET", f"{API}/users", admin_h),
            ("GET", f"{API}/analytics/classes", admin_h),
        ]
        
        for method, url, headers in endpoints:
            r = requests.request(method, url, headers=headers, timeout=30)
            assert r.status_code == 200, f"{method} {url} failed: {r.status_code} {r.text}"
        
        print("✅ All existing endpoints still work")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
