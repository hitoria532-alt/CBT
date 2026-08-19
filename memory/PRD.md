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

## Restore dari GitHub (2026-08-19)
- Repo: `hitoria532-alt/CBT` (private) — commit terakhir `35675c1 Auto-generated changes` (15 commit, iterasi 1–12).
- Seluruh kode di-restore ke /app; dependency backend (reportlab, openpyxl, pandas, bcrypt, PyJWT, requests) + `yarn install` selesai.
- `.env` tidak ada di git → dibuat ulang: JWT_SECRET, ADMIN_EMAIL, ADMIN_PASSWORD, WEBHOOK_CRON_SECRET, EMERGENT_LLM_KEY. Object storage init OK.
- **Database kosong** (data lama tidak tersimpan di git) → `python /app/scripts/seed_demo.py` (idempoten) membuat: admin, guru, 2 siswa (Ani/Budi), kategori Matematika, 3 soal (pg/tf/esai), paket publik berbobot, kelas X-A, sesi aktif "UH Matematika - Kelas X", 1 attempt selesai.
- **Bug diperbaiki**: TypeError "can't compare offset-naive and offset-aware datetimes" pada `/api/notifications`, `enrich_session` (`/api/sessions`, `/api/exam/start`) dan auto-submit. Solusi: helper `parse_dt()` (semua parsing ISO dinormalisasi ke UTC-aware), `normalize_session_times()` saat create/update sesi, plus migrasi startup untuk sesi lama yang tersimpan tanpa timezone.
- Verified: pytest legacy 118/122 (4 sisa = asumsi fixture usang, bukan bug), testing agent: backend 55/56, frontend 100% tanpa 500/overlay.

## Implemented (2026-08-19) — Iterasi 13
- **Ujian Ulang Terjadwal**: sesi punya `max_attempts` (default 1) + `score_policy` per sesi (`tertinggi`/`terakhir`/`rata`). Backend menandai tepat satu attempt sebagai `counted` (helper `recount_attempts()`, field `attempt_number`, `counted`, `effective_score`); semua agregat (dashboard, analitik kelas/mapel, peringkat, rapor PDF, rekap xlsx) memakai `counted != False` + `effective_score`. Mengubah kebijakan nilai memicu recount ulang seluruh peserta. Siswa melihat badge "Percobaan n/N", sisa kesempatan, tombol "Ujian Ulang"; blokir dengan pesan "Batas percobaan tercapai (n/N)". Guru melihat kolom Percobaan + badge "Dipakai", rata-rata hanya dari attempt terhitung, Export CSV memuat kolom Percobaan/Dipakai.
- **Impor Akun Massal**: `GET /api/users/import-template` + `POST /api/users/import` (admin saja) menerima .xlsx/.xls/.csv dengan kolom `nama, email, password, role, identifier`. Email yang sudah ada diperbarui (password opsional), baris tidak valid dilaporkan per baris tanpa membatalkan impor. UI: dialog "Impor Akun" di Manajemen Akun (unduh template, unggah, ringkasan hasil + daftar error).
- **Bug UI**: overlay dialog Radix meninggalkan `pointer-events: none` di body sehingga halaman terasa beku setelah simpan → helper `releaseBodyPointerEvents()` dipanggil di semua dialog admin.
- Verified: testing agent — backend 13/13 fitur baru + regresi 200 OK, frontend semua alur (impor, retake 3x, blokir ke-4, kebijakan nilai, badge) lolos; overlay diverifikasi ulang lewat klik non-force.

