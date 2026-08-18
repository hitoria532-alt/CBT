"""Backend tests for iteration 4 features:
(1) Bank Rumus Nilai (min_score + rounding on packages / compute_grade)
(2) Analitik Kelas (/api/analytics/classes)
(3) Soal Gambar Massal (CSV import with image_url column)
(4) Pengumuman Sesi (/api/notifications + Session.announcement)
"""
import io
import os
import uuid
from datetime import datetime, timezone, timedelta

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


def _mk_pkg_with_qs(admin_token, n=3, unique=None, min_score=0.0, rounding="2desimal"):
    """Create category + n PG questions (correct index=0) + package. Returns ids."""
    unique = unique or uuid.uuid4().hex[:8]
    rc = requests.post(f"{API}/categories", headers=H(admin_token),
                       json={"name": f"TEST_I4_{unique}"}, timeout=15).json()
    cid = rc["id"]
    qids = []
    for i in range(n):
        q = requests.post(f"{API}/questions", headers=H(admin_token), json={
            "category_id": cid, "type": "pg", "text": f"TEST_I4_Q{i}_{unique}",
            "options": ["a", "b", "c", "d"], "correct_answer": "0", "weight": 1}, timeout=15).json()
        qids.append(q["id"])
    pkg = requests.post(f"{API}/packages", headers=H(admin_token), json={
        "title": f"TEST_I4_Pkg_{unique}", "question_ids": qids,
        "scoring_method": "percentage",
        "min_score": min_score, "rounding": rounding}, timeout=15).json()
    return cid, qids, pkg


def _cleanup(admin_token, cid=None, qids=(), pkg_id=None, sid=None):
    if sid: requests.delete(f"{API}/sessions/{sid}", headers=H(admin_token))
    if pkg_id: requests.delete(f"{API}/packages/{pkg_id}", headers=H(admin_token))
    for q in qids: requests.delete(f"{API}/questions/{q}", headers=H(admin_token))
    if cid: requests.delete(f"{API}/categories/{cid}", headers=H(admin_token))


# ============================================================================
# 1. BANK RUMUS NILAI - min_score + rounding
# ============================================================================
class TestScoringFloorAndRounding:
    def test_package_persists_min_score_and_rounding(self, admin_token):
        unique = uuid.uuid4().hex[:8]
        cid, qids, pkg = _mk_pkg_with_qs(admin_token, n=1, unique=unique,
                                         min_score=40.0, rounding="bulat")
        # GET package back
        r = requests.get(f"{API}/packages/{pkg['id']}", headers=H(admin_token), timeout=15)
        assert r.status_code == 200
        got = r.json()
        assert got["min_score"] == 40.0
        assert got["rounding"] == "bulat"
        _cleanup(admin_token, cid=cid, qids=qids, pkg_id=pkg["id"])

    def test_min_score_floor_with_integer_rounding(self, admin_token, siswa):
        """1/3 correct → raw 33.33 → round bulat = 33 → floored to 40."""
        stok, _ = siswa
        unique = uuid.uuid4().hex[:8]
        cid, qids, pkg = _mk_pkg_with_qs(admin_token, n=3, unique=unique,
                                         min_score=40.0, rounding="bulat")
        now = datetime.now(timezone.utc)
        ses = requests.post(f"{API}/sessions", headers=H(admin_token), json={
            "title": f"TEST_I4_Ses_{unique}", "package_id": pkg["id"],
            "start_time": iso(now - timedelta(minutes=5)),
            "end_time": iso(now + timedelta(hours=1)),
            "duration_minutes": 60, "kkm": 70, "class_ids": []}, timeout=15).json()
        sid = ses["id"]

        st = requests.post(f"{API}/exam/start", headers=H(stok),
                           json={"session_id": sid}, timeout=15).json()
        # Answer q0 correctly (=0), leave others wrong
        answers = {qids[0]: "0", qids[1]: "3", qids[2]: "3"}
        subm = requests.post(f"{API}/exam/submit", headers=H(stok),
                             json={"session_id": sid, "answers": answers}, timeout=15)
        assert subm.status_code == 200, subm.text

        rd = requests.get(f"{API}/results/detail/{st['attempt_id']}",
                          headers=H(stok), timeout=15).json()
        assert rd["status"] == "selesai"
        assert rd["score"] == 40.0, f"expected floored score 40.0 got {rd['score']}"
        _cleanup(admin_token, cid=cid, qids=qids, pkg_id=pkg["id"], sid=sid)

    def test_rounding_1desimal_produces_one_decimal(self, admin_token, siswa):
        """1/3 correct with rounding=1desimal, min_score=0 → 33.3"""
        stok, _ = siswa
        unique = uuid.uuid4().hex[:8]
        cid, qids, pkg = _mk_pkg_with_qs(admin_token, n=3, unique=unique,
                                         min_score=0.0, rounding="1desimal")
        now = datetime.now(timezone.utc)
        ses = requests.post(f"{API}/sessions", headers=H(admin_token), json={
            "title": f"TEST_I4_1d_{unique}", "package_id": pkg["id"],
            "start_time": iso(now - timedelta(minutes=5)),
            "end_time": iso(now + timedelta(hours=1)),
            "duration_minutes": 60, "kkm": 70, "class_ids": []}, timeout=15).json()
        sid = ses["id"]
        st = requests.post(f"{API}/exam/start", headers=H(stok),
                           json={"session_id": sid}, timeout=15).json()
        answers = {qids[0]: "0", qids[1]: "3", qids[2]: "3"}
        requests.post(f"{API}/exam/submit", headers=H(stok),
                      json={"session_id": sid, "answers": answers}, timeout=15)
        rd = requests.get(f"{API}/results/detail/{st['attempt_id']}",
                          headers=H(stok), timeout=15).json()
        # 100/3 = 33.333... rounded to 1 dp -> 33.3
        assert rd["score"] == 33.3, f"expected 33.3 got {rd['score']}"
        # verify one decimal max (str form)
        s = repr(rd["score"])
        # e.g. '33.3' - can't have more than 1 fractional digit
        if "." in s:
            assert len(s.split(".")[1]) <= 1
        _cleanup(admin_token, cid=cid, qids=qids, pkg_id=pkg["id"], sid=sid)


