"""Seed baseline demo content for the CBT app.

Recreates the baseline dataset (categories, question bank, packages, class,
sessions, and one graded attempt) so every module of the app has data to show.
Idempotent: re-running will not duplicate anything.

Run: python /app/scripts/seed_demo.py
"""
import os
import sys
from datetime import datetime, timezone, timedelta

import requests

BASE = os.environ.get("BASE_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE}/api"
ADMIN = {
    "email": os.environ.get("ADMIN_EMAIL", "hitoria532@gmail.com"),
    "password": os.environ.get("ADMIN_PASSWORD", "admin123"),
}

STUDENTS = [
    ("ani@sekolah.id", "Ani Siswa", "S2001", "siswa123"),
    ("budi@sekolah.id", "Budi Siswa", "S2002", "siswa123"),
    ("citra@sekolah.id", "Citra Siswa", "S2003", "siswa123"),
    ("siswa@sekolah.id", "Siswa Sekolah", "S001", "siswa123"),
]
TEACHERS = [("guru@sekolah.id", "Guru Sekolah", "G001", "guru123")]

QUESTIONS = [
    # (category, type, text, options, correct, weight, in_core_package)
    ("Matematika", "pg", "Hasil dari 12 x 8 adalah ...",
     ["86", "96", "108", "112"], "1", 2.0, True),
    ("Matematika", "truefalse", "Bilangan 17 adalah bilangan prima.",
     [], "true", 1.0, True),
    ("Matematika", "essay", "Jelaskan langkah menyelesaikan persamaan linear 2x - 4 = 10.",
     [], None, 3.0, True),
    ("Matematika", "pg", "Nilai x pada persamaan 3x + 6 = 21 adalah ...",
     ["3", "5", "7", "9"], "1", 1.0, False),
    ("Matematika", "pg", "Luas persegi dengan sisi 9 cm adalah ...",
     ["36 cm2", "72 cm2", "81 cm2", "18 cm2"], "2", 1.0, False),
    # contoh soal pilihan ganda 5 opsi (A-E)
    ("Bahasa Indonesia", "pg", "Ibu kota Provinsi Jawa Barat adalah ...",
     ["Bogor", "Bandung", "Bekasi", "Cimahi", "Depok"], "1", 1.0, False),
    ("IPA", "pg", "Organ tubuh manusia yang berfungsi memompa darah adalah ...",
     ["Hati", "Jantung", "Paru-paru", "Ginjal"], "1", 1.0, False),
    ("IPA", "pg", "Proses tumbuhan membuat makanan dengan bantuan cahaya disebut ...",
     ["Respirasi", "Fotosintesis", "Transpirasi", "Fermentasi"], "1", 1.0, False),
    ("IPA", "truefalse", "Air mendidih pada suhu 100 derajat Celsius di tekanan 1 atm.",
     [], "true", 1.0, False),
    ("Bahasa Indonesia", "pg", "Gagasan utama sebuah paragraf disebut ...",
     ["Kalimat penjelas", "Ide pokok", "Konjungsi", "Sinonim"], "1", 1.0, False),
    ("Bahasa Indonesia", "essay", "Buatlah satu paragraf deskriptif tentang lingkungan sekolahmu.",
     [], None, 4.0, False),
]


def H(t):
    return {"Authorization": f"Bearer {t}"}


def login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=20)
    r.raise_for_status()
    return r.json()["token"], r.json()["user"]


def get_or_create(tok, path, payload, match_key):
    for item in requests.get(f"{API}/{path}", headers=H(tok), timeout=20).json():
        if item.get(match_key) == payload[match_key]:
            return item, False
    r = requests.post(f"{API}/{path}", headers=H(tok), json=payload, timeout=30)
    r.raise_for_status()
    return r.json(), True