## Implemented (2026-08-19) — Iterasi 14
- **Export Excel Rapi (Hasil & Koreksi)**: `GET /api/export/session/{id}/xlsx` (admin/guru) — kop sekolah, band judul bertema, meta sesi (paket, jumlah soal, jadwal WIB, durasi, KKM, maks percobaan + kebijakan nilai), tabel bergaris & zebra (No, Nama, NISN/NIP, Kelas, [Percobaan, Dipakai jika retake], Status, Nilai, KKM, Keterangan) dengan warna nilai lulus/tidak, header di-freeze, plus blok RINGKASAN (jumlah peserta, sudah dinilai, rata-rata, tertinggi, terendah, tuntas %, belum tuntas). Tombol "Export Excel" (utama) + "CSV" di halaman hasil sesi. Helper baru `fmt_local()` (WIB) & `STATUS_ID`.
- **Pilihan Ganda A–E**: editor Bank Soal kini 5 baris opsi (A–E); opsi kosong di akhir dipangkas otomatis sehingga soal boleh 2–5 opsi. Validasi: minimal 2 opsi, tidak boleh ada opsi kosong di tengah, kunci tidak boleh menunjuk opsi kosong. Impor massal: kolom `option_e` + kunci `A..E`, baris dengan kunci menunjuk opsi kosong ditolak per baris. ExamView/hasil/PDF sudah berbasis indeks sehingga otomatis mendukung E (diverifikasi juga dengan acak opsi).
- Verified: testing agent iterasi 13 (export Excel) 18/18 backend + frontend 100%; iterasi 14 (A–E) 9/9 backend, 5/5 frontend, 7/7 integrasi.

## Implemented (2026-08-19) — Iterasi 15
- **Kartu Peserta Ujian**: `GET /api/cards/class/{id}/pdf?session_id=opsional` (admin/guru) — PDF A4 siap cetak, 2 kartu per baris. Tiap kartu: logo + nama & alamat sekolah (dari Pengaturan Sekolah), band "KARTU PESERTA UJIAN", Nama Peserta, NISN/NIP, Kelas, Akun Login (email), tabel sesi ujian (judul + paket, jadwal WIB, durasi, maks 5 sesi + indikator "+n sesi lainnya"), catatan wajib bawa kartu + kolom tanda tangan; garis aksen terracotta & border untuk dipotong. Tombol "Kartu" di kartu kelas (Manajemen Kelas). Helper `_sized_logo()`.
- **Fix**: `PUT /api/settings/school` tidak lagi menghapus `theme_color` saat field tidak dikirim (patch-merge).
- Verified: testing agent — backend 9/9 (role check 200/200/403/404, isi PDF, filter session_id, logo tertanam, theme preserved), frontend 100% (unduh kartu, Rekap, Rapor, simpan Pengaturan Sekolah), regresi export Excel & rapor PDF & peringkat OK.

## Implemented (2026-08-19) — Iterasi 16
- **Impor Fleksibel (Data Lama)**: importer kini mengenali header spreadsheet gaya sekolah.
  - Bank soal: `soal/pertanyaan/butir soal/uraian`, opsi `a–e / opsi_a / pilihan_a / option_a`, `kunci/kunci_jawaban/jawaban` (menerima A–E, indeks 0–4, atau teks jawabannya), `bobot/skor`, `mapel/kategori/mata pelajaran/materi`, `gambar/url_gambar`. Kolom `type` opsional — tipe soal ditebak otomatis (ada opsi → PG, kunci benar/salah → B/S, tanpa keduanya → esai). Validasi per baris tetap dilaporkan.
  - Akun: `nama/nama_lengkap`, `nis/nisn/nip/no induk`, dan kolom baru **`kelas`** (kelas dibuat otomatis + siswa langsung menjadi anggota). Siswa tanpa email → email otomatis `nisn@siswa.sekolah.id`; akun baru tanpa password → password = NISN (fallback `siswa123`/`guru123`). Respons menambahkan daftar `notes` yang ditampilkan di dialog Impor Akun.
- Verified: testing agent — backend 8/8 impor (header Indonesia, inferensi tipe, kunci teks, kategori & kelas otomatis, login akun hasil impor) + 8/8 regresi (kartu peserta, export Excel, retake, koreksi, peringkat), frontend 100%.
