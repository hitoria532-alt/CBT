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

## Implemented (2026-08-18) — Iteration 9
- **Rapor Siswa PDF**: `/api/report/student/{id}/pdf` (reportlab) — identitas, rata-rata, grafik perkembangan nilai, tabel rincian. Admin/guru unduh untuk siswa mana pun (tombol di Manajemen Akun); siswa unduh rapor sendiri (alias `me`) via tombol "Unduh Rapor" di Hasil Saya (siswa lain → 403).
- **Bank Soal Publik**: paket punya `created_by` + `is_public`; guru melihat paket sendiri + publik + legacy; toggle "Bagikan ke Guru Lain". Edit/Hapus hanya pemilik/admin (403 untuk non-pemilik) — bug delete tanpa cek kepemilikan sudah diperbaiki & diverifikasi (403/200/404).
- Verified: setelah fix, permission delete/update paket benar; PDF rapor 200 (admin/self) & 403 (siswa lain).

## Implemented (2026-08-18) — Iteration 10
- **Rapor Kelas Massal**: `/api/report/class/{id}/pdf` (admin/guru) — satu file PDF berisi rapor semua siswa satu kelas (tiap siswa 1 halaman: identitas, rata-rata, grafik perkembangan, tabel rincian). Tombol "Rapor" pada tiap kartu kelas di Manajemen Kelas.
- Verified: endpoint 200 application/pdf (%PDF valid), siswa ditolak 403; Classes.jsx parse OK.

## Implemented (2026-08-18) — Iteration 11
- **Duplikat Paket**: `POST /api/packages/{id}/duplicate` — guru menyalin paket (publik milik guru lain, atau miliknya) menjadi paket baru miliknya ("… (Salinan)", is_public=false) untuk diubah bebas. Menyalin paket privat milik guru lain → 403. Tombol "Duplikat" (ikon copy) di tiap kartu paket.
- Verified: guru B menyalin paket publik guru A (jadi milik B & privat), salinan muncul di daftar B; salin paket privat orang lain 403; Packages.jsx parse OK.

## Implemented (2026-08-19) — Iteration 12 (Identitas Sekolah)
- **Pengaturan Sekolah**: menu admin baru (`/admin/pengaturan`) untuk atur nama, alamat, **unggah logo**, dan **tema warna**. Endpoint `/api/settings/school` (GET semua, PUT admin).
- **Logo & Identitas di Dashboard**: banner hero memakai logo & nama sekolah tersimpan (fallback logo bawaan).
- **Kop Rapor**: rapor siswa & rapor kelas PDF kini menampilkan logo + nama + alamat sekolah di kop (via `_school_kop`).
- **Tema Warna**: pilihan warna (6 preset) diterapkan ke `--primary`/`--ring` global saat app dimuat.
- Verified: PUT/GET school OK; report PDF dgn kop 200 %PDF; semua file frontend parse OK.

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

## Restore from GitHub (2026-08-19)
Repo `hitoria532-alt/CBT` (branch `main`, 14 commits, latest `35675c1`) was re-cloned into
`/app` and brought back online on the Emergent live preview.

**What had to be recreated** (these are gitignored, so they were NOT in the repo):
- `/app/backend/.env`: `JWT_SECRET` (regenerated — old tokens invalid), `ADMIN_EMAIL`,
  `ADMIN_PASSWORD`, `EMERGENT_LLM_KEY` (object storage for question images),
  `WEBHOOK_CRON_SECRET` (auto-submit cron).
- MongoDB data: the database was empty. Baseline content is now re-seeded via the new
  idempotent `/app/scripts/seed_demo.py`. See `/app/memory/test_credentials.md`.

**Dependencies installed**: `reportlab`, `openpyxl` (were missing from the image);
`requirements.txt` refreshed via pip freeze. Frontend deps were already complete.

**Bugs found & fixed during the restore**
- HTTP 500 on `/api/results/detail/{id}`, `/api/results/detail/{id}/pdf`,
  `/api/results/grade/{id}` and on submit when a **package had been deleted after** an
  exam was taken. Added `attempt_question_ids()` which falls back to the attempt's stored
  `details`/`question_order`, so historical results and PDFs keep working.
