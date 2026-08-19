"""Backend API tests for the Indonesian CBT/online exam app."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://quiz-master-app-67.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "hitoria532@gmail.com", "password": "admin123"}
GURU = {"email": "guru@sekolah.id", "password": "guru123"}
SISWA = {"email": "siswa@sekolah.id", "password": "siswa123"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["token"], r.json()["user"]


@pytest.fixture(scope="module")
def admin_token():
    tok, _ = _login(ADMIN)
    return tok


@pytest.fixture(scope="module")
def guru_token():
    tok, _ = _login(GURU)
    return tok


@pytest.fixture(scope="module")
def siswa_ctx():
    tok, user = _login(SISWA)
    return {"token": tok, "user": user}


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


# -------- AUTH --------
class TestAuth:
    def test_admin_login(self):
        tok, u = _login(ADMIN)
        assert u["role"] == "admin" and u["email"] == ADMIN["email"]

    def test_guru_login(self):
        tok, u = _login(GURU)
        assert u["role"] == "guru"

    def test_siswa_login(self):
        tok, u = _login(SISWA)
        assert u["role"] == "siswa"

    def test_wrong_password(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN["email"], "password": "wrong"})
        assert r.status_code == 401

    def test_me(self, admin_token):
        r = requests.get(f"{API}/auth/me", headers=H(admin_token))
        assert r.status_code == 200 and r.json()["role"] == "admin"

    def test_me_no_token(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401


# -------- USERS (admin only) --------
class TestUsers:
    created_id = None

    def test_list_users_admin(self, admin_token):
        r = requests.get(f"{API}/users", headers=H(admin_token))
        assert r.status_code == 200 and isinstance(r.json(), list)

    def test_list_users_role_filter(self, admin_token):
        r = requests.get(f"{API}/users?role=siswa", headers=H(admin_token))
        assert r.status_code == 200
        assert all(u["role"] == "siswa" for u in r.json())

    def test_guru_cannot_create_user(self, guru_token):
        r = requests.post(f"{API}/users", headers=H(guru_token),
                          json={"email": "TEST_x@x.com", "password": "p", "name": "x", "role": "siswa"})
        assert r.status_code == 403

    def test_crud_user(self, admin_token):
        payload = {"email": f"test_{int(time.time())}@example.com",
                   "password": "pw12345", "name": "TEST User", "role": "siswa", "identifier": "N001"}
        r = requests.post(f"{API}/users", headers=H(admin_token), json=payload)
        assert r.status_code == 200, r.text
        uid = r.json()["id"]
        assert r.json()["email"] == payload["email"]
        # update
        r2 = requests.put(f"{API}/users/{uid}", headers=H(admin_token), json={"name": "TEST Updated"})
        assert r2.status_code == 200 and r2.json()["name"] == "TEST Updated"
        # verify via list
        r3 = requests.get(f"{API}/users", headers=H(admin_token))
        assert any(u["id"] == uid and u["name"] == "TEST Updated" for u in r3.json())
        # delete
        r4 = requests.delete(f"{API}/users/{uid}", headers=H(admin_token))
        assert r4.status_code == 200


# -------- CATEGORIES / QUESTIONS / PACKAGES / SESSIONS --------
class TestContent:
    def test_categories_list(self, admin_token):
        r = requests.get(f"{API}/categories", headers=H(admin_token))
        assert r.status_code == 200 and len(r.json()) >= 1

    def test_questions_list(self, guru_token):
        r = requests.get(f"{API}/questions", headers=H(guru_token))
        assert r.status_code == 200
        types = {q["type"] for q in r.json()}
        assert {"pg", "truefalse", "essay"}.issubset(types) or len(r.json()) >= 3

    def test_siswa_cannot_list_questions(self, siswa_ctx):
        r = requests.get(f"{API}/questions", headers=H(siswa_ctx["token"]))
        assert r.status_code == 403

    def test_packages_list(self, guru_token):
        r = requests.get(f"{API}/packages", headers=H(guru_token))
        assert r.status_code == 200 and len(r.json()) >= 1

    def test_sessions_list(self, siswa_ctx):
        r = requests.get(f"{API}/sessions", headers=H(siswa_ctx["token"]))
        assert r.status_code == 200
        sessions = r.json()
        assert any(s["title"] == "UH Matematika - Kelas X" for s in sessions)

    def test_create_delete_category(self, guru_token):
        r = requests.post(f"{API}/categories", headers=H(guru_token),
                          json={"name": "TEST_Cat", "description": "d"})
        assert r.status_code == 200
        cid = r.json()["id"]
        r2 = requests.delete(f"{API}/categories/{cid}", headers=H(guru_token))
        assert r2.status_code == 200


# -------- DASHBOARD --------
class TestDashboard:
    def test_stats(self, admin_token):
        r = requests.get(f"{API}/dashboard/stats", headers=H(admin_token))
        assert r.status_code == 200
        data = r.json()
        for k in ("students", "teachers", "questions", "packages", "sessions", "avg_score"):
            assert k in data

    def test_stats_forbidden_siswa(self, siswa_ctx):
        r = requests.get(f"{API}/dashboard/stats", headers=H(siswa_ctx["token"]))
        assert r.status_code == 403


# -------- EXAM FLOW (uses seeded session + siswa) --------
# NOTE: siswa can only submit once. We test start (returns questions) and results endpoints.
# We create a NEW student & attempt via admin to test full submit + grade + weighted math.
class TestExamFlow:
    def test_start_exam_seeded(self, siswa_ctx):
        # Find session id
        r = requests.get(f"{API}/sessions", headers=H(siswa_ctx["token"]))
        session = next(s for s in r.json() if s["title"] == "UH Matematika - Kelas X")
        r2 = requests.post(f"{API}/exam/start", headers=H(siswa_ctx["token"]),
                           json={"session_id": session["id"]})
        assert r2.status_code == 200, r2.text
        data = r2.json()
        assert len(data["questions"]) == 3
        types = [q["type"] for q in data["questions"]]
        assert set(types) == {"pg", "truefalse", "essay"}
        # ensure correct_answer not leaked
        for q in data["questions"]:
            assert "correct_answer" not in q

    def test_full_flow_new_student(self, admin_token):
        # Get session + package + questions
        sess_r = requests.get(f"{API}/sessions", headers=H(admin_token))
        session = next(s for s in sess_r.json() if s["title"] == "UH Matematika - Kelas X")
        pkg_r = requests.get(f"{API}/packages/{session['package_id']}", headers=H(admin_token))
        pkg = pkg_r.json()
        assert pkg["scoring_method"] == "weighted"
        q_r = requests.get(f"{API}/questions", headers=H(admin_token))
        qmap = {q["id"]: q for q in q_r.json()}
        pkg_questions = [qmap[qid] for qid in pkg["question_ids"]]

        # Create new student
        email = f"test_stu_{int(time.time())}@example.com"
        cu = requests.post(f"{API}/users", headers=H(admin_token),
                           json={"email": email, "password": "pw12345",
                                 "name": "TEST Stu", "role": "siswa"})
        assert cu.status_code == 200
        new_uid = cu.json()["id"]
        try:
            stu_tok, _ = _login({"email": email, "password": "pw12345"})
            # Start
            st = requests.post(f"{API}/exam/start", headers=H(stu_tok),
                               json={"session_id": session["id"]})
            assert st.status_code == 200

            # Prepare correct answers for pg & tf, essay answer text
            answers = {}
            essay_qid = None
            pg_weight = tf_weight = essay_weight = 0
            for q in pkg_questions:
                full = qmap[q["id"]]
                if full["type"] == "pg":
                    answers[q["id"]] = full["correct_answer"]
                    pg_weight = full["weight"]
                elif full["type"] == "truefalse":
                    answers[q["id"]] = full["correct_answer"]
                    tf_weight = full["weight"]
                else:
                    essay_qid = q["id"]
                    essay_weight = full["weight"]
                    answers[q["id"]] = "jawaban essay saya"

            # Submit
            sub = requests.post(f"{API}/exam/submit", headers=H(stu_tok),
                                json={"session_id": session["id"], "answers": answers})
            assert sub.status_code == 200, sub.text
            body = sub.json()
            assert body["needs_grading"] is True
            assert body["status"] == "menunggu_koreksi"
            assert body["score"] is None

            # Results for me (student)
            mine = requests.get(f"{API}/results/me", headers=H(stu_tok))
            assert mine.status_code == 200 and len(mine.json()) == 1
            attempt_id = mine.json()[0]["id"]

            # Grade essay full points
            g = requests.post(f"{API}/results/grade/{attempt_id}",
                              headers=H(admin_token),
                              json={"scores": {essay_qid: essay_weight}})
            assert g.status_code == 200
            gd = g.json()
            expected_total = pg_weight + tf_weight + essay_weight
            expected_earned = pg_weight + tf_weight + essay_weight
            expected_score = round(expected_earned / expected_total * 100, 2)
            assert gd["needs_grading"] is False
            assert gd["score"] == expected_score, f"got {gd['score']} expected {expected_score}"
            assert expected_score == 100.0

            # Detail
            det = requests.get(f"{API}/results/detail/{attempt_id}", headers=H(admin_token))
            assert det.status_code == 200
            djson = det.json()
            assert djson["score"] == expected_score
            assert djson["scoring_method"] == "weighted"
            assert len(djson["details"]) == 3
        finally:
            requests.delete(f"{API}/users/{new_uid}", headers=H(admin_token))
            # Also cleanup attempts