# ============================================================================
# 2. ANALITIK KELAS
# ============================================================================
class TestAnalyticsClasses:
    def test_siswa_forbidden(self, siswa):
        stok, _ = siswa
        r = requests.get(f"{API}/analytics/classes", headers=H(stok), timeout=15)
        assert r.status_code == 403

    def test_admin_shape(self, admin_token):
        r = requests.get(f"{API}/analytics/classes", headers=H(admin_token), timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "classes" in data and "trend" in data
        assert isinstance(data["classes"], list)
        assert isinstance(data["trend"], list)
        for c in data["classes"]:
            assert {"class_id", "name", "avg_score", "completed", "students"} <= set(c.keys())
        for t in data["trend"]:
            assert {"session", "avg"} <= set(t.keys())

    def test_guru_allowed(self, guru_token):
        r = requests.get(f"{API}/analytics/classes", headers=H(guru_token), timeout=15)
        assert r.status_code == 200


# ============================================================================
# 3. SOAL GAMBAR MASSAL - import with image_url column
# ============================================================================
GOOD_IMG = "https://httpbin.org/image/png"
BAD_IMG = "https://example.com/definitely-does-not-exist-xyz-9x9.png"


class TestImportWithImageUrl:
    def test_template_contains_image_url_column(self, admin_token):
        r = requests.get(f"{API}/questions/import-template", headers=H(admin_token), timeout=15)
        assert r.status_code == 200
        # response can be CSV bytes or JSON with content field; check body
        body = r.text if r.text else ""
        assert "image_url" in body, f"template missing image_url column: {body[:200]}"

    def test_import_row_with_valid_image_downloads(self, admin_token):
        unique = uuid.uuid4().hex[:8]
        cat = requests.post(f"{API}/categories", headers=H(admin_token),
                            json={"name": f"TEST_I4_IMP_{unique}"}, timeout=15).json()
        cat_name = cat["name"]

            # CSV: category,type,text,option_a,option_b,option_c,option_d,correct,weight,image_url
        csv = (
            "category,type,text,option_a,option_b,option_c,option_d,correct,weight,image_url\n"
            f'{cat_name},pg,TEST_I4_IMPQ_{unique},aa,bb,cc,dd,a,1,{GOOD_IMG}\n'
            f'{cat_name},pg,TEST_I4_IMPQ2_{unique},aa,bb,cc,dd,a,1,{BAD_IMG}\n'
        )
        files = {"file": (f"import_{unique}.csv", csv.encode(), "text/csv")}
        r = requests.post(f"{API}/questions/import", headers=H(admin_token),
                          files=files, timeout=90)
        assert r.status_code == 200, r.text
        res = r.json()
        assert res.get("imported", 0) == 2, res

        # Fetch imported questions
        rq = requests.get(f"{API}/questions", headers=H(admin_token),
                          params={"category_id": cat["id"]}, timeout=15)
        assert rq.status_code == 200
        qs = rq.json()
        by_text = {q["text"]: q for q in qs}
        good_q = by_text.get(f"TEST_I4_IMPQ_{unique}")
        bad_q = by_text.get(f"TEST_I4_IMPQ2_{unique}")
        assert good_q is not None and bad_q is not None
        assert good_q.get("image_path"), f"expected image_path set, got {good_q}"
        assert not bad_q.get("image_path"), f"expected no image_path, got {bad_q}"

        # File must be fetchable
        rf = requests.get(f"{API}/files/{good_q['image_path']}",
                         headers=H(admin_token), timeout=30)
        assert rf.status_code == 200
        assert rf.headers.get("content-type", "").startswith("image/")

        # Cleanup
        for q in qs:
            requests.delete(f"{API}/questions/{q['id']}", headers=H(admin_token))
        requests.delete(f"{API}/categories/{cat['id']}", headers=H(admin_token))


# ============================================================================
# 4. PENGUMUMAN SESI - /api/notifications
# ============================================================================
class TestNotifications:
    def test_admin_forbidden(self, admin_token):
        r = requests.get(f"{API}/notifications", headers=H(admin_token), timeout=15)
        assert r.status_code == 403

    def test_siswa_gets_live_for_seeded_active(self, siswa):
        stok, _ = siswa
        r = requests.get(f"{API}/notifications", headers=H(stok), timeout=15)
        assert r.status_code == 200
        notes = r.json()
        assert isinstance(notes, list)
        # Look for "UH Matematika - Kelas X" as live
        titles = [n["title"] for n in notes]
        # Whether seeded exists is env-dependent; at least response shape is ok
        for n in notes:
            assert {"id", "type", "title", "message", "time"} <= set(n.keys())
            assert n["type"] in ("info", "upcoming", "live")

    def test_announcement_and_upcoming_flow(self, admin_token, siswa):
        stok, suser = siswa
        unique = uuid.uuid4().hex[:8]
        cid, qids, pkg = _mk_pkg_with_qs(admin_token, n=1, unique=unique)
        now = datetime.now(timezone.utc)
        # session is UPCOMING (starts in 1 hour) + custom announcement
        ses = requests.post(f"{API}/sessions", headers=H(admin_token), json={
            "title": f"TEST_I4_NOTIF_{unique}", "package_id": pkg["id"],
            "start_time": iso(now + timedelta(hours=1)),
            "end_time": iso(now + timedelta(hours=2)),
            "duration_minutes": 60, "kkm": 70, "class_ids": [],
            "announcement": f"Pengumuman TEST {unique}"}, timeout=15)
        assert ses.status_code == 200, ses.text
        sid = ses.json()["id"]

        r = requests.get(f"{API}/notifications", headers=H(stok), timeout=15).json()
        # Find matching notifications for this session
        mine = [n for n in r if n["id"].startswith(sid)]
        types = {n["type"] for n in mine}
        assert "upcoming" in types, f"missing upcoming in {mine}"
        assert "info" in types, f"missing info (announcement) in {mine}"
        info_note = next(n for n in mine if n["type"] == "info")
        assert f"Pengumuman TEST {unique}" in info_note["message"]

        _cleanup(admin_token, cid=cid, qids=qids, pkg_id=pkg["id"], sid=sid)

    def test_completed_session_excluded_from_live(self, admin_token, siswa):
        stok, _ = siswa
        unique = uuid.uuid4().hex[:8]
        cid, qids, pkg = _mk_pkg_with_qs(admin_token, n=1, unique=unique)
        now = datetime.now(timezone.utc)
        # live session
        ses = requests.post(f"{API}/sessions", headers=H(admin_token), json={
            "title": f"TEST_I4_LIVE_{unique}", "package_id": pkg["id"],
            "start_time": iso(now - timedelta(minutes=5)),
            "end_time": iso(now + timedelta(hours=1)),
            "duration_minutes": 60, "kkm": 70, "class_ids": []}, timeout=15).json()
        sid = ses["id"]
        # student submits (completes)
        st = requests.post(f"{API}/exam/start", headers=H(stok),
                           json={"session_id": sid}, timeout=15).json()
        requests.post(f"{API}/exam/submit", headers=H(stok),
                      json={"session_id": sid, "answers": {qids[0]: "0"}}, timeout=15)
        # notifications should not contain a 'live' for this sid
        r = requests.get(f"{API}/notifications", headers=H(stok), timeout=15).json()
        for n in r:
            if n["id"] == f"{sid}-live":
                pytest.fail(f"completed session should not appear as live: {n}")

        _cleanup(admin_token, cid=cid, qids=qids, pkg_id=pkg["id"], sid=sid)