- `/api/exam/start` and `/api/analytics/session/{id}` now return a clear 400
  ("Paket soal untuk sesi ini sudah dihapus") instead of a 500 when a session's package
  is missing.
- `/admin/akun` and `/admin/pengaturan` were reachable by **guru** via direct URL even
  though the sidebar hid them — both routes are now admin-only in `App.js`.
- `GET /api/settings/school` is now public (school name/theme is branding needed before
  login); this also removed 401 console noise on the login page.
- Recharts console warnings on the dashboard eliminated with a new measured
  `components/ChartBox.jsx` wrapper (explicit pixel width/height, still responsive).
- Test debt cleaned: outdated threshold assertions in `test_iteration5.py` /
  `test_iteration6.py`, a dead external image host in `test_iteration4.py`, and an
  order-dependent exam-start test in `test_cbt_api.py`.

**Verified**: 122/122 backend pytest pass; frontend E2E regression 95%+ with all reported
issues fixed; result/rapor/class PDFs and class xlsx export all return 200; essay grading
recomputes the score correctly (4/5 -> 80.0).

## Implemented (2026-08-19) — Iteration 13: Pilihan Ganda A–E + Ekspor Excel Hasil
- **Opsi PG A–E**: editor Bank Soal kini menyediakan 5 slot opsi (A–E) dengan tombol
  "Tambah opsi" & hapus per baris (min 2, maks 5). Saat menyimpan hanya opsi kosong di
  **akhir** yang dipangkas sehingga posisi A–E — dan indeks kunci jawaban — tidak pernah
  bergeser. Validasi: minimal 2 opsi terisi, dan kunci tidak boleh menunjuk opsi kosong.
- **Impor A–E**: kolom `option_e` ditambahkan pada impor CSV/Excel, huruf kunci `E`/`e`
  dipetakan ke indeks 4, slot kosong di tengah tidak menggeser kunci, dan kunci yang
  menunjuk opsi kosong ditolak dengan pesan jelas. Template unduhan diperbarui (5 opsi +
  contoh baris baru). ExamView/ResultDetail sudah generik sehingga otomatis mendukung 5 opsi
  (termasuk saat opsi diacak — indeks tampilan didekode kembali ke kunci asli).
- **Ekspor Excel Hasil & Koreksi**: endpoint baru `GET /api/export/session/{id}/xlsx`
  (admin+guru) memakai openpyxl, menghasilkan 3 lembar rapi:
  1. `Rekap Nilai` — kop sekolah, blok info sesi (paket, mapel, jumlah soal, metode nilai,
     durasi, KKM, jadwal), tabel peserta (No, Nama, NISN/NIP, Kelas, Status, Benar, Salah,
     Kosong, Poin, Nilai, Predikat A–E, Keterangan Lulus/Belum, Waktu Kumpul) dengan warna
     lulus/tidak lulus, baris zebra, header dibekukan + autofilter, blok `RINGKASAN`
     (rata-rata, tertinggi, terendah, jumlah lulus, ketuntasan %), landscape fit-to-width.
  2. `Rincian Jawaban` — matriks poin siswa × soal, sel diwarnai benar/salah/esai, teks soal
     tersimpan sebagai komentar sel.
  3. `Analisis Butir` — % benar & label Mudah/Sedang/Sulit per soal beserta ambang yang dipakai.
  Tombol **Ekspor Excel** ditambahkan di halaman Hasil & Koreksi.
- Verified: 14/14 pytest `test_iteration13.py` + E2E UI (5 input opsi A–E, simpan/edit kunci E,
  unduh .xlsx berhasil).

## Implemented (2026-08-19) — Iteration 14: Impor Siswa via Excel (Manajemen Kelas)
- **Template Excel rapi**: `GET /api/students/import-template` menghasilkan workbook 2 lembar:
  `Petunjuk` (7 langkah pengisian + keterangan tiap kolom + daftar kelas yang sudah ada) dan
  `Data Siswa` (judul, header berwarna dengan komentar penjelas, 3 baris contoh abu-abu,
  40 baris pra-format, header dibekukan, dropdown kelas, format teks pada NIS agar angka 0
  di depan tidak hilang).
