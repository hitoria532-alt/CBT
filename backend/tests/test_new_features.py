"""Backend tests for iteration 2 new features: Impor Soal, Acak Soal, Manajemen Kelas, Kartu Hasil PDF."""
import io
import os
import time
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "hitoria532@gmail.com", "password": "admin123"}
GURU = {"email": "guru@sekolah.id", "password": "guru123"}
SISWA = {"email": "siswa@sekolah.id", "password": "siswa123"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"], r.json()["user"]


def H(t):
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN)[0]


@pytest.fixture(scope="module")
def guru_token():
    return _login(GURU)[0]


# ============================================================
# 1. IMPOR SOAL
# ============================================================
class TestImportSoal:
    def test_import_template_download(self, admin_token):
        r = requests.get(f"{API}/questions/import-template", headers=H(admin_token))
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
        body = r.text
        assert "type,text,option_a" in body

    def test_import_valid_csv(self, admin_token):
        unique = int(time.time())
        csv_text = (
            "type,text,option_a,option_b,option_c,option_d,correct,weight,category\n"
            f"pg,TEST_IMP_{unique} Berapa 2+2?,3,4,5,6,B,2,TEST_ImportCat_{unique}\n"
            f"truefalse,TEST_IMP_{unique} Bumi bulat.,,,,,benar,1,TEST_ImportCat_{unique}\n"
            f"essay,TEST_IMP_{unique} Jelaskan gravitasi.,,,,,,3,TEST_ImportCat_{unique}\n"
        )
        files = {"file": ("soal.csv", csv_text.encode("utf-8"), "text/csv")}
        r = requests.post(f"{API}/questions/import", headers=H(admin_token), files=files)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["imported"] == 3, data
        assert data["errors"] == []

        # Verify persistence + category auto-created
        cats = requests.get(f"{API}/categories", headers=H(admin_token)).json()
        cat = next((c for c in cats if c["name"] == f"TEST_ImportCat_{unique}"), None)
        assert cat is not None, "Category not auto-created"

        qs = requests.get(f"{API}/questions?category_id={cat['id']}", headers=H(admin_token)).json()
        assert len(qs) == 3
        pg = next(q for q in qs if q["type"] == "pg")
        assert pg["options"] == ["3", "4", "5", "6"]
        assert pg["correct_answer"] == "1"  # B -> index 1
        assert pg["weight"] == 2.0
        tf = next(q for q in qs if q["type"] == "truefalse")
        assert tf["correct_answer"] == "true"
        essay = next(q for q in qs if q["type"] == "essay")
        assert essay["weight"] == 3.0

        # cleanup
        for q in qs:
            requests.delete(f"{API}/questions/{q['id']}", headers=H(admin_token))
        requests.delete(f"{API}/categories/{cat['id']}", headers=H(admin_token))

    def test_import_invalid_rows_reported(self, admin_token):
        csv_text = (
            "type,text,option_a,option_b,option_c,option_d,correct,weight,category\n"
            "pg,,a,b,c,d,A,1,X\n"  # missing text
            "unknown,Foo,,,,,,,\n"  # bad type
        )
        files = {"file": ("bad.csv", csv_text.encode("utf-8"), "text/csv")}
        r = requests.post(f"{API}/questions/import", headers=H(admin_token), files=files)
        assert r.status_code == 200
        d = r.json()
        assert d["imported"] == 0
        assert len(d["errors"]) >= 2

    def test_import_siswa_forbidden(self):
        tok, _ = _login(SISWA)
        files = {"file": ("x.csv", b"type,text\npg,hi", "text/csv")}
        r = requests.post(f"{API}/questions/import", headers=H(tok), files=files)
        assert r.status_code == 403


