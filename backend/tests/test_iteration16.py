"""Iteration 16 — Ujian Susulan (make-up exams).

Guru memberi jendela waktu khusus kepada siswa yang tidak hadir, tanpa mengubah
jadwal sesi asli sehingga kelas lain tidak terganggu.
"""
import os
from datetime import datetime, timezone, timedelta

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "hitoria532@gmail.com", "password": "admin123"}
STUDENT_PASSWORD = "siswa123"


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["token"]


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def ended_session(admin):
    """Sesi yang jadwalnya SUDAH BERAKHIR untuk sebuah kelas berisi siswa."""
    now = datetime.now(timezone.utc)
    classes = requests.get(f"{API}/classes", headers=H(admin), timeout=20).json()
    cls = next((c for c in classes if len(c.get("student_ids") or []) >= 2), None)
    if not cls:
        pytest.skip("Butuh satu kelas dengan minimal 2 siswa")
    pkgs = requests.get(f"{API}/packages", headers=H(admin), timeout=20).json()
    pkg = next((p for p in pkgs if p.get("question_count", 0) > 0), None)
    if not pkg:
        pytest.skip("Butuh paket soal berisi soal")
    r = requests.post(f"{API}/sessions", headers=H(admin), json={
        "title": "[PYTEST] Sesi Susulan", "package_id": pkg["id"],
        "start_time": iso(now - timedelta(days=2)), "end_time": iso(now - timedelta(days=1)),
        "duration_minutes": 30, "kkm": 70, "class_ids": [cls["id"]], "announcement": "",
    }, timeout=20)
    assert r.status_code == 200, r.text
    ses = r.json()
    yield ses
    requests.delete(f"{API}/sessions/{ses['id']}", headers=H(admin), timeout=20)


@pytest.fixture(scope="module")
def two_absentees(admin, ended_session):
    r = requests.get(f"{API}/makeups/absentees/{ended_session['id']}", headers=H(admin), timeout=20)
    assert r.status_code == 200, r.text
    items = r.json()["absentees"]
    if len(items) < 2:
        pytest.skip("Butuh minimal 2 siswa yang belum mengerjakan")
    return items[0], items[1]