- **Impor**: `POST /api/students/import` (khusus admin) menerima .xlsx/.csv dengan kolom
  `nama, kelas, nis, username, password` (+ alias: nama siswa/email/nisn/rombel/kata sandi).
  Membuat akun login siswa, membuat kelas otomatis bila belum ada, dan memasukkan siswa ke
  kelasnya. Idempoten: username yang sudah ada akan **diperbarui**, bukan diduplikasi.
  Validasi per baris: nama & username wajib, username harus format email, password minimal
  5 karakter untuk siswa baru, username dobel dalam file ditolak, dan email milik akun
  admin/guru tidak bisa diambil alih. Respons memuat ringkasan + daftar error per baris.
- **UI**: tombol "Impor Siswa" di Manajemen Kelas (hanya admin) membuka dialog berisi tabel
  keterangan kolom, tombol unduh template, pemilih file, dan panel hasil impor
  (Siswa Baru / Diperbarui / Masuk Kelas, kelas baru yang dibuat, serta daftar baris dilewati).
- Verified: 16/16 pytest `test_iteration14.py` (termasuk siswa hasil impor benar-benar bisa
  login dan melihat sesi kelasnya) + E2E UI unggah file nyata.
- Total suite: **152 passed, 2 skipped**.

## Implemented (2026-08-19) — Iteration 15: Mode Ujian Ketat (anti-menyontek)
Pilihan user: sanksi = peringatan lalu **kumpul otomatis** setelah N pelanggaran; mode
**selalu aktif** untuk semua sesi; laporan pelanggaran **tampil di Hasil & Koreksi + masuk Excel**.

**BATASAN JUJUR:** aplikasi web tidak dapat mengunci HP di level sistem operasi — hanya
aplikasi Android/iOS native (kiosk / screen pinning) yang bisa. Layar penuh berfungsi di
Android Chrome; iPhone/Safari tidak mendukung Fullscreen API, namun deteksi keluar aplikasi
tetap berjalan di semua perangkat.

- **Layar gerbang** sebelum ujian (`lockdown-gate`) berisi aturan + tombol "Saya Mengerti,
  Mulai Ujian" (dibutuhkan karena permintaan layar penuh wajib dari gestur pengguna).
- **Hook `useExamLockdown`**: paksa fullscreen, Screen Wake Lock (layar tetap menyala),
  kunci orientasi, blokir klik-kanan/copy/cut/paste, blokir F12 & Ctrl+Shift+I/J/C &
  Ctrl+T/N/W/P/S/U/O, peringatan `beforeunload`, serta deteksi `visibilitychange`,
  `blur`, dan `fullscreenchange`.
- **Overlay penghalang** tiap pelanggaran menampilkan alasan + hitungan `n/N` + sisa
  kesempatan, dan tombol "Lanjutkan Ujian" yang mengembalikan layar penuh.
- **Backend**: `GET/PUT /api/settings/exam-lock` (siswa boleh baca, admin/guru ubah,
  N di-clamp 1–20), `POST /api/exam/violation` mencatat `{type,label,at}` ke attempt dan
  **memanggil `finalize_attempt()` otomatis** saat batas tercapai (`auto_submitted_reason`
  = "pelanggaran"). `/api/exam/start` kini mengirim `lock` + jumlah pelanggaran berjalan.
- **Untuk guru**: kolom "Pelanggaran" (badge merah, tanda `auto`) di tabel Hasil & Koreksi,
  rincian waktu tiap pelanggaran di halaman Koreksi, kolom "Pelanggaran" di sheet
  `Rekap Nilai`, dan sheet ke-4 **`Pelanggaran`** (Nama, NISN, pelanggaran ke-, jenis,
  waktu, dikumpulkan otomatis, status ujian) yang juga memuat attempt yang **masih
  berlangsung** agar kecurangan terlihat saat ujian sedang jalan.
- **Pengaturan**: bagian "Mode Ujian Ketat" di Pengaturan Sekolah (saklar aktif/nonaktif +
  batas pelanggaran, default 3) berikut catatan batasan perangkat.
- Layar ujian sudah responsif untuk HP (header ringkas, palet soal berupa dialog, tombol
  besar). Verified: 10/10 pytest `test_iteration15.py`, total suite **162 passed, 2 skipped**,
  serta E2E UI di viewport HP: gerbang → ujian → pelanggaran 1/3 → 2/3 → kumpul otomatis
  dan guru melihat catatannya.