# ============================================================
# 2. ACAK SOAL (shuffle + grading correctness)
# ============================================================
class TestShuffle:
    @pytest.fixture(scope="class")
    def shuffle_setup(self, admin_token):
        """Create dedicated category/questions/package/session/students."""
        u = int(time.time())
        # Category
        cat = requests.post(f"{API}/categories", headers=H(admin_token),
                            json={"name": f"TEST_Shuffle_{u}", "description": ""}).json()
        # 4 PG questions each with 4 options; correct varies
        qids = []
        correct_map = {}
        for i in range(4):
            body = {
                "category_id": cat["id"], "type": "pg",
                "text": f"TEST_SHF_{u} Q{i}",
                "options": [f"opt{i}A", f"opt{i}B", f"opt{i}C", f"opt{i}D"],
                "correct_answer": str(i % 4),  # 0,1,2,3
                "weight": 1.0,
            }
            q = requests.post(f"{API}/questions", headers=H(admin_token), json=body).json()
            qids.append(q["id"])
            correct_map[q["id"]] = {"correct_index": i % 4,
                                    "correct_text": body["options"][i % 4]}
        # Package with shuffles on
        pkg = requests.post(f"{API}/packages", headers=H(admin_token), json={
            "title": f"TEST_ShufflePkg_{u}", "description": "",
            "category_id": cat["id"], "question_ids": qids,
            "scoring_method": "percentage",
            "shuffle_questions": True, "shuffle_options": True,
        }).json()
        # Session: active window
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        start = (now - timedelta(minutes=5)).isoformat()
        end = (now + timedelta(hours=2)).isoformat()
        sess = requests.post(f"{API}/sessions", headers=H(admin_token), json={
            "title": f"TEST_ShuffleSess_{u}", "package_id": pkg["id"],
            "start_time": start, "end_time": end, "duration_minutes": 60,
            "kkm": 75.0, "class_ids": [],
        }).json()
        # 2 fresh students
        students = []
        for j in range(2):
            email = f"test_shf_stu_{u}_{j}@example.com"
            usr = requests.post(f"{API}/users", headers=H(admin_token), json={
                "email": email, "password": "pw12345",
                "name": f"TEST_Stu_{j}", "role": "siswa"
            }).json()
            tok, _ = _login({"email": email, "password": "pw12345"})
            students.append({"id": usr["id"], "token": tok, "email": email})
        yield {"cat": cat, "qids": qids, "correct_map": correct_map,
               "pkg": pkg, "sess": sess, "students": students}
        # Teardown
        for s in students:
            requests.delete(f"{API}/users/{s['id']}", headers=H(admin_token))
        requests.delete(f"{API}/sessions/{sess['id']}", headers=H(admin_token))
        requests.delete(f"{API}/packages/{pkg['id']}", headers=H(admin_token))
        for qid in qids:
            requests.delete(f"{API}/questions/{qid}", headers=H(admin_token))
        requests.delete(f"{API}/categories/{cat['id']}", headers=H(admin_token))

    def test_shuffle_stable_on_resume(self, shuffle_setup):
        s = shuffle_setup["students"][0]
        r1 = requests.post(f"{API}/exam/start", headers=H(s["token"]),
                           json={"session_id": shuffle_setup["sess"]["id"]})
        assert r1.status_code == 200, r1.text
        first = r1.json()
        r2 = requests.post(f"{API}/exam/start", headers=H(s["token"]),
                           json={"session_id": shuffle_setup["sess"]["id"]})
        second = r2.json()
        # order stable
        assert [q["id"] for q in first["questions"]] == [q["id"] for q in second["questions"]]
        for q1, q2 in zip(first["questions"], second["questions"]):
            assert q1["options"] == q2["options"]

    def test_shuffle_grading_with_option_perm(self, shuffle_setup):
        """Submit using DISPLAYED indices matching correct option text; verify score=100."""
        s = shuffle_setup["students"][1]
        r = requests.post(f"{API}/exam/start", headers=H(s["token"]),
                          json={"session_id": shuffle_setup["sess"]["id"]})
        data = r.json()
        answers = {}
        for q in data["questions"]:
            correct_text = shuffle_setup["correct_map"][q["id"]]["correct_text"]
            displayed_idx = q["options"].index(correct_text)
            answers[q["id"]] = str(displayed_idx)
        sub = requests.post(f"{API}/exam/submit", headers=H(s["token"]),
                            json={"session_id": shuffle_setup["sess"]["id"], "answers": answers})
        assert sub.status_code == 200, sub.text
        body = sub.json()
        assert body["needs_grading"] is False
        assert body["score"] == 100.0, f"Expected 100, got {body}"

    def test_two_students_can_get_different_orders(self, admin_token, shuffle_setup):
        """Fresh new attempts should each generate independent randomization.
        Note both students already started in prior tests. Check their stored attempts differ (probabilistically).
        With 4 questions and 4 options, prob of identical order = 1/24, prob of identical option perms for all 4 questions = (1/24)^4 = tiny.
        Still, we assert that AT LEAST ONE of question order or option perms differ.
        """
        # Fetch each student's displayed order via /exam/start (idempotent for existing attempt)
        outs = []
        for s in shuffle_setup["students"]:
            r = requests.post(f"{API}/exam/start", headers=H(s["token"]),
                              json={"session_id": shuffle_setup["sess"]["id"]})
            if r.status_code == 200:
                d = r.json()
                outs.append({
                    "order": [q["id"] for q in d["questions"]],
                    "opts": {q["id"]: q["options"] for q in d["questions"]},
                })
        if len(outs) < 2:
            pytest.skip("Second student already submitted; cannot compare orders")
        a, b = outs[0], outs[1]
        diff_order = a["order"] != b["order"]
        diff_opts = any(a["opts"].get(qid) != b["opts"].get(qid) for qid in a["opts"])
        assert diff_order or diff_opts, "Both students got identical shuffle - randomization suspect"


