# PRD — Aplikasi CBT / Ujian Online

## Problem Statement (asli)
Aplikasi CBT/ujian soal lengkap dengan pengolahan nilai + rumus pengolahan nilai, detail jawaban siswa, paket soal, sesi pelaksanaan, kategori materi, laporan hasil siswa, dan manajemen akun (siswa, guru, admin).

## User Choices
- Tipe soal: Pilihan Ganda + Esai + Benar/Salah
- Rumus nilai: Persentase (benar/total×100) DAN Berbobot per soal
- Timer + jadwal sesi (waktu mulai & selesai)
- Auth: JWT email/password, 3 role
- Desain: ditentukan agent (tema "Calm Authority" — hijau forest + terracotta, font Outfit + IBM Plex Sans)

## Arsitektur
- Backend: FastAPI + MongoDB (motor), JWT auth (bcrypt), semua route prefix `/api`
- Frontend: React 19 + React Router + Tailwind + shadcn/ui + framer-motion + recharts + sonner
- Auth: token di localStorage (Bearer) + httpOnly cookie

## Personas
- Admin: akses penuh + manajemen akun
- Guru: kelola kategori/soal/paket/sesi + koreksi esai (tanpa manajemen akun)
- Siswa: kerjakan ujian + lihat hasil

## Implemented (2026-08-18)
- Auth 3 role + seed admin (hitoria532@gmail.com)
- Manajemen Akun (CRUD user, filter role)
- Kategori Materi (CRUD)
- Bank Soal (CRUD, tipe pg/truefalse/essay, bobot, kunci)
- Paket Soal (pilih soal, metode penilaian persentase/berbobot)
- Sesi Pelaksanaan (paket, jadwal mulai/selesai, durasi, KKM, status otomatis)
- Ujian Siswa: timer + auto-submit, palette navigasi, autosave, transisi soal
- Pengolahan nilai otomatis (pg/tf) + koreksi esai manual oleh guru
- Laporan hasil: dashboard admin (stats+chart), hasil per sesi + export CSV, detail jawaban siswa
- Verified: 20/20 backend tests + frontend E2E pass. Weighted math verified.

## Implemented (2026-08-18) — Iteration 2
- **Impor Soal**: impor massal bank soal dari CSV/Excel (template unduh, auto-buat kategori). Bug numeric-option & blank-row diperbaiki.
- **Acak Soal**: opsi paket acak urutan soal & opsi jawaban per siswa (stabil per attempt, grading tetap benar via option_perm decode saat submit).
- **Manajemen Kelas**: kelola rombel + anggota siswa; sesi bisa ditargetkan ke kelas tertentu (kosong = semua siswa), siswa hanya melihat sesi kelasnya.
- **Kartu Hasil PDF**: unduh kartu hasil ujian (reportlab) untuk siswa & admin/guru.
- Verified: shuffle+grading E2E benar, class filtering benar, PDF 200 application/pdf, semua selektor UI ada.

## Implemented (2026-08-18) — Iteration 3
- **Auto-Submit Server**: cron `.emergent/crons.yml` (tiap 15 menit) memanggil `/api/cron/auto-submit` (auth Bearer WEBHOOK_CRON_SECRET, kerja di background). Menyelesaikan+menilai attempt 'berlangsung' yang sudah lewat batas waktu sesi/durasi walau browser ditutup. Logika submit dipakai bersama via `finalize_attempt()`.
- **Analitik Butir Soal**: `/api/analytics/session/{id}` — persen benar & tingkat kesukaran (Mudah/Sedang/Sulit) per soal; tombol "Analitik Butir" di Hasil & Koreksi.
- **Ekspor Rekap Nilai**: `/api/export/class/{id}/xlsx` (openpyxl, header bertema) — rekap nilai satu kelas; tombol "Rekap Nilai" di kartu kelas.
- **Bank Media Soal**: object storage (Emergent) untuk gambar soal — `/api/uploads/image` + `/api/files/{path}` (auth via header/query). Gambar tampil di editor soal, ExamView, & detail hasil.
- Verified: backend 14/14 pytest lolos (termasuk uji timing auto-submit), frontend E2E lolos (unduh xlsx nyata, render analitik, editor gambar). Bug lama impor angka-float dikonfirmasi sudah diperbaiki (impor baru bersih) & sisa data lama dibersihkan.

