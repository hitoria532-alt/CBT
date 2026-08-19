"""Seed demo accounts + minimal content so the restored app is immediately usable.

Idempotent: re-running will not duplicate users/categories/packages/sessions.
Run: python /app/scripts/seed_demo.py
"""
import os
import sys
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE}/api"
ADMIN = {
    "email": os.environ.get("ADMIN_EMAIL", "admin@example.com"),
    "password": os.environ.get("ADMIN_PASSWORD", "admin123"),
}


def login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=20)
    r.raise_for_status()
    return r.json()["token"]


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


def ensure_user(tok, email, password, name, role, identifier=""):
    users = requests.get(f"{API}/users", headers=H(tok), timeout=20).json()
    for u in users:
        if u["email"] == email:
            return u["id"]
    r = requests.post(f"{API}/users", headers=H(tok), timeout=20, json={
        "email": email, "password": password, "name": name,
        "role": role, "identifier": identifier,
    })
    r.raise_for_status()
    return r.json()["id"]


def ensure_category(tok, name):
    cats = requests.get(f"{API}/categories", headers=H(tok), timeout=20).json()
    for c in cats:
        if c["name"] == name:
            return c["id"]
    r = requests.post(f"{API}/categories", headers=H(tok), timeout=20,
                      json={"name": name, "description": f"Materi {name}"})
    r.raise_for_status()
    return r.json()["id"]


def ensure_questions(tok, cat_id):
    existing = requests.get(f"{API}/questions", headers=H(tok), timeout=20).json()
    if len(existing) >= 3:
        return [q["id"] for q in existing[:3]]
    payloads = [
        {"category_id": cat_id, "type": "pg", "text": "Hasil dari 12 x 8 adalah ...",
         "options": ["86", "96", "108", "112"], "correct_answer": "1", "weight": 1},
        {"category_id": cat_id, "type": "truefalse",
         "text": "Bilangan 17 adalah bilangan prima.", "correct_answer": "true", "weight": 1},
        {"category_id": cat_id, "type": "essay",
         "text": "Jelaskan langkah menghitung luas trapesium.", "weight": 2},
    ]
    ids = []
    for p in payloads:
        r = requests.post(f"{API}/questions", headers=H(tok), timeout=20, json=p)
        r.raise_for_status()
        ids.append(r.json()["id"])
    return ids


def ensure_package(tok, name, qids):
    pkgs = requests.get(f"{API}/packages", headers=H(tok), timeout=20).json()
    for p in pkgs:
        if p.get("title") == name:
            return p["id"]
    r = requests.post(f"{API}/packages", headers=H(tok), timeout=20, json={
        "title": name, "description": "Paket contoh hasil restore repository",
        "category_id": None, "question_ids": qids, "scoring_method": "weighted",
    })
    r.raise_for_status()
    return r.json()["id"]


def ensure_class(tok, name, student_ids):
    classes = requests.get(f"{API}/classes", headers=H(tok), timeout=20).json()
    for c in classes:
        if c["name"] == name:
            return c["id"]
    r = requests.post(f"{API}/classes", headers=H(tok), timeout=20,
                      json={"name": name, "student_ids": student_ids})
    r.raise_for_status()
    return r.json()["id"]


def ensure_session(tok, name, package_id):
    sess = requests.get(f"{API}/sessions", headers=H(tok), timeout=20).json()
    for s in sess:
        if s.get("title") == name:
            return s["id"]
    start = datetime.now(timezone.utc) - timedelta(minutes=5)
    end = datetime.now(timezone.utc) + timedelta(days=7)
    r = requests.post(f"{API}/sessions", headers=H(tok), timeout=20, json={
        "title": name, "package_id": package_id,
        "start_time": start.isoformat(), "end_time": end.isoformat(),
        "duration_minutes": 30, "kkm": 70, "class_ids": [],
        "announcement": "Sesi contoh aktif — silakan dikerjakan.",
    })
    r.raise_for_status()
    return r.json()["id"]


def ensure_attempt(qids, session_id):
    """Have Ani complete the exam once so leaderboard/report features have data."""
    stok = login({"email": "siswa@sekolah.id", "password": "siswa123"})
    done = requests.get(f"{API}/results/me", headers=H(stok), timeout=20).json()
    if any(a.get("session_id") == session_id and a.get("status") != "berlangsung" for a in done):
        return
    r = requests.post(f"{API}/exam/start", headers=H(stok), timeout=20,
                      json={"session_id": session_id})
    r.raise_for_status()
    answers = {qids[0]: "1", qids[1]: "true", qids[2]: "Luas = (a + b) / 2 x tinggi"}
    r = requests.post(f"{API}/exam/submit", headers=H(stok), timeout=30,
                      json={"session_id": session_id, "answers": answers})
    r.raise_for_status()
    print("attempt submitted:", r.json().get("score"))


def main():
    tok = login(ADMIN)
    print("admin login OK")
    ensure_user(tok, "guru@sekolah.id", "guru123", "Guru Contoh", "guru", "G-001")
    s1 = ensure_user(tok, "siswa@sekolah.id", "siswa123", "Ani Siswa", "siswa", "S-001")
    s2 = ensure_user(tok, "siswa2@sekolah.id", "siswa123", "Budi Siswa", "siswa", "S-002")
    print("users ensured")
    cat = ensure_category(tok, "Matematika")
    qids = ensure_questions(tok, cat)
    pkg = ensure_package(tok, "Paket Contoh Matematika", qids)
    ensure_class(tok, "Kelas X-A", [s1, s2])
    sid = ensure_session(tok, "UH Matematika - Kelas X", pkg)
    ensure_attempt(qids, sid)
    print("content ensured: category, 3 questions, package, class, active session")


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        print("FAILED:", e, e.response.text[:400])
        sys.exit(1)
