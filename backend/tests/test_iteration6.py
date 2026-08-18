"""Iteration 6 tests: Peringkat Angkatan (global leaderboard) + per-package thresholds."""
import os
import time
import pytest
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
API = f"{BASE_URL}/api"

ADMIN = {"email": "hitoria532@gmail.com", "password": "admin123"}
SISWA = {"email": "siswa@sekolah.id", "password": "siswa123"}


def login(cred):
    r = requests.post(f"{API}/auth/login", json=cred, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    return login(ADMIN)


@pytest.fixture(scope="module")
def siswa_token():
    return login(SISWA)


def H(t):
    return {"Authorization": f"Bearer {t}"}


# ---------- Peringkat Angkatan (global) ----------
class TestGlobalLeaderboard:
    def test_admin_can_get_global(self, admin_token):
        r = requests.get(f"{API}/leaderboard/global", headers=H(admin_token), timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "rows" in data
        assert isinstance(data["rows"], list)
        assert len(data["rows"]) >= 1
        row = data["rows"][0]
        for k in ("rank", "student_id", "name", "identifier", "classes", "avg_score", "completed"):
            assert k in row, f"missing {k} in row"
        assert isinstance(row["classes"], list)
        # rows sorted desc by avg
        avgs = [r["avg_score"] for r in data["rows"]]
        assert avgs == sorted(avgs, reverse=True)
        # ranks sequential
        assert [r["rank"] for r in data["rows"]] == list(range(1, len(data["rows"]) + 1))

    def test_siswa_can_get_global(self, siswa_token):
        r = requests.get(f"{API}/leaderboard/global", headers=H(siswa_token), timeout=30)
        assert r.status_code == 200
        assert "rows" in r.json()

    def test_unauth_blocked(self):
        r = requests.get(f"{API}/leaderboard/global", timeout=30)
        assert r.status_code == 401

    def test_ani_siswa_present_with_class(self, admin_token):
        r = requests.get(f"{API}/leaderboard/global", headers=H(admin_token), timeout=30)
        rows = r.json()["rows"]
        ani = next((x for x in rows if x["name"] == "Ani Siswa"), None)
        assert ani is not None
        assert "Kelas X-A" in ani["classes"]

    def test_per_class_still_works(self, admin_token):
        classes = requests.get(f"{API}/classes", headers=H(admin_token), timeout=30).json()
        xa = next(c for c in classes if c["name"] == "Kelas X-A")
        r = requests.get(f"{API}/leaderboard/class/{xa['id']}", headers=H(admin_token), timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["class_name"] == "Kelas X-A"
        assert any(row["name"] == "Ani Siswa" for row in data["rows"])


# ---------- Per-package thresholds ----------
class TestPerPackageThresholds:
    """Create TEST_I6 package with custom thresholds (95/80), session, attempt, check analytics."""

    @pytest.fixture(scope="class")
    def resources(self, admin_token):
        h = H(admin_token)
        created = {}
        # category
        cat = requests.post(f"{API}/categories", headers=h,
                            json={"name": "TEST_I6_Cat"}, timeout=30).json()
        created["cat_id"] = cat["id"]
        # 1 PG question with correct answer index "0"
        q = requests.post(f"{API}/questions", headers=h, json={
            "category_id": cat["id"], "type": "pg", "text": "TEST_I6 Q1",
            "options": ["A", "B"], "correct_answer": "0", "weight": 1.0}, timeout=30).json()
        created["q_id"] = q["id"]
        # Package with easy_min=95, medium_min=80
        pkg = requests.post(f"{API}/packages", headers=h, json={
            "title": "TEST_I6_Paket", "category_id": cat["id"],
            "question_ids": [q["id"]], "scoring_method": "percentage",
            "easy_min": 95, "medium_min": 80}, timeout=30).json()
        created["pkg_id"] = pkg["id"]
        # verify persisted
        got = requests.get(f"{API}/packages/{pkg['id']}", headers=h, timeout=30).json()
        assert got["easy_min"] == 95
        assert got["medium_min"] == 80
        # Session (starts in past, ends in future)
        start = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        end = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        ses = requests.post(f"{API}/sessions", headers=h, json={
            "title": "TEST_I6_Sesi", "package_id": pkg["id"],
            "start_time": start, "end_time": end, "duration_minutes": 60,
            "kkm": 75.0, "class_ids": []}, timeout=30).json()
        created["ses_id"] = ses["id"]

        yield created

        # cleanup
        try:
            requests.delete(f"{API}/sessions/{ses['id']}", headers=h)
            # attempts get orphaned; delete via mongo not possible via API -> ignore
            requests.delete(f"{API}/packages/{pkg['id']}", headers=h)
            requests.delete(f"{API}/questions/{q['id']}", headers=h)
            requests.delete(f"{API}/categories/{cat['id']}", headers=h)
        except Exception:
            pass

    def test_package_saved_with_custom_thresholds(self, admin_token, resources):
        got = requests.get(f"{API}/packages/{resources['pkg_id']}",
                           headers=H(admin_token), timeout=30).json()
        assert got["easy_min"] == 95
        assert got["medium_min"] == 80

    def test_analytics_shows_source_paket_and_labels_by_custom(
            self, admin_token, siswa_token, resources):
        # Student takes exam and submits correct answer (=100% -> should be 'Mudah' by 95/80)
        s = requests.post(f"{API}/exam/start", headers=H(siswa_token),
                          json={"session_id": resources["ses_id"]}, timeout=30)
        assert s.status_code == 200, s.text
        # Grab question order from attempt data to answer correctly
        start_data = s.json()
        # answers dict uses question ids; correct index is "0" (options not shuffled)
        answers = {resources["q_id"]: "0"}
        sub = requests.post(f"{API}/exam/submit", headers=H(siswa_token),
                            json={"session_id": resources["ses_id"], "answers": answers}, timeout=30)
        assert sub.status_code == 200, sub.text
        assert sub.json()["score"] == 100.0

        # analytics
        an = requests.get(f"{API}/analytics/session/{resources['ses_id']}",
                          headers=H(admin_token), timeout=30)
        assert an.status_code == 200, an.text
        data = an.json()
        assert data["thresholds"]["source"] == "paket"
        assert data["thresholds"]["easy_min"] == 95
        assert data["thresholds"]["medium_min"] == 80
        # 100% correct -> Mudah
        item = next(i for i in data["items"] if i["question_id"] == resources["q_id"])
        assert item["percent_correct"] == 100.0
        assert item["difficulty"] == "Mudah"

    def test_analytics_labels_90pct_as_sedang_when_thresholds_95_80(
            self, admin_token, resources):
        """Update the package to have easy_min=95, medium_min=80 already;
        simulate: reduce easy_min so a 100% is 'Sedang'? Instead: set thresholds to 101/80,
        which is invalid. Use a different approach: verify boundary logic by
        temporarily setting easy_min=101 impossible - skip; the previous test already
        proves labeling; here verify 100% would be 'Sedang' if easy_min > 100.
        Simpler: just re-check that with 95/80, pct=100 -> Mudah (already covered).
        This test asserts logic via updating thresholds to 200/80 not allowed
        (server enforces 0-100)? Package endpoint doesn't validate range, so set
        easy_min=101, then 100% -> Sedang."""
        h = H(admin_token)
        pkg = requests.get(f"{API}/packages/{resources['pkg_id']}",
                           headers=h, timeout=30).json()
        pkg_body = {k: pkg[k] for k in ("title", "description", "category_id",
                                         "question_ids", "scoring_method",
                                         "shuffle_questions", "shuffle_options",
                                         "min_score", "rounding")}
        pkg_body["easy_min"] = 101
        pkg_body["medium_min"] = 80
        r = requests.put(f"{API}/packages/{resources['pkg_id']}",
                         headers=h, json=pkg_body, timeout=30)
        assert r.status_code == 200
        an = requests.get(f"{API}/analytics/session/{resources['ses_id']}",
                          headers=h, timeout=30).json()
        assert an["thresholds"]["source"] == "paket"
        item = next(i for i in an["items"] if i["question_id"] == resources["q_id"])
        assert item["percent_correct"] == 100.0
        assert item["difficulty"] == "Sedang", f"expected Sedang, got {item['difficulty']}"

    def test_null_thresholds_use_global(self, admin_token, resources):
        h = H(admin_token)
        pkg = requests.get(f"{API}/packages/{resources['pkg_id']}",
                           headers=h, timeout=30).json()
        pkg_body = {k: pkg[k] for k in ("title", "description", "category_id",
                                         "question_ids", "scoring_method",
                                         "shuffle_questions", "shuffle_options",
                                         "min_score", "rounding")}
        pkg_body["easy_min"] = None
        pkg_body["medium_min"] = None
        r = requests.put(f"{API}/packages/{resources['pkg_id']}",
                         headers=h, json=pkg_body, timeout=30)
        assert r.status_code == 200
        an = requests.get(f"{API}/analytics/session/{resources['ses_id']}",
                          headers=h, timeout=30).json()
        assert an["thresholds"]["source"] == "global"
        # global is 70/40 per prev iteration cleanup
        assert an["thresholds"]["easy_min"] == 70
        assert an["thresholds"]["medium_min"] == 40


# ---------- Regression: global settings unchanged ----------
class TestGlobalSettingsIntact:
    def test_global_still_70_40(self, admin_token):
        r = requests.get(f"{API}/settings/difficulty", headers=H(admin_token), timeout=30)
        assert r.status_code == 200
        assert r.json() == {"easy_min": 70, "medium_min": 40}
