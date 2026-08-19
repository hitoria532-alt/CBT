"""Iteration 9: Rapor Siswa PDF + Bank Soal Publik."""
import os
import uuid
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


@pytest.fixture(scope="module")
def siswa_id(siswa_h):
    r = requests.get(f"{API}/auth/me", headers=siswa_h, timeout=30)
    assert r.status_code == 200
    return r.json()["id"]


# --------- Rapor Siswa PDF ---------

class TestReportPDF:
    def test_admin_downloads_siswa_report(self, admin_h, siswa_id):
        r = requests.get(f"{API}/report/student/{siswa_id}/pdf", headers=admin_h, timeout=60)
        assert r.status_code == 200
        assert "application/pdf" in r.headers.get("content-type", "").lower()
        assert r.content[:4] == b"%PDF"

    def test_guru_downloads_siswa_report(self, guru_h, siswa_id):
        r = requests.get(f"{API}/report/student/{siswa_id}/pdf", headers=guru_h, timeout=60)
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"

    def test_siswa_downloads_own_by_id(self, siswa_h, siswa_id):
        r = requests.get(f"{API}/report/student/{siswa_id}/pdf", headers=siswa_h, timeout=60)
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"

    def test_siswa_downloads_me_alias(self, siswa_h):
        r = requests.get(f"{API}/report/student/me/pdf", headers=siswa_h, timeout=60)
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"

    def test_siswa_forbidden_other(self, siswa_h, admin_h):
        # Get another siswa id (or any user with different id)
        users = requests.get(f"{API}/users", headers=admin_h, timeout=30).json()
        other = next((u for u in users if u["role"] == "siswa"
                      and u["email"] != "siswa@sekolah.id"), None)
        if not other:
            # create one
            payload = {"email": f"TEST_other_{uuid.uuid4().hex[:6]}@t.id",
                       "password": "pass1234", "name": "TEST Other",
                       "role": "siswa"}
            cr = requests.post(f"{API}/users", json=payload, headers=admin_h, timeout=30)
            assert cr.status_code in (200, 201)
            other = cr.json()
        r = requests.get(f"{API}/report/student/{other['id']}/pdf",
                         headers=siswa_h, timeout=30)
        assert r.status_code == 403


# --------- Bank Soal Publik ---------

@pytest.fixture(scope="module")
def guru_b(admin_h):
    """Create a second guru account for public-package sharing test."""
    email = f"TEST_guruB_{uuid.uuid4().hex[:6]}@t.id"
    payload = {"email": email, "password": "pass1234",
               "name": "TEST Guru B", "role": "guru"}
    r = requests.post(f"{API}/users", json=payload, headers=admin_h, timeout=30)
    assert r.status_code in (200, 201), r.text
    uid = r.json()["id"]
    token = _login(email, "pass1234")
    yield {"headers": {"Authorization": f"Bearer {token}"}, "id": uid, "email": email}
    # cleanup
    requests.delete(f"{API}/users/{uid}", headers=admin_h, timeout=30)


@pytest.fixture(scope="module")
def created_packages(guru_h, admin_h):
    """Guru A creates one public and one private package."""
    ids = []

    def mk(is_public, title):
        payload = {"title": title, "is_public": is_public, "question_ids": []}
        r = requests.post(f"{API}/packages", json=payload, headers=guru_h, timeout=30)
        assert r.status_code in (200, 201), r.text
        ids.append(r.json()["id"])
        return r.json()

    pub = mk(True, f"TEST_pub_{uuid.uuid4().hex[:6]}")
    priv = mk(False, f"TEST_priv_{uuid.uuid4().hex[:6]}")
    yield {"public": pub, "private": priv}
    for pid in ids:
        requests.delete(f"{API}/packages/{pid}", headers=admin_h, timeout=30)


class TestPublicPackages:
    def test_created_by_and_is_public_persist(self, guru_h, created_packages):
        pid = created_packages["public"]["id"]
        # via list (guru A sees own)
        r = requests.get(f"{API}/packages", headers=guru_h, timeout=30)
        assert r.status_code == 200
        pkgs = {p["id"]: p for p in r.json()}
        assert pid in pkgs
        p = pkgs[pid]
        assert p["is_public"] is True
        assert p.get("created_by")  # not null
        assert p["is_owner"] is True
        assert "owner_name" in p

    def test_guru_b_sees_public_not_private(self, guru_b, created_packages):
        r = requests.get(f"{API}/packages", headers=guru_b["headers"], timeout=30)
        assert r.status_code == 200
        ids = {p["id"]: p for p in r.json()}
        pub_id = created_packages["public"]["id"]
        priv_id = created_packages["private"]["id"]
        assert pub_id in ids, "guru B should see public package"
        assert priv_id not in ids, "guru B should NOT see private package of guru A"
        # Non-owner marker
        p = ids[pub_id]
        assert p["is_owner"] is False
        assert p.get("owner_name")

    def test_guru_b_cannot_edit_public_package(self, guru_b, created_packages):
        pid = created_packages["public"]["id"]
        r = requests.put(f"{API}/packages/{pid}",
                         json={"title": "hacked", "is_public": True, "question_ids": []},
                         headers=guru_b["headers"], timeout=30)
        assert r.status_code == 403

    def test_guru_b_cannot_delete_public_package(self, guru_b, created_packages):
        pid = created_packages["public"]["id"]
        r = requests.delete(f"{API}/packages/{pid}",
                            headers=guru_b["headers"], timeout=30)
        assert r.status_code == 403

    def test_owner_can_edit(self, guru_h, created_packages):
        pid = created_packages["public"]["id"]
        r = requests.put(f"{API}/packages/{pid}",
                         json={"title": "TEST_pub_renamed", "is_public": True, "question_ids": []},
                         headers=guru_h, timeout=30)
        assert r.status_code == 200

    def test_admin_sees_all(self, admin_h, created_packages):
        r = requests.get(f"{API}/packages", headers=admin_h, timeout=30)
        assert r.status_code == 200
        ids = {p["id"] for p in r.json()}
        assert created_packages["public"]["id"] in ids
        assert created_packages["private"]["id"] in ids

    def test_legacy_null_created_by_visible_to_guru_b(self, guru_b, admin_h):
        """Legacy packages (created_by null) should be visible to any guru."""
        r_admin = requests.get(f"{API}/packages", headers=admin_h, timeout=30).json()
        legacy = [p for p in r_admin if not p.get("created_by")]
        if not legacy:
            pytest.skip("no legacy packages present")
        rb = requests.get(f"{API}/packages", headers=guru_b["headers"], timeout=30).json()
        rb_ids = {p["id"] for p in rb}
        for p in legacy:
            assert p["id"] in rb_ids, f"legacy pkg {p['name']} not visible to guru B"


# --------- Regression ---------

class TestRegression:
    def test_login_all_roles(self):
        assert _login(*ADMIN)
        assert _login(*GURU)
        assert _login(*SISWA)

    def test_categories_ok(self, admin_h):
        r = requests.get(f"{API}/categories", headers=admin_h, timeout=30)
        assert r.status_code == 200

    def test_global_leaderboard(self, admin_h):
        r = requests.get(f"{API}/leaderboard/global", headers=admin_h, timeout=30)
        assert r.status_code == 200
