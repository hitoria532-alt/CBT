"""Backend tests for iteration 3 features:
   (1) Auto-Submit cron, (2) Item Analytics, (3) Class Grade Excel export,
   (4) Image upload + protected file serving."""
import io
import os
import time
import uuid
import zipfile
from datetime import datetime, timezone, timedelta

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "hitoria532@gmail.com", "password": "admin123"}
GURU = {"email": "guru@sekolah.id", "password": "guru123"}
SISWA = {"email": "siswa@sekolah.id", "password": "siswa123"}

# Read cron secret from backend .env
CRON_SECRET = None
with open("/app/backend/.env") as f:
    for line in f:
        if line.startswith("WEBHOOK_CRON_SECRET"):
            CRON_SECRET = line.split("=", 1)[1].strip().strip('"').strip("'")
            break


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"], r.json()["user"]


def H(t):
    return {"Authorization": f"Bearer {t}"}


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN)[0]


@pytest.fixture(scope="module")
def guru_token():
    return _login(GURU)[0]


@pytest.fixture(scope="module")
def siswa():
    tok, u = _login(SISWA)
    return tok, u


# ============================================================================
# 1. AUTO-SUBMIT CRON
# ============================================================================
class TestAutoSubmitCron:
    def test_no_token_401(self):
        r = requests.post(f"{API}/cron/auto-submit", timeout=15)
        assert r.status_code == 401

    def test_wrong_token_401(self):
        r = requests.post(f"{API}/cron/auto-submit",
                          headers={"Authorization": "Bearer wrong-secret-xyz"}, timeout=15)
        assert r.status_code == 401

    def test_valid_token_accepts(self):
        assert CRON_SECRET, "cron secret not loaded"
        r = requests.post(f"{API}/cron/auto-submit",
                          headers={"Authorization": f"Bearer {CRON_SECRET}"}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json().get("accepted") is True

    def test_end_to_end_finalizes_expired_attempt(self, admin_token, siswa):
        """Create a session ending in ~10s; student starts; wait; hit cron; verify finalized."""
        stok, suser = siswa
        unique = uuid.uuid4().hex[:8]

        # Create category + PG question
        rc = requests.post(f"{API}/categories", headers=H(admin_token),
                           json={"name": f"TEST_AS_Cat_{unique}"}, timeout=15)
        assert rc.status_code == 200
        cat_id = rc.json()["id"]

        rq = requests.post(f"{API}/questions", headers=H(admin_token), json={
            "category_id": cat_id, "type": "pg",
            "text": f"TEST_AS_Q_{unique} 2+2?",
            "options": ["3", "4", "5", "6"], "correct_answer": "1", "weight": 1.0}, timeout=15)
        assert rq.status_code == 200
        qid = rq.json()["id"]

        # Package
        rp = requests.post(f"{API}/packages", headers=H(admin_token), json={
            "title": f"TEST_AS_Pkg_{unique}", "question_ids": [qid],
            "scoring_method": "percentage"}, timeout=15)
        assert rp.status_code == 200
        pkg_id = rp.json()["id"]

        # Session: currently berlangsung, end_time in ~12 seconds, long duration
        now = datetime.now(timezone.utc)
        start_time = iso(now - timedelta(minutes=5))
        end_time = iso(now + timedelta(seconds=12))
        rs = requests.post(f"{API}/sessions", headers=H(admin_token), json={
            "title": f"TEST_AS_Ses_{unique}", "package_id": pkg_id,
            "start_time": start_time, "end_time": end_time,
            "duration_minutes": 60, "kkm": 70, "class_ids": []}, timeout=15)
        assert rs.status_code == 200, rs.text
        sid = rs.json()["id"]

        # Student starts exam
        rst = requests.post(f"{API}/exam/start", headers=H(stok),
                            json={"session_id": sid}, timeout=15)
        # If siswa already has attempt on stale sessions from prior runs, that's fine only if new session
        assert rst.status_code == 200, rst.text
        attempt_id = rst.json()["attempt_id"]

        # Verify attempt is berlangsung
        # Wait for session end_time to pass (deadline = min(end, started+60min) = end)
        time.sleep(15)

        # Trigger cron
        rcron = requests.post(f"{API}/cron/auto-submit",
                              headers={"Authorization": f"Bearer {CRON_SECRET}"}, timeout=15)
        assert rcron.status_code == 200

        # Background task - poll for finalization
        finalized = None
        for _ in range(15):
            time.sleep(1)
            rd = requests.get(f"{API}/results/detail/{attempt_id}", headers=H(stok), timeout=15)
            if rd.status_code == 200 and rd.json().get("status") in ("selesai", "menunggu_koreksi"):
                finalized = rd.json()
                break
        assert finalized is not None, "Attempt not finalized by cron within 15s"
        assert finalized["status"] == "selesai"
        assert finalized["score"] is not None
        # Student didn't answer, so score should be 0
        assert finalized["score"] == 0.0

        # Cleanup
        requests.delete(f"{API}/sessions/{sid}", headers=H(admin_token))
        requests.delete(f"{API}/packages/{pkg_id}", headers=H(admin_token))
        requests.delete(f"{API}/questions/{qid}", headers=H(admin_token))
        requests.delete(f"{API}/categories/{cat_id}", headers=H(admin_token))


# ============================================================================
# 2. ITEM ANALYTICS
# ============================================================================
class TestAnalytics:
    def test_unauthorized_siswa_forbidden(self, siswa, admin_token):
        # need a session id; get any
        rs = requests.get(f"{API}/sessions", headers=H(admin_token), timeout=15)
        if not rs.json():
            pytest.skip("no sessions")
        sid = rs.json()[0]["id"]
        stok, _ = siswa
        r = requests.get(f"{API}/analytics/session/{sid}", headers=H(stok), timeout=15)
        assert r.status_code == 403

    def test_analytics_response_shape(self, admin_token, siswa):
        """Create a mini session with 2 PG questions, one attempt correct, one wrong; verify percents."""
        stok, suser = siswa
        unique = uuid.uuid4().hex[:8]

        rc = requests.post(f"{API}/categories", headers=H(admin_token),
                           json={"name": f"TEST_AN_{unique}"}, timeout=15).json()
        cid = rc["id"]
        q1 = requests.post(f"{API}/questions", headers=H(admin_token), json={
            "category_id": cid, "type": "pg", "text": f"TEST_AN_Q1_{unique}",
            "options": ["a", "b", "c", "d"], "correct_answer": "0", "weight": 1}, timeout=15).json()
        q2 = requests.post(f"{API}/questions", headers=H(admin_token), json={
            "category_id": cid, "type": "pg", "text": f"TEST_AN_Q2_{unique}",
            "options": ["a", "b", "c", "d"], "correct_answer": "1", "weight": 1}, timeout=15).json()
        pkg = requests.post(f"{API}/packages", headers=H(admin_token), json={
            "title": f"TEST_AN_Pkg_{unique}", "question_ids": [q1["id"], q2["id"]],
            "scoring_method": "percentage"}, timeout=15).json()
        now = datetime.now(timezone.utc)
        ses = requests.post(f"{API}/sessions", headers=H(admin_token), json={
            "title": f"TEST_AN_Ses_{unique}", "package_id": pkg["id"],
            "start_time": iso(now - timedelta(minutes=5)),
            "end_time": iso(now + timedelta(hours=1)),
            "duration_minutes": 60, "kkm": 70, "class_ids": []}, timeout=15).json()
        sid = ses["id"]

        # student starts and submits: q1 correct(0), q2 wrong(2)
        start = requests.post(f"{API}/exam/start", headers=H(stok),
                              json={"session_id": sid}, timeout=15).json()
        # Build answer map by original qid; but if shuffle_options was on we'd need perm.
        # This package has shuffle off, so displayed index = original.
        answers = {q1["id"]: "0", q2["id"]: "2"}
        subm = requests.post(f"{API}/exam/submit", headers=H(stok),
                             json={"session_id": sid, "answers": answers}, timeout=15)
        assert subm.status_code == 200, subm.text

        # Analytics
        r = requests.get(f"{API}/analytics/session/{sid}", headers=H(admin_token), timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["session_title"] == f"TEST_AN_Ses_{unique}"
        assert data["participants"] == 1
        assert len(data["items"]) == 2
        items_by_qid = {it["question_id"]: it for it in data["items"]}
        it1 = items_by_qid[q1["id"]]
        it2 = items_by_qid[q2["id"]]
        assert it1["percent_correct"] == 100.0
        assert it1["difficulty"] == "Mudah"
        assert it2["percent_correct"] == 0.0
        assert it2["difficulty"] == "Sulit"

        # Cleanup
        requests.delete(f"{API}/sessions/{sid}", headers=H(admin_token))
        requests.delete(f"{API}/packages/{pkg['id']}", headers=H(admin_token))
        requests.delete(f"{API}/questions/{q1['id']}", headers=H(admin_token))
        requests.delete(f"{API}/questions/{q2['id']}", headers=H(admin_token))
        requests.delete(f"{API}/categories/{cid}", headers=H(admin_token))


# ============================================================================
# 3. CLASS GRADE EXCEL EXPORT
# ============================================================================
class TestExportXlsx:
    def test_export_returns_valid_xlsx(self, admin_token, siswa):
        stok, suser = siswa
        unique = uuid.uuid4().hex[:8]
        # Create class with the siswa
        rc = requests.post(f"{API}/classes", headers=H(admin_token), json={
            "name": f"TEST_EXP_Cls_{unique}", "description": "", "student_ids": [suser["id"]]}, timeout=15)
        assert rc.status_code == 200, rc.text
        cid = rc.json()["id"]

        r = requests.get(f"{API}/export/class/{cid}/xlsx", headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        ct = r.headers.get("content-type", "")
        assert "spreadsheetml" in ct, ct
        # xlsx is a zip; verify PK header + can open
        assert r.content[:2] == b"PK", "not a valid xlsx (no PK)"
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            assert "xl/workbook.xml" in z.namelist()

        # Cleanup
        requests.delete(f"{API}/classes/{cid}", headers=H(admin_token))

    def test_export_404_for_unknown_class(self, admin_token):
        r = requests.get(f"{API}/export/class/unknown-xxx/xlsx", headers=H(admin_token), timeout=15)
        assert r.status_code == 404


# ============================================================================
# 4. IMAGE UPLOAD + FILE SERVING
# ============================================================================
# 1x1 PNG (valid minimal)
PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d49444154789c6300010000000500010d0a2db40000000049454e44ae426082"
)


class TestImageUpload:
    def test_upload_and_fetch_png(self, guru_token):
        files = {"file": ("test.png", PNG_1PX, "image/png")}
        r = requests.post(f"{API}/uploads/image", headers=H(guru_token), files=files, timeout=30)
        assert r.status_code == 200, r.text
        path = r.json()["path"]
        assert path
        # Fetch with Bearer header
        rf = requests.get(f"{API}/files/{path}", headers=H(guru_token), timeout=30)
        assert rf.status_code == 200, rf.text
        assert rf.headers.get("content-type", "").startswith("image/")
        assert rf.content[:8] == PNG_1PX[:8]
        # Fetch with query param
        rq = requests.get(f"{API}/files/{path}?auth={guru_token}", timeout=30)
        assert rq.status_code == 200

    def test_upload_invalid_ext_400(self, guru_token):
        files = {"file": ("evil.txt", b"hello", "text/plain")}
        r = requests.post(f"{API}/uploads/image", headers=H(guru_token), files=files, timeout=15)
        assert r.status_code == 400

    def test_files_no_auth_401(self):
        r = requests.get(f"{API}/files/some/random/path.png", timeout=15)
        assert r.status_code == 401

    def test_files_unknown_path_404(self, guru_token):
        r = requests.get(f"{API}/files/cbt-ujian/questions/nonexistent-{uuid.uuid4().hex}.png",
                         headers=H(guru_token), timeout=15)
        assert r.status_code == 404

    def test_siswa_cannot_upload(self, siswa):
        stok, _ = siswa
        files = {"file": ("test.png", PNG_1PX, "image/png")}
        r = requests.post(f"{API}/uploads/image", headers=H(stok), files=files, timeout=15)
        assert r.status_code == 403


# ============================================================================
# 5. REGRESSION: image_path persisted on question, sanitize returns it,
#    student ExamView receives it, result_detail returns it
# ============================================================================
class TestImageIntegration:
    def test_question_with_image_flows_to_exam_and_result(self, admin_token, guru_token, siswa):
        stok, suser = siswa
        unique = uuid.uuid4().hex[:8]
        # Upload image
        files = {"file": ("q.png", PNG_1PX, "image/png")}
        up = requests.post(f"{API}/uploads/image", headers=H(guru_token), files=files, timeout=30).json()
        img_path = up["path"]

        rc = requests.post(f"{API}/categories", headers=H(admin_token),
                           json={"name": f"TEST_IMG_{unique}"}, timeout=15).json()
        cid = rc["id"]
        q = requests.post(f"{API}/questions", headers=H(admin_token), json={
            "category_id": cid, "type": "pg", "text": f"TEST_IMG_Q_{unique}",
            "options": ["a", "b"], "correct_answer": "0", "weight": 1,
            "image_path": img_path}, timeout=15).json()
        assert q.get("image_path") == img_path

        pkg = requests.post(f"{API}/packages", headers=H(admin_token), json={
            "title": f"TEST_IMG_Pkg_{unique}", "question_ids": [q["id"]],
            "scoring_method": "percentage"}, timeout=15).json()
        now = datetime.now(timezone.utc)
        ses = requests.post(f"{API}/sessions", headers=H(admin_token), json={
            "title": f"TEST_IMG_Ses_{unique}", "package_id": pkg["id"],
            "start_time": iso(now - timedelta(minutes=5)),
            "end_time": iso(now + timedelta(hours=1)),
            "duration_minutes": 60, "kkm": 70, "class_ids": []}, timeout=15).json()
        sid = ses["id"]

        # Student starts exam, expects image_path in question payload
        st = requests.post(f"{API}/exam/start", headers=H(stok),
                           json={"session_id": sid}, timeout=15).json()
        assert st["questions"][0]["image_path"] == img_path

        # Submit; result detail should also include image_path
        requests.post(f"{API}/exam/submit", headers=H(stok),
                      json={"session_id": sid, "answers": {q["id"]: "0"}}, timeout=15)
        rd = requests.get(f"{API}/results/detail/{st['attempt_id']}", headers=H(stok), timeout=15).json()
        assert rd["details"][0]["image_path"] == img_path

        # Cleanup
        requests.delete(f"{API}/sessions/{sid}", headers=H(admin_token))
        requests.delete(f"{API}/packages/{pkg['id']}", headers=H(admin_token))
        requests.delete(f"{API}/questions/{q['id']}", headers=H(admin_token))
        requests.delete(f"{API}/categories/{cid}", headers=H(admin_token))