## Implemented (2026-08-18) — Iteration 4
- **Analitik Kelas**: `/api/analytics/classes` + 2 chart di dashboard admin (rata-rata nilai per kelas + tren rata-rata per sesi).
- **Soal Gambar Massal**: kolom `image_url` pada impor CSV/Excel — gambar diunduh otomatis ke object storage (browser UA agar host publik tak menolak). Template diperbarui.
- **Pengumuman Sesi**: `/api/notifications` untuk siswa (upcoming/live/info) + lonceng notifikasi dengan badge belum-dibaca di header siswa; field Pengumuman pada sesi.
- **Bank Rumus Nilai**: paket punya Nilai Minimal (floor) & Pembulatan (2/1 desimal/bulat), diterapkan di compute_grade (re-round setelah clamp). Terverifikasi 1/3 benar + min 40/bulat = 40.0.
- Verified: 12/12 pytest iter-4 lolos + frontend E2E 100% (fix import Textarea di Sessions.jsx oleh testing agent).

## Implemented (2026-08-18) — Iteration 5
- **Peringkat Kelas**: papan peringkat siswa per kelas berdasarkan rata-rata nilai. Admin `/admin/peringkat` (pilih kelas, medali top-3); siswa `/peringkat` (peringkat kelasnya, baris sendiri ditandai "Anda"). Endpoint `/api/leaderboard/class/{id}` & `/api/leaderboard/me`.
- **Ambang Kesukaran**: guru bisa atur batas persen label Mudah/Sedang/Sulit (global) via dialog "Atur Ambang" di Analitik Butir. Endpoint `/api/settings/difficulty` (GET/PUT, validasi medium<easy, clamp 0-100); analitik memakai ambang tersimpan.
- Verified: 11/11 pytest iter-5 lolos + frontend E2E 100%, tanpa isu kritis.

## Implemented (2026-08-18) — Iteration 6
- **Peringkat Angkatan**: papan peringkat gabungan lintas kelas (semua siswa) via `/api/leaderboard/global`. Admin: opsi "🏆 Angkatan (Semua Siswa)" default di halaman Peringkat (menampilkan kelas tiap siswa). Siswa: seksi "Peringkat Angkatan" (top 10 + baris sendiri) di atas peringkat kelas.
- **Ambang per Paket**: paket bisa punya ambang kesukaran khusus (easy_min/medium_min) yang menimpa setelan global; analitik menampilkan sumber ("khusus paket"/"global"). Validasi 0 ≤ Sedang < Mudah ≤ 100 di backend.
- Verified: 10/10 pytest iter-6 lolos + frontend E2E 100%, tanpa isu kritis.

## Implemented (2026-08-18) — Iteration 7
- **Filter Peringkat**: peringkat angkatan bisa disaring per rentang tanggal (`start`/`end`) dan/atau mata pelajaran (kategori) via `/api/leaderboard/global`; bar filter tampil hanya di mode Angkatan, dengan tombol Reset.
- **Ekspor Peringkat**: tombol "Ekspor Excel" mengunduh papan peringkat angkatan (mengikuti filter aktif) via `/api/export/leaderboard/xlsx` (openpyxl, hanya admin/guru).
- Verified: 12/12 pytest iter-7 lolos + frontend E2E 100%, tanpa isu.

## Implemented (2026-08-18) — Iteration 8
- **Filter Peringkat Siswa**: filter mata pelajaran (kategori) di halaman peringkat siswa, berlaku untuk seksi Angkatan & per-kelas via `/api/leaderboard/me?category_id=`.
- **Statistik Mapel**: chart "Rata-rata Nilai per Mata Pelajaran" di dashboard admin via `/api/analytics/subjects` (terkuat→terlemah).
- Verified: 16/16 pytest iter-8 lolos + frontend E2E 100%, tanpa bug.

## Backlog (P1/P2)
- P1: Bank soal impor Excel/CSV, acak urutan soal per siswa
- P1: Cascade delete attempts saat user dihapus
- P2: Grup/kelas siswa & assign sesi per kelas
- P2: Analitik butir soal (tingkat kesukaran)
- P2: Cetak/print sertifikat atau kartu hasil PDF

## Test Credentials
- Admin: hitoria532@gmail.com / admin123
- Guru: guru@sekolah.id / guru123
- Siswa: siswa@sekolah.id / siswa123
