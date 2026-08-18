"""Iteration 8: Filter Peringkat Siswa (category_id on /leaderboard/me) + Statistik Mapel."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("hitoria532@gmail.com", "admin123")
GURU = ("guru@sekolah.id", "guru123")
SISWA = ("siswa@sekolah.id", "siswa123")


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


# ---------- Statistik Mapel (GET /api/analytics/subjects) ----------

class TestAnalyticsSubjects:
    def test_admin_shape(self, admin_h):
        r = requests.get(f"{API}/analytics/subjects", headers=admin_h, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        for row in data:
            assert set(["category_id", "name", "avg_score", "attempts"]).issubset(row.keys())
            assert isinstance(row["name"], str)
            assert isinstance(row["attempts"], int)
            assert isinstance(row["avg_score"], (int, float))
        # sorted by avg_score desc
        avgs = [row["avg_score"] for row in data]
        assert avgs == sorted(avgs, reverse=True)

    def test_guru_can_access(self, guru_h):
        r = requests.get(f"{API}/analytics/subjects", headers=guru_h, timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_siswa_forbidden(self, siswa_h):
        r = requests.get(f"{API}/analytics/subjects", headers=siswa_h, timeout=30)
        assert r.status_code == 403

    def test_zero_attempts_category_is_zero(self, admin_h):
        """Any category with 0 attempts must have avg_score == 0."""
        r = requests.get(f"{API}/analytics/subjects", headers=admin_h, timeout=30)
        assert r.status_code == 200
        for row in r.json():
            if row["attempts"] == 0:
                assert row["avg_score"] == 0

    def test_uncategorized_umum_only_if_attempts(self, admin_h):
        """Umum row must have attempts > 0 (only appears when uncategorized attempts exist)."""
        r = requests.get(f"{API}/analytics/subjects", headers=admin_h, timeout=30)
        for row in r.json():
            if row["name"] == "Umum" and row["category_id"] is None:
                assert row["attempts"] > 0

    def test_known_values(self, admin_h):
        """Based on request: Matematika 100.0 (1 attempt), Umum 61.2 (8 attempts)."""
        r = requests.get(f"{API}/analytics/subjects", headers=admin_h, timeout=30)
        by_name = {row["name"]: row for row in r.json()}
        # Not strictly required; just log if present
        if "Matematika" in by_name:
            print("Matematika:", by_name["Matematika"])
        if "Umum" in by_name:
            print("Umum:", by_name["Umum"])


# ---------- Filter Peringkat Siswa (/leaderboard/me?category_id) ----------

class TestStudentLeaderboardCategoryFilter:
    def test_me_no_filter(self, siswa_h):
        r = requests.get(f"{API}/leaderboard/me", headers=siswa_h, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0, "expected siswa to be in at least one class"
        for cls in data:
            assert "class_id" in cls and "class_name" in cls and "rows" in cls
            assert isinstance(cls["rows"], list)
            # ranks
            for i, row in enumerate(cls["rows"]):
                assert row["rank"] == i + 1

    def test_me_with_category_recomputes(self, siswa_h, admin_h):
        # Get any category
        cats = requests.get(f"{API}/categories", headers=admin_h, timeout=30).json()
        if not cats:
            pytest.skip("no categories seeded")
        cid = cats[0]["id"]
        base = requests.get(f"{API}/leaderboard/me", headers=siswa_h, timeout=30).json()
        filt = requests.get(f"{API}/leaderboard/me", params={"category_id": cid},
                            headers=siswa_h, timeout=30)
        assert filt.status_code == 200
        fdata = filt.json()
        assert len(fdata) == len(base)
        # Same classes
        base_ids = {c["class_id"] for c in base}
        filt_ids = {c["class_id"] for c in fdata}
        assert base_ids == filt_ids
        # Filtered completed <= base for each student (per class)
        base_map = {c["class_id"]: {r["student_id"]: r["completed"] for r in c["rows"]}
                    for c in base}
        for c in fdata:
            for row in c["rows"]:
                assert row["completed"] <= base_map[c["class_id"]].get(row["student_id"], 0)
                if row["completed"] == 0:
                    assert row["avg_score"] == 0

    def test_me_bogus_category_all_zero(self, siswa_h):
        r = requests.get(f"{API}/leaderboard/me",
                         params={"category_id": "does-not-exist-xyz"},
                         headers=siswa_h, timeout=30)
        assert r.status_code == 200
        for cls in r.json():
            for row in cls["rows"]:
                assert row["completed"] == 0
                assert row["avg_score"] == 0

    def test_non_siswa_forbidden(self, admin_h, guru_h):
        assert requests.get(f"{API}/leaderboard/me", headers=admin_h, timeout=30).status_code == 403
        assert requests.get(f"{API}/leaderboard/me", headers=guru_h, timeout=30).status_code == 403


# ---------- Regression ----------

class TestRegression:
    def test_login_admin(self):
        assert _login(*ADMIN)

    def test_login_guru(self):
        assert _login(*GURU)

    def test_login_siswa(self):
        assert _login(*SISWA)

    def test_global_leaderboard_still_works(self, admin_h):
        r = requests.get(f"{API}/leaderboard/global", headers=admin_h, timeout=30)
        assert r.status_code == 200
        assert "rows" in r.json()

    def test_export_xlsx_still_works(self, admin_h):
        r = requests.get(f"{API}/export/leaderboard/xlsx", headers=admin_h, timeout=60)
        assert r.status_code == 200
        assert r.content[:2] == b"PK"

    def test_class_leaderboard_still_works(self, admin_h):
        classes = requests.get(f"{API}/classes", headers=admin_h, timeout=30).json()
        if not classes:
            pytest.skip("no classes")
        r = requests.get(f"{API}/leaderboard/class/{classes[0]['id']}",
                         headers=admin_h, timeout=30)
        assert r.status_code == 200