class TestAbsenteeDetection:
    def test_absentees_listed_with_hint(self, admin, ended_session):
        r = requests.get(f"{API}/makeups/absentees/{ended_session['id']}", headers=H(admin), timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert data["session"]["id"] == ended_session["id"]
        assert len(data["absentees"]) >= 2
        for a in data["absentees"]:
            assert a["reason_hint"]
            assert a["makeup"] is None

    def test_absentees_unknown_session_404(self, admin):
        r = requests.get(f"{API}/makeups/absentees/tidak-ada", headers=H(admin), timeout=20)
        assert r.status_code == 404


class TestMakeupValidation:
    def test_reject_end_before_start(self, admin, ended_session, two_absentees):
        now = datetime.now(timezone.utc)
        r = requests.post(f"{API}/makeups", headers=H(admin), json={
            "session_id": ended_session["id"], "student_ids": [two_absentees[0]["id"]],
            "start_time": iso(now), "end_time": iso(now - timedelta(hours=1))}, timeout=20)
        assert r.status_code == 400

    def test_reject_empty_students(self, admin, ended_session):
        now = datetime.now(timezone.utc)
        r = requests.post(f"{API}/makeups", headers=H(admin), json={
            "session_id": ended_session["id"], "student_ids": [],
            "start_time": iso(now), "end_time": iso(now + timedelta(hours=1))}, timeout=20)
        assert r.status_code == 400

    def test_reject_unknown_session(self, admin, two_absentees):
        now = datetime.now(timezone.utc)
        r = requests.post(f"{API}/makeups", headers=H(admin), json={
            "session_id": "tidak-ada", "student_ids": [two_absentees[0]["id"]],
            "start_time": iso(now), "end_time": iso(now + timedelta(hours=1))}, timeout=20)
        assert r.status_code == 404

    def test_reject_zero_duration(self, admin, ended_session, two_absentees):
        now = datetime.now(timezone.utc)
        r = requests.post(f"{API}/makeups", headers=H(admin), json={
            "session_id": ended_session["id"], "student_ids": [two_absentees[0]["id"]],
            "start_time": iso(now), "end_time": iso(now + timedelta(hours=1)),
            "duration_minutes": 0}, timeout=20)
        assert r.status_code == 400


class TestMakeupLifecycle:
    def test_full_flow(self, admin, ended_session, two_absentees):
        now = datetime.now(timezone.utc)
        target, other = two_absentees
        sid = ended_session["id"]

        # --- jadwalkan susulan aktif untuk target
        r = requests.post(f"{API}/makeups", headers=H(admin), json={
            "session_id": sid, "student_ids": [target["id"]],
            "start_time": iso(now - timedelta(minutes=5)),
            "end_time": iso(now + timedelta(hours=2)),
            "duration_minutes": 15, "reason": "Sakit"}, timeout=20)
        assert r.status_code == 200, r.text
        assert r.json()["created"] == 1

        mks = requests.get(f"{API}/makeups", headers=H(admin),
                           params={"session_id": sid}, timeout=20).json()
        mk = next(m for m in mks if m["student_id"] == target["id"])
        assert mk["status"] == "berlangsung"
        assert mk["effective_duration"] == 15
        assert mk["reason"] == "Sakit"
        assert mk["session_title"] == ended_session["title"]

        # --- badge count untuk guru
        summary = requests.get(f"{API}/makeups/summary", headers=H(admin), timeout=20).json()
        assert summary.get(sid) == 1
        adm_sessions = requests.get(f"{API}/sessions", headers=H(admin), timeout=20).json()
        assert next(s for s in adm_sessions if s["id"] == sid)["makeup_count"] == 1

        # --- sisi siswa target
        stok = _login({"email": target["email"], "password": STUDENT_PASSWORD})
        s = next(x for x in requests.get(f"{API}/sessions", headers=H(stok), timeout=20).json()
                 if x["id"] == sid)
        assert s["status"] == "berlangsung"          # dibuka kembali khusus untuk dia
        assert s["active_window"] == "susulan"
        assert s["effective_duration"] == 15
        assert s["makeup"]["status"] == "berlangsung"

        notes = requests.get(f"{API}/notifications", headers=H(stok), timeout=20).json()
        assert any("susulan" in n["message"].lower() for n in notes)

        start = requests.post(f"{API}/exam/start", headers=H(stok),
                              json={"session_id": sid}, timeout=20)
        assert start.status_code == 200, start.text
        data = start.json()
        assert data["is_makeup"] is True
        assert data["session"]["duration_minutes"] == 15
        assert data["session"]["end_time"] == mk["end_time"]
        assert len(data["questions"]) > 0

        answers = {q["id"]: ("0" if q["type"] == "pg"
                             else "true" if q["type"] == "truefalse" else "Esai")
                   for q in data["questions"]}
        sub = requests.post(f"{API}/exam/submit", headers=H(stok),
                            json={"session_id": sid, "answers": answers}, timeout=20)
        assert sub.status_code == 200, sub.text

        # --- siswa lain tanpa susulan tetap terblokir
        otok = _login({"email": other["email"], "password": STUDENT_PASSWORD})
        os_ = next(x for x in requests.get(f"{API}/sessions", headers=H(otok), timeout=20).json()
                   if x["id"] == sid)
        assert os_["status"] == "selesai"
        assert os_.get("makeup") is None
        blocked = requests.post(f"{API}/exam/start", headers=H(otok),
                                json={"session_id": sid}, timeout=20)
        assert blocked.status_code == 400
        assert "berakhir" in blocked.text.lower()

        # --- hasil ditandai susulan
        res = requests.get(f"{API}/results/session/{sid}", headers=H(admin), timeout=20).json()
        att = next(a for a in res["attempts"] if a["student_id"] == target["id"])
        assert att["is_makeup"] is True
        assert att["makeup_id"] == mk["id"]

        mk_after = next(m for m in requests.get(f"{API}/makeups", headers=H(admin),
                                                params={"session_id": sid}, timeout=20).json()
                        if m["student_id"] == target["id"])
        assert mk_after["status"] == "sudah_dikerjakan"

        # target hilang dari daftar absen & tak bisa mengulang
        abs_now = requests.get(f"{API}/makeups/absentees/{sid}", headers=H(admin), timeout=20).json()["absentees"]
        assert all(a["id"] != target["id"] for a in abs_now)
        again = requests.post(f"{API}/exam/start", headers=H(stok), json={"session_id": sid}, timeout=20)
        assert again.status_code == 400

    def test_future_window_blocks_with_specific_message(self, admin, ended_session, two_absentees):
        now = datetime.now(timezone.utc)
        other = two_absentees[1]
        sid = ended_session["id"]
        r = requests.post(f"{API}/makeups", headers=H(admin), json={
            "session_id": sid, "student_ids": [other["id"]],
            "start_time": iso(now + timedelta(days=1)),
            "end_time": iso(now + timedelta(days=1, hours=2)),
            "reason": "Izin keluarga"}, timeout=20)
        assert r.status_code == 200, r.text

        otok = _login({"email": other["email"], "password": STUDENT_PASSWORD})
        s = next(x for x in requests.get(f"{API}/sessions", headers=H(otok), timeout=20).json()
                 if x["id"] == sid)
        assert s["status"] == "akan_datang"
        assert s["makeup"]["duration_minutes"] == 30  # kosong = ikut durasi sesi

        early = requests.post(f"{API}/exam/start", headers=H(otok),
                              json={"session_id": sid}, timeout=20)
        assert early.status_code == 400
        assert "susulan" in early.text.lower()

    def test_reschedule_then_upsert_then_delete(self, admin, ended_session, two_absentees):
        now = datetime.now(timezone.utc)
        other = two_absentees[1]
        sid = ended_session["id"]
        mk = next(m for m in requests.get(f"{API}/makeups", headers=H(admin),
                                          params={"session_id": sid}, timeout=20).json()
                  if m["student_id"] == other["id"])

        up = requests.put(f"{API}/makeups/{mk['id']}", headers=H(admin), json={
            "start_time": iso(now - timedelta(minutes=1)),
            "end_time": iso(now + timedelta(hours=1)),
            "duration_minutes": 20, "reason": "Dijadwalkan ulang"}, timeout=20)
        assert up.status_code == 200, up.text
        assert up.json()["status"] == "berlangsung"

        otok = _login({"email": other["email"], "password": STUDENT_PASSWORD})
        st = requests.post(f"{API}/exam/start", headers=H(otok), json={"session_id": sid}, timeout=20)
        assert st.status_code == 200, st.text
        assert st.json()["session"]["duration_minutes"] == 20

        # jadwalkan lagi siswa yang sama -> update, bukan duplikat
        dup = requests.post(f"{API}/makeups", headers=H(admin), json={
            "session_id": sid, "student_ids": [other["id"]],
            "start_time": iso(now - timedelta(minutes=1)),
            "end_time": iso(now + timedelta(hours=3))}, timeout=20)
        assert dup.json() == {"created": 0, "updated": 1, "skipped": []}

        me = requests.get(f"{API}/makeups/me", headers=H(otok), timeout=20)
        assert me.status_code == 200
        # siswa bisa punya susulan di sesi lain juga — cukup pastikan sesi ini ada
        mine = [m for m in me.json() if m["session_id"] == sid]
        assert len(mine) == 1
        assert mine[0]["student_id"] == other["id"]

        d = requests.delete(f"{API}/makeups/{mk['id']}", headers=H(admin), timeout=20)
        assert d.status_code == 200
        assert requests.delete(f"{API}/makeups/{mk['id']}", headers=H(admin), timeout=20).status_code == 404

    def test_update_unknown_makeup_404(self, admin):
        now = datetime.now(timezone.utc)
        r = requests.put(f"{API}/makeups/tidak-ada", headers=H(admin), json={
            "start_time": iso(now), "end_time": iso(now + timedelta(hours=1))}, timeout=20)
        assert r.status_code == 404


class TestMakeupAuthorization:
    def test_student_cannot_list_or_create(self, admin, ended_session, two_absentees):
        now = datetime.now(timezone.utc)
        target = two_absentees[0]
        stok = _login({"email": target["email"], "password": STUDENT_PASSWORD})
        assert requests.get(f"{API}/makeups", headers=H(stok), timeout=20).status_code == 403
        assert requests.get(f"{API}/makeups/absentees/{ended_session['id']}",
                            headers=H(stok), timeout=20).status_code == 403
        r = requests.post(f"{API}/makeups", headers=H(stok), json={
            "session_id": ended_session["id"], "student_ids": [target["id"]],
            "start_time": iso(now), "end_time": iso(now + timedelta(hours=1))}, timeout=20)
        assert r.status_code == 403

    def test_makeups_me_forbidden_for_admin(self, admin):
        assert requests.get(f"{API}/makeups/me", headers=H(admin), timeout=20).status_code == 403

    def test_unauthenticated_blocked(self):
        assert requests.get(f"{API}/makeups", timeout=20).status_code in (401, 403)


class TestMakeupCascade:
    def test_deleting_session_removes_makeups(self, admin):
        """Sesi terpisah agar tidak mengganggu fixture modul."""
        now = datetime.now(timezone.utc)
        classes = requests.get(f"{API}/classes", headers=H(admin), timeout=20).json()
        cls = next((c for c in classes if c.get("student_ids")), None)
        pkgs = requests.get(f"{API}/packages", headers=H(admin), timeout=20).json()
        pkg = next((p for p in pkgs if p.get("question_count", 0) > 0), None)
        if not cls or not pkg:
            pytest.skip("Butuh kelas berisi siswa dan paket soal")
        ses = requests.post(f"{API}/sessions", headers=H(admin), json={
            "title": "[PYTEST] Cascade Susulan", "package_id": pkg["id"],
            "start_time": iso(now - timedelta(days=2)), "end_time": iso(now - timedelta(days=1)),
            "duration_minutes": 30, "kkm": 70, "class_ids": [cls["id"]],
        }, timeout=20).json()
        student_id = cls["student_ids"][0]
        r = requests.post(f"{API}/makeups", headers=H(admin), json={
            "session_id": ses["id"], "student_ids": [student_id],
            "start_time": iso(now), "end_time": iso(now + timedelta(hours=1))}, timeout=20)
        assert r.status_code == 200, r.text
        assert len(requests.get(f"{API}/makeups", headers=H(admin),
                                params={"session_id": ses["id"]}, timeout=20).json()) == 1

        requests.delete(f"{API}/sessions/{ses['id']}", headers=H(admin), timeout=20)
        assert requests.get(f"{API}/makeups", headers=H(admin),
                            params={"session_id": ses["id"]}, timeout=20).json() == []

    def test_deleting_session_removes_attempts(self, admin):
        """Tanpa cascade ini, attempt yatim terus mencemari /api/dashboard/stats."""
        now = datetime.now(timezone.utc)
        classes = requests.get(f"{API}/classes", headers=H(admin), timeout=20).json()
        cls = next((c for c in classes if c.get("student_ids")), None)
        pkgs = requests.get(f"{API}/packages", headers=H(admin), timeout=20).json()
        pkg = next((p for p in pkgs if p.get("question_count", 0) > 0), None)
        if not cls or not pkg:
            pytest.skip("Butuh kelas berisi siswa dan paket soal")
        ses = requests.post(f"{API}/sessions", headers=H(admin), json={
            "title": "[PYTEST] Cascade Attempt", "package_id": pkg["id"],
            "start_time": iso(now - timedelta(minutes=10)),
            "end_time": iso(now + timedelta(hours=1)),
            "duration_minutes": 30, "kkm": 70, "class_ids": [cls["id"]],
        }, timeout=20).json()

        absentees = requests.get(f"{API}/makeups/absentees/{ses['id']}",
                                 headers=H(admin), timeout=20).json()["absentees"]
        stud = absentees[0]
        stok = _login({"email": stud["email"], "password": STUDENT_PASSWORD})
        start = requests.post(f"{API}/exam/start", headers=H(stok),
                              json={"session_id": ses["id"]}, timeout=20)
        assert start.status_code == 200, start.text
        answers = {q["id"]: "0" for q in start.json()["questions"]}
        requests.post(f"{API}/exam/submit", headers=H(stok),
                      json={"session_id": ses["id"], "answers": answers}, timeout=20)
        before = requests.get(f"{API}/results/session/{ses['id']}", headers=H(admin), timeout=20).json()
        assert len(before["attempts"]) == 1

        d = requests.delete(f"{API}/sessions/{ses['id']}", headers=H(admin), timeout=20)
        assert d.status_code == 200
        assert d.json()["attempts_deleted"] == 1
        after = requests.get(f"{API}/results/session/{ses['id']}", headers=H(admin), timeout=20).json()
        assert after["attempts"] == []