# ============================================================
# 3. MANAJEMEN KELAS
# ============================================================
class TestClasses:
    def test_class_crud_and_session_filter(self, admin_token):
        u = int(time.time())
        # Create student
        email_a = f"test_cls_a_{u}@example.com"
        email_b = f"test_cls_b_{u}@example.com"
        sa = requests.post(f"{API}/users", headers=H(admin_token), json={
            "email": email_a, "password": "pw12345", "name": "TEST_ClsA", "role": "siswa"}).json()
        sb = requests.post(f"{API}/users", headers=H(admin_token), json={
            "email": email_b, "password": "pw12345", "name": "TEST_ClsB", "role": "siswa"}).json()

        # Create class with only student A
        cls_r = requests.post(f"{API}/classes", headers=H(admin_token), json={
            "name": f"TEST_KelasA_{u}", "description": "d", "student_ids": [sa["id"]]})
        assert cls_r.status_code == 200
        cls = cls_r.json()
        assert cls["student_count"] == 1
        cls_id = cls["id"]

        # GET list
        lst = requests.get(f"{API}/classes", headers=H(admin_token)).json()
        assert any(c["id"] == cls_id for c in lst)

        # Update: add student B
        upd = requests.put(f"{API}/classes/{cls_id}", headers=H(admin_token), json={
            "name": f"TEST_KelasA_{u}", "description": "d",
            "student_ids": [sa["id"], sb["id"]]}).json()
        assert upd["student_count"] == 2

        # Session assigned to class - only members should see it
        # Need a package
        cat = requests.post(f"{API}/categories", headers=H(admin_token),
                            json={"name": f"TEST_ClsCat_{u}"}).json()
        q = requests.post(f"{API}/questions", headers=H(admin_token), json={
            "category_id": cat["id"], "type": "essay", "text": "TEST_ClsQ",
            "options": [], "correct_answer": None, "weight": 1.0}).json()
        pkg = requests.post(f"{API}/packages", headers=H(admin_token), json={
            "title": f"TEST_ClsPkg_{u}", "category_id": cat["id"],
            "question_ids": [q["id"]], "scoring_method": "percentage"}).json()
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        sess = requests.post(f"{API}/sessions", headers=H(admin_token), json={
            "title": f"TEST_ClsSess_{u}", "package_id": pkg["id"],
            "start_time": (now - timedelta(minutes=5)).isoformat(),
            "end_time": (now + timedelta(hours=2)).isoformat(),
            "duration_minutes": 60, "kkm": 75.0, "class_ids": [cls_id]}).json()

        # Login as A (member) - should see session
        tok_a, _ = _login({"email": email_a, "password": "pw12345"})
        sees_a = requests.get(f"{API}/sessions", headers=H(tok_a)).json()
        assert any(s["id"] == sess["id"] for s in sees_a), "Class member A must see targeted session"

        # Remove A from class -> shouldn't see it
        requests.put(f"{API}/classes/{cls_id}", headers=H(admin_token), json={
            "name": f"TEST_KelasA_{u}", "description": "d", "student_ids": [sb["id"]]})
        sees_a2 = requests.get(f"{API}/sessions", headers=H(tok_a)).json()
        assert not any(s["id"] == sess["id"] for s in sees_a2), "Non-member should not see class-restricted session"

        # Session with NO class -> everyone sees
        open_sess = requests.post(f"{API}/sessions", headers=H(admin_token), json={
            "title": f"TEST_OpenSess_{u}", "package_id": pkg["id"],
            "start_time": (now - timedelta(minutes=5)).isoformat(),
            "end_time": (now + timedelta(hours=2)).isoformat(),
            "duration_minutes": 60, "kkm": 75.0, "class_ids": []}).json()
        sees_a3 = requests.get(f"{API}/sessions", headers=H(tok_a)).json()
        assert any(s["id"] == open_sess["id"] for s in sees_a3), "Open session must be visible to all students"

        # Non-siswa list should include class_names
        adm_sessions = requests.get(f"{API}/sessions", headers=H(admin_token)).json()
        target = next(s for s in adm_sessions if s["id"] == sess["id"])
        assert "class_names" in target

        # Cleanup
        requests.delete(f"{API}/sessions/{sess['id']}", headers=H(admin_token))
        requests.delete(f"{API}/sessions/{open_sess['id']}", headers=H(admin_token))
        requests.delete(f"{API}/packages/{pkg['id']}", headers=H(admin_token))
        requests.delete(f"{API}/questions/{q['id']}", headers=H(admin_token))
        requests.delete(f"{API}/categories/{cat['id']}", headers=H(admin_token))
        requests.delete(f"{API}/classes/{cls_id}", headers=H(admin_token))
        requests.delete(f"{API}/users/{sa['id']}", headers=H(admin_token))
        requests.delete(f"{API}/users/{sb['id']}", headers=H(admin_token))

    def test_siswa_cannot_list_classes(self):
        tok, _ = _login(SISWA)
        r = requests.get(f"{API}/classes", headers=H(tok))
        assert r.status_code == 403