def main():
    tok, _ = login(ADMIN)
    print("Login admin OK")

    # ---- users
    users = requests.get(f"{API}/users", headers=H(tok), timeout=20).json()
    by_email = {u["email"]: u for u in users}
    for email, name, ident, pw in TEACHERS + STUDENTS:
        role = "guru" if (email, name, ident, pw) in TEACHERS else "siswa"
        if email in by_email:
            print(f"exists   akun: {email}")
            continue
        r = requests.post(f"{API}/users", headers=H(tok), json={
            "email": email, "password": pw, "name": name,
            "role": role, "identifier": ident}, timeout=20)
        r.raise_for_status()
        by_email[email] = r.json()
        print(f"created  akun: {email} ({role})")

    # ---- categories
    cats = {}
    for name in ["Matematika", "IPA", "Bahasa Indonesia"]:
        c, created = get_or_create(tok, "categories",
                                   {"name": name, "description": f"Materi {name}"}, "name")
        cats[name] = c
        print(("created " if created else "exists  ") + f" kategori: {name}")

    # ---- question bank
    existing_q = requests.get(f"{API}/questions", headers=H(tok), timeout=20).json()
    by_text = {q["text"]: q for q in existing_q}
    core_ids, math_extra, ipa_ids, bind_ids = [], [], [], []
    for cat, qtype, text, options, correct, weight, core in QUESTIONS:
        q = by_text.get(text)
        if q is None:
            r = requests.post(f"{API}/questions", headers=H(tok), json={
                "category_id": cats[cat]["id"], "type": qtype, "text": text,
                "options": options, "correct_answer": correct, "weight": weight}, timeout=30)
            r.raise_for_status()
            q = r.json()
            print(f"created  soal: {text[:50]}")
        if core:
            core_ids.append(q["id"])
        elif cat == "Matematika":
            math_extra.append(q["id"])
        elif cat == "IPA":
            ipa_ids.append(q["id"])
        else:
            bind_ids.append(q["id"])

    # ---- class
    student_ids = [by_email[e]["id"] for e, _, _, _ in STUDENTS if e in by_email]
    klass, created = get_or_create(tok, "classes", {
        "name": "Kelas X-A", "description": "Rombel utama demo",
        "student_ids": student_ids}, "name")
    if not created:
        merged = sorted(set(klass.get("student_ids", [])) | set(student_ids))
        requests.put(f"{API}/classes/{klass['id']}", headers=H(tok), json={
            "name": klass["name"], "description": klass.get("description", ""),
            "student_ids": merged}, timeout=20)
    print(("created " if created else "updated ") + f" kelas: Kelas X-A ({len(student_ids)} siswa)")

    # ---- packages
    pkg, _ = get_or_create(tok, "packages", {
        "title": "Paket UH Matematika",
        "description": "Ulangan harian Matematika (penilaian berbobot)",
        "category_id": cats["Matematika"]["id"],
        "question_ids": core_ids,
        "scoring_method": "weighted",
        "shuffle_questions": False, "shuffle_options": False,
        "min_score": 0.0, "rounding": "2desimal", "is_public": True}, "title")
    # keep the core package aligned with the 3 baseline questions / weighted method
    requests.put(f"{API}/packages/{pkg['id']}", headers=H(tok), json={
        "title": pkg["title"], "description": pkg.get("description", ""),
        "category_id": cats["Matematika"]["id"], "question_ids": core_ids,
        "scoring_method": "weighted", "shuffle_questions": False,
        "shuffle_options": False, "min_score": 0.0, "rounding": "2desimal",
        "is_public": True}, timeout=20)
    print(f"ready    paket: {pkg['title']} (berbobot, {len(core_ids)} soal)")

    pkg2, c2 = get_or_create(tok, "packages", {
        "title": "Paket UH IPA (Acak)",
        "description": "Ulangan harian IPA, soal & opsi diacak",
        "category_id": cats["IPA"]["id"], "question_ids": ipa_ids,
        "scoring_method": "percentage", "shuffle_questions": True,
        "shuffle_options": True, "min_score": 0.0, "rounding": "2desimal",
        "is_public": True}, "title")
    print(("created " if c2 else "exists  ") + f" paket: {pkg2['title']}")

    pkg3, c3 = get_or_create(tok, "packages", {
        "title": "Paket Latihan Bahasa Indonesia",
        "description": "Latihan mandiri Bahasa Indonesia",
        "category_id": cats["Bahasa Indonesia"]["id"],
        "question_ids": bind_ids + math_extra,
        "scoring_method": "percentage", "shuffle_questions": False,
        "shuffle_options": False, "min_score": 0.0, "rounding": "bulat",
        "is_public": True}, "title")
    print(("created " if c3 else "exists  ") + f" paket: {pkg3['title']}")

    # ---- sessions
    now = datetime.now(timezone.utc)
    start = (now - timedelta(hours=1)).isoformat()
    end = (now + timedelta(days=21)).isoformat()
    sessions = {}
    for title, package in [("UH Matematika - Kelas X", pkg),
                           ("UH IPA - Kelas X", pkg2),
                           ("Latihan Bahasa Indonesia", pkg3)]:
        s, created = get_or_create(tok, "sessions", {
            "title": title, "package_id": package["id"],
            "start_time": start, "end_time": end,
            "duration_minutes": 45, "kkm": 75.0, "class_ids": [],
            "announcement": "Kerjakan dengan jujur. Pastikan koneksi internet stabil."}, "title")
        sessions[title] = s
        print(("created " if created else "exists  ") + f" sesi: {title}")

    # ---- one graded attempt so results/leaderboard/analytics have data
    qmap = {q["id"]: q for q in requests.get(f"{API}/questions", headers=H(tok), timeout=20).json()}
    for email, expected_essay in [("ani@sekolah.id", 3.0), ("budi@sekolah.id", 1.5)]:
        stok, suser = login({"email": email, "password": "siswa123"})
        mine = requests.get(f"{API}/results/me", headers=H(stok), timeout=20).json()
        if any(a.get("session_id") == sessions["UH Matematika - Kelas X"]["id"] for a in mine):
            print(f"exists   attempt: {email}")
            continue
        sid = sessions["UH Matematika - Kelas X"]["id"]
        st = requests.post(f"{API}/exam/start", headers=H(stok), json={"session_id": sid}, timeout=30)
        st.raise_for_status()
        answers, essay_qid = {}, None
        for q in st.json()["questions"]:
            full = qmap[q["id"]]
            if full["type"] == "essay":
                essay_qid = q["id"]
                answers[q["id"]] = "Pindahkan -4 ke kanan menjadi 2x = 14, lalu bagi 2 sehingga x = 7."
            else:
                answers[q["id"]] = full["correct_answer"]
        sub = requests.post(f"{API}/exam/submit", headers=H(stok),
                            json={"session_id": sid, "answers": answers}, timeout=30)
        sub.raise_for_status()
        attempt = requests.get(f"{API}/results/me", headers=H(stok), timeout=20).json()[0]
        g = requests.post(f"{API}/results/grade/{attempt['id']}", headers=H(tok),
                          json={"scores": {essay_qid: expected_essay}}, timeout=30)
        g.raise_for_status()
        print(f"created  attempt+koreksi: {suser['name']} -> nilai {g.json().get('score')}")

    print("\nSeed selesai.")


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        print("HTTP error:", e.response.status_code, e.response.text[:500])
        sys.exit(1)
