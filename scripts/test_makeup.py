"""Uji alur inti fitur Ujian Susulan (end-to-end lewat HTTP API)."""
import os
import sys
from datetime import datetime, timezone, timedelta

import requests

BASE = os.environ.get("BASE_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE}/api"
ok, fail = 0, 0


def check(label, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {extra}")


def login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    r.raise_for_status()
    return r.json()["token"]


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def main():
    now = datetime.now(timezone.utc)
    admin = login("hitoria532@gmail.com", "admin123")

    # ---------- persiapan: sesi yang SUDAH BERAKHIR untuk Kelas X-A
    classes = requests.get(f"{API}/classes", headers=H(admin), timeout=30).json()
    cls = next((c for c in classes if c["student_ids"]), classes[0])
    pkgs = requests.get(f"{API}/packages", headers=H(admin), timeout=30).json()
    pkg = next(p for p in pkgs if p["question_count"] > 0 and not p.get("has_essay", False))
    # pilih paket tanpa esai bila ada agar nilai langsung keluar
    for p in pkgs:
        if p["question_count"] > 0:
            pkg = p
            break

    body = {
        "title": "[TES] Sesi Susulan Otomatis", "package_id": pkg["id"],
        "start_time": iso(now - timedelta(days=2)), "end_time": iso(now - timedelta(days=1)),
        "duration_minutes": 30, "kkm": 70, "class_ids": [cls["id"]],
        "announcement": "",
    }
    ses = requests.post(f"{API}/sessions", headers=H(admin), json=body, timeout=30).json()
    print(f"\n[setup] sesi '{ses['title']}' (sudah berakhir) kelas={cls['name']} paket={pkg['title']}")

    try:
        # ---------- 1. deteksi siswa absen
        r = requests.get(f"{API}/makeups/absentees/{ses['id']}", headers=H(admin), timeout=30)
        check("GET /makeups/absentees 200", r.status_code == 200, r.text[:200])
        abs_list = r.json()["absentees"]
        check("absentees terdeteksi (>=2 siswa)", len(abs_list) >= 2, f"dapat {len(abs_list)}")
        check("absentee punya reason_hint", all(a["reason_hint"] for a in abs_list))
        check("absentee belum punya jadwal susulan", all(a["makeup"] is None for a in abs_list))
        target = abs_list[0]
        other = abs_list[1]
        print(f"[setup] target susulan = {target['name']}, kontrol = {other['name']}")

        # ---------- 2. validasi input
        bad = requests.post(f"{API}/makeups", headers=H(admin), json={
            "session_id": ses["id"], "student_ids": [target["id"]],
            "start_time": iso(now), "end_time": iso(now - timedelta(hours=1))}, timeout=30)
        check("tolak end_time <= start_time (400)", bad.status_code == 400, bad.text[:150])
        bad2 = requests.post(f"{API}/makeups", headers=H(admin), json={
            "session_id": ses["id"], "student_ids": [],
            "start_time": iso(now), "end_time": iso(now + timedelta(hours=1))}, timeout=30)
        check("tolak daftar siswa kosong (400)", bad2.status_code == 400, bad2.text[:150])

        # ---------- 3. jadwalkan susulan (jendela aktif sekarang)
        r = requests.post(f"{API}/makeups", headers=H(admin), json={
            "session_id": ses["id"], "student_ids": [target["id"]],
            "start_time": iso(now - timedelta(minutes=5)),
            "end_time": iso(now + timedelta(hours=2)),
            "duration_minutes": 15, "reason": "Sakit, ada surat dokter"}, timeout=30)
        check("POST /makeups 200", r.status_code == 200, r.text[:200])
        check("1 susulan dibuat", r.json().get("created") == 1, r.text[:150])

        mks = requests.get(f"{API}/makeups", headers=H(admin), params={"session_id": ses["id"]}, timeout=30).json()
        check("GET /makeups mengembalikan 1 jadwal", len(mks) == 1, str(len(mks)))
        mk = mks[0]
        check("status susulan = berlangsung", mk["status"] == "berlangsung", mk["status"])
        check("durasi override = 15", mk["effective_duration"] == 15, str(mk["effective_duration"]))
        check("judul sesi ter-enrich", mk["session_title"] == ses["title"], mk["session_title"])
        check("alasan tersimpan", mk["reason"] == "Sakit, ada surat dokter", mk["reason"])

        summ = requests.get(f"{API}/makeups/summary", headers=H(admin), timeout=30).json()
        check("summary hitung 1 susulan untuk sesi", summ.get(ses["id"]) == 1, str(summ.get(ses["id"])))

        adm_ses = requests.get(f"{API}/sessions", headers=H(admin), timeout=30).json()
        mine = next(s for s in adm_ses if s["id"] == ses["id"])
        check("sesi admin punya makeup_count=1", mine.get("makeup_count") == 1, str(mine.get("makeup_count")))

        # absentee sekarang menampilkan jadwalnya
        abs2 = requests.get(f"{API}/makeups/absentees/{ses['id']}", headers=H(admin), timeout=30).json()["absentees"]
        tgt2 = next(a for a in abs2 if a["id"] == target["id"])
        check("absentee target menampilkan jadwal susulan", tgt2["makeup"] is not None)

        # ---------- 4. sisi siswa: siswa TARGET bisa mengerjakan
        stok = login(target["email"], "siswa123")
        slist = requests.get(f"{API}/sessions", headers=H(stok), timeout=30).json()
        s = next((x for x in slist if x["id"] == ses["id"]), None)
        check("siswa target melihat sesi", s is not None)
        check("status sesi jadi 'berlangsung' bagi target", s and s["status"] == "berlangsung",
              s["status"] if s else "-")
        check("payload berisi objek makeup", bool(s and s.get("makeup")))
        check("active_window = susulan", s and s.get("active_window") == "susulan", str(s.get("active_window")))
        check("effective_duration = 15", s and s.get("effective_duration") == 15, str(s.get("effective_duration")))

        notif = requests.get(f"{API}/notifications", headers=H(stok), timeout=30).json()
        check("notifikasi susulan muncul", any("susulan" in n["message"].lower() for n in notif),
              str([n["message"][:40] for n in notif])[:200])

        st = requests.post(f"{API}/exam/start", headers=H(stok), json={"session_id": ses["id"]}, timeout=30)
        check("siswa target bisa /exam/start 200", st.status_code == 200, st.text[:250])
        data = st.json()
        check("exam/start tandai is_makeup", data.get("is_makeup") is True)
        check("durasi ujian = 15 (override susulan)", data["session"]["duration_minutes"] == 15,
              str(data["session"]["duration_minutes"]))
        check("batas waktu = akhir jendela susulan", data["session"]["end_time"] == mk["end_time"],
              f"{data['session']['end_time']} vs {mk['end_time']}")
        check("soal terkirim", len(data["questions"]) > 0, str(len(data["questions"])))

        # jawab semua soal PG/TF dengan opsi pertama
        answers = {q["id"]: ("0" if q["type"] == "pg" else "true" if q["type"] == "truefalse" else "Jawaban esai tes")
                   for q in data["questions"]}
        sub = requests.post(f"{API}/exam/submit", headers=H(stok),
                            json={"session_id": ses["id"], "answers": answers}, timeout=30)
        check("siswa target bisa submit 200", sub.status_code == 200, sub.text[:250])

        # ---------- 5. siswa LAIN (tanpa susulan) tetap terblokir
        otok = login(other["email"], "siswa123")
        olist = requests.get(f"{API}/sessions", headers=H(otok), timeout=30).json()
        os_ = next((x for x in olist if x["id"] == ses["id"]), None)
        check("siswa lain melihat sesi status 'selesai'", os_ and os_["status"] == "selesai",
              os_["status"] if os_ else "-")
        check("siswa lain tidak punya objek makeup", os_ is not None and os_.get("makeup") is None)
        blocked = requests.post(f"{API}/exam/start", headers=H(otok), json={"session_id": ses["id"]}, timeout=30)
        check("siswa lain DITOLAK /exam/start (400)", blocked.status_code == 400, blocked.text[:200])
        check("pesan tolak = sesi berakhir", "berakhir" in blocked.text.lower(), blocked.text[:150])

        # ---------- 6. hasil menandai susulan
        res = requests.get(f"{API}/results/session/{ses['id']}", headers=H(admin), timeout=30).json()
        att = next((a for a in res["attempts"] if a["student_id"] == target["id"]), None)
        check("hasil memuat attempt susulan", att is not None)
        check("attempt bertanda is_makeup", att and att.get("is_makeup") is True)
        check("attempt menyimpan makeup_id", att and att.get("makeup_id") == mk["id"])

        mk_after = requests.get(f"{API}/makeups", headers=H(admin),
                                params={"session_id": ses["id"]}, timeout=30).json()[0]
        check("status susulan jadi 'sudah_dikerjakan'", mk_after["status"] == "sudah_dikerjakan", mk_after["status"])

        # target tidak lagi muncul sebagai absen
        abs3 = requests.get(f"{API}/makeups/absentees/{ses['id']}", headers=H(admin), timeout=30).json()["absentees"]
        check("target hilang dari daftar absen", all(a["id"] != target["id"] for a in abs3))

        # mengulang lagi ditolak
        again = requests.post(f"{API}/exam/start", headers=H(stok), json={"session_id": ses["id"]}, timeout=30)
        check("target tidak bisa mengerjakan 2x (400)", again.status_code == 400, again.text[:200])

        # ---------- 7. jadwal susulan MASA DEPAN memblokir dengan pesan khusus
        r = requests.post(f"{API}/makeups", headers=H(admin), json={
            "session_id": ses["id"], "student_ids": [other["id"]],
            "start_time": iso(now + timedelta(days=1)), "end_time": iso(now + timedelta(days=1, hours=2)),
            "reason": "Izin keluarga"}, timeout=30)
        check("jadwalkan susulan mendatang 200", r.status_code == 200, r.text[:200])
        f_list = requests.get(f"{API}/sessions", headers=H(otok), timeout=30).json()
        fs = next(x for x in f_list if x["id"] == ses["id"])
        check("status bagi siswa jadi 'akan_datang'", fs["status"] == "akan_datang", fs["status"])
        check("durasi susulan mendatang ikut sesi (30)",
              fs["makeup"]["duration_minutes"] == 30, str(fs["makeup"]["duration_minutes"]))
        early = requests.post(f"{API}/exam/start", headers=H(otok), json={"session_id": ses["id"]}, timeout=30)
        check("mulai sebelum jadwal ditolak (400)", early.status_code == 400, early.text[:200])
        check("pesan = susulan belum dimulai", "susulan" in early.text.lower(), early.text[:200])

        # ---------- 8. ubah jadwal (reschedule) & upsert tidak menduplikasi
        mk_other = next(m for m in requests.get(f"{API}/makeups", headers=H(admin),
                                                params={"session_id": ses["id"]}, timeout=30).json()
                        if m["student_id"] == other["id"])
        up = requests.put(f"{API}/makeups/{mk_other['id']}", headers=H(admin), json={
            "start_time": iso(now - timedelta(minutes=1)), "end_time": iso(now + timedelta(hours=1)),
            "duration_minutes": 20, "reason": "Dijadwalkan ulang"}, timeout=30)
        check("PUT /makeups 200", up.status_code == 200, up.text[:200])
        check("status setelah reschedule = berlangsung", up.json()["status"] == "berlangsung", up.json()["status"])
        now_start = requests.post(f"{API}/exam/start", headers=H(otok), json={"session_id": ses["id"]}, timeout=30)
        check("siswa lain bisa mulai setelah reschedule", now_start.status_code == 200, now_start.text[:200])
        check("durasi reschedule = 20", now_start.json()["session"]["duration_minutes"] == 20)

        dup = requests.post(f"{API}/makeups", headers=H(admin), json={
            "session_id": ses["id"], "student_ids": [other["id"]],
            "start_time": iso(now - timedelta(minutes=1)), "end_time": iso(now + timedelta(hours=3))}, timeout=30)
        check("jadwal ulang siswa sama = updated (bukan duplikat)",
              dup.json().get("updated") == 1 and dup.json().get("created") == 0, dup.text[:150])
        cnt = len(requests.get(f"{API}/makeups", headers=H(admin),
                               params={"session_id": ses["id"]}, timeout=30).json())
        check("total jadwal tetap 2", cnt == 2, str(cnt))

        # ---------- 9. GET /makeups/me untuk siswa
        me = requests.get(f"{API}/makeups/me", headers=H(otok), timeout=30)
        check("GET /makeups/me 200", me.status_code == 200, me.text[:150])
        check("siswa melihat jadwal susulannya", len(me.json()) == 1, str(len(me.json())))

        # ---------- 10. batalkan jadwal
        d = requests.delete(f"{API}/makeups/{mk_other['id']}", headers=H(admin), timeout=30)
        check("DELETE /makeups 200", d.status_code == 200, d.text[:150])
        left = requests.get(f"{API}/makeups", headers=H(admin),
                            params={"session_id": ses["id"]}, timeout=30).json()
        check("tinggal 1 jadwal", len(left) == 1, str(len(left)))
        check("DELETE jadwal tak ada = 404",
              requests.delete(f"{API}/makeups/{mk_other['id']}", headers=H(admin), timeout=30).status_code == 404)

        # ---------- 11. otorisasi: siswa tak boleh akses endpoint guru
        forb = requests.get(f"{API}/makeups", headers=H(stok), timeout=30)
        check("siswa DITOLAK GET /makeups (403)", forb.status_code == 403, str(forb.status_code))
        forb2 = requests.post(f"{API}/makeups", headers=H(stok), json={
            "session_id": ses["id"], "student_ids": [target["id"]],
            "start_time": iso(now), "end_time": iso(now + timedelta(hours=1))}, timeout=30)
        check("siswa DITOLAK POST /makeups (403)", forb2.status_code == 403, str(forb2.status_code))

        # ---------- 12. hapus sesi ikut menghapus susulan (cascade)
        requests.delete(f"{API}/sessions/{ses['id']}", headers=H(admin), timeout=30)
        after = requests.get(f"{API}/makeups", headers=H(admin),
                             params={"session_id": ses["id"]}, timeout=30).json()
        check("hapus sesi menghapus susulan (cascade)", len(after) == 0, str(len(after)))
        ses["id"] = None
    finally:
        if ses.get("id"):
            requests.delete(f"{API}/sessions/{ses['id']}", headers=H(admin), timeout=30)

    print(f"\n===== {ok} PASS / {fail} FAIL =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