# ============================================================
# 4. KARTU HASIL PDF
# ============================================================
class TestResultPDF:
    def test_pdf_download_admin(self, admin_token):
        # Find a completed attempt
        sess = requests.get(f"{API}/sessions", headers=H(admin_token)).json()
        target = next(s for s in sess if s["title"] == "UH Matematika - Kelas X")
        res = requests.get(f"{API}/results/session/{target['id']}", headers=H(admin_token)).json()
        attempts = res["attempts"]
        assert attempts, "Need at least one attempt from seed"
        # Prefer completed
        att = next((a for a in attempts if a.get("status") == "selesai"), attempts[0])
        r = requests.get(f"{API}/results/detail/{att['id']}/pdf", headers=H(admin_token))
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"
        assert len(r.content) > 1000

    def test_pdf_student_own_only(self, admin_token):
        # Try to fetch a PDF as SISWA - siswa can access own attempts only
        stok, suser = _login(SISWA)
        mine = requests.get(f"{API}/results/me", headers=H(stok)).json()
        if mine:
            r = requests.get(f"{API}/results/detail/{mine[0]['id']}/pdf", headers=H(stok))
            assert r.status_code == 200
            assert r.headers.get("content-type", "").startswith("application/pdf")
        # Try someone else's attempt
        sess = requests.get(f"{API}/sessions", headers=H(admin_token)).json()
        target = next(s for s in sess if s["title"] == "UH Matematika - Kelas X")
        res = requests.get(f"{API}/results/session/{target['id']}", headers=H(admin_token)).json()
        other = next((a for a in res["attempts"] if a["student_id"] != suser["id"]), None)
        if other:
            r = requests.get(f"{API}/results/detail/{other['id']}/pdf", headers=H(stok))
            assert r.status_code == 403


# ============================================================
# 5. REGRESSION - basic auth still works
# ============================================================
class TestRegression:
    def test_admin_login(self):
        _login(ADMIN)

    def test_guru_login(self):
        _login(GURU)

    def test_siswa_login(self):
        _login(SISWA)
