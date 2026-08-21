<div align="center">

# CBT Ujian Online

**Platform Ujian Berbasis Komputer (Computer Based Test) untuk Sekolah**

Kelola bank soal, jadwalkan sesi ujian, nilai otomatis, dan pantau hasil siswa dalam satu tempat.

![Stack](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)
![Stack](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white)
![Stack](https://img.shields.io/badge/MongoDB-Motor-47A248?logo=mongodb&logoColor=white)
![Stack](https://img.shields.io/badge/Tailwind-3.4-06B6D4?logo=tailwindcss&logoColor=white)
![Auth](https://img.shields.io/badge/Auth-JWT%20%2B%20bcrypt-orange)

</div>

---

## 1. Overview Project

**CBT Ujian Online** adalah aplikasi web *full-stack* untuk penyelenggaraan ujian/asesmen
digital di lingkungan sekolah. Aplikasi menggantikan alur ujian kertas — mulai dari
penyusunan bank soal, pelaksanaan ujian berjadwal di browser, penilaian otomatis, sampai
pelaporan nilai — menjadi satu alur kerja digital yang terukur.

### Untuk siapa aplikasi ini?

Aplikasi memiliki **3 peran (role)** dengan hak akses berbeda:

| Role | Hak Akses |
|------|-----------|
| **Admin** | Akses penuh: seluruh fitur guru + Manajemen Akun + Pengaturan Sekolah + impor siswa |
| **Guru** | Kategori materi, bank soal, paket soal, sesi ujian, manajemen kelas, koreksi esai, laporan |
| **Siswa** | Mengerjakan ujian sesuai jadwal & kelasnya, melihat hasil, detail jawaban, dan peringkat |

### Fitur Utama

<details open>
<summary><b>Penyusunan Materi Ujian</b></summary>

- **Kategori Materi** — CRUD pengelompokan mata pelajaran / topik.
- **Bank Soal** — 3 tipe soal: **Pilihan Ganda (opsi A–E, 2–5 opsi)**, **Benar/Salah**, dan
  **Esai**. Setiap soal memiliki bobot nilai dan dapat menyertakan **gambar** (object storage).
- **Impor Soal Massal** — unggah CSV/Excel dengan template siap pakai; kategori dibuat
  otomatis, kolom `image_url` mengunduh gambar soal secara otomatis.
- **Paket Soal** — rakit soal menjadi paket ujian, atur **metode penilaian**
  (persentase atau berbobot per soal), **acak urutan soal & opsi jawaban** per siswa,
  **nilai minimal (floor)**, dan **pembulatan** (2 desimal / 1 desimal / bulat).
  Paket bisa **diduplikasi** dalam satu klik.

</details>

<details open>
<summary><b>Pelaksanaan Ujian</b></summary>

- **Sesi Pelaksanaan** — pilih paket, jadwal mulai & selesai, durasi, KKM, pengumuman,
  serta **target kelas** (kosong = semua siswa). Status sesi berubah otomatis:
  `akan_datang` → `berlangsung` → `selesai` / `menunggu_koreksi`.
- **Ruang Ujian Siswa** — timer hitung-mundur dengan **auto-submit**, palet navigasi soal,
  **autosave** jawaban, dan transisi antar soal yang halus.
- **Mode Ujian Ketat (anti-menyontek)** — layar gerbang berisi aturan, paksa *fullscreen*,
  *Screen Wake Lock*, deteksi pindah tab/keluar fullscreen, overlay peringatan berhitung
  `n/N`, hingga **kumpul otomatis** saat batas pelanggaran terlampaui. Semua pelanggaran
  dilaporkan ke guru.
- **Auto-Submit Server-Side** — cron tiap 15 menit memanggil `/api/cron/auto-submit`
  sehingga *attempt* yang kedaluwarsa tetap dinilai meski browser siswa ditutup.

</details>

<details open>
<summary><b>Penilaian & Pelaporan</b></summary>

- **Penilaian otomatis** untuk PG & Benar/Salah; **koreksi esai manual** oleh guru.
- **Hasil & Koreksi** — rekap per sesi, detail jawaban per siswa, ekspor **CSV** dan
  **Excel 4 sheet** (Rekap Nilai, Rincian Jawaban, Analisis Butir, Pelanggaran).
- **Kartu Hasil / Rapor PDF** — kartu hasil per siswa dan **rapor kelas massal** (reportlab).
- **Analitik Butir Soal** — persentase benar & tingkat kesukaran (Mudah/Sedang/Sulit)
  dengan **ambang batas yang dapat diatur guru**.
- **Dashboard & Analitik Kelas** — statistik ringkas, rata-rata nilai per kelas, dan tren
  rata-rata per sesi (grafik Recharts).
- **Peringkat (Leaderboard)** — peringkat per kelas & global, medali top-3, ekspor Excel.
  Siswa melihat peringkat kelasnya sendiri dengan barisnya ditandai "Anda".

</details>

<details open>
<summary><b>Administrasi</b></summary>

- **Manajemen Akun** — CRUD pengguna dengan filter role (khusus admin).
- **Manajemen Kelas** — kelola rombel & anggota, **impor siswa via Excel** dengan template
  dan validasi per baris.
- **Pengaturan Sekolah** — nama & alamat sekolah, **logo**, dan **warna tema** yang
  langsung diterapkan ke seluruh UI.
- **Notifikasi Siswa** — lonceng dengan badge belum-dibaca untuk sesi mendatang/berlangsung.

</details>

---

## 2. Tech Stack

### Frontend

| Komponen | Teknologi | Keterangan |
|----------|-----------|------------|
| Framework | **React 19** | CRA + **CRACO** (`craco.config.js`) sebagai build tooling |
| Routing | **react-router-dom 7** | Nested route + guard berbasis role |
| Styling | **Tailwind CSS 3.4** | Token warna HSL via CSS variables di `index.css` |
| Komponen UI | **shadcn/ui** + **Radix UI** | ~45 komponen primitif di `src/components/ui/` |
| Ikon | **lucide-react** | — |
| Animasi | **framer-motion** | Transisi halaman & soal |
| Grafik | **Recharts 3** | Dibungkus `ChartBox.jsx` (ukuran terukur, bebas warning) |
| HTTP Client | **axios** | Instance terpusat + interceptor token (`src/lib/api.js`) |
| Notifikasi | **sonner** | Toast |
| Form | **react-hook-form** + **zod** | Validasi skema |
| Tanggal | **date-fns**, **dayjs** | Format lokal `id-ID` |

### Backend

| Komponen | Teknologi | Keterangan |
|----------|-----------|------------|
| Framework | **FastAPI 0.110** | Seluruh route di bawah prefix `/api` |
| Server | **Uvicorn** | Bind `0.0.0.0:8001`, dijalankan via **supervisor** |
| Validasi | **Pydantic v2** | Model request/response |
| Driver DB | **Motor** (async PyMongo) | Akses MongoDB non-blocking |
| Excel | **openpyxl**, **pandas** | Impor & ekspor `.xlsx` / `.csv` |
| PDF | **reportlab** | Kartu hasil & rapor kelas |
| Auth | **PyJWT** + **bcrypt/passlib** | Token HS256 |

### Database

- **MongoDB** (koneksi lewat `MONGO_URL`, nama database lewat `DB_NAME`).
- *Schema-less*, dokumen memakai **UUID string** sebagai `id` (bukan `ObjectId`) agar
  aman diserialisasi ke JSON.

**Koleksi yang digunakan:**

| Koleksi | Isi |
|---------|-----|
| `users` | Akun admin/guru/siswa (email, nama, NIS, `password_hash`, role) |
| `categories` | Kategori materi / mata pelajaran |
| `questions` | Bank soal (tipe, teks, opsi, kunci, bobot, `image_path`) |
| `packages` | Paket soal (daftar `question_ids`, metode nilai, acak, floor, pembulatan) |
| `sessions` | Sesi pelaksanaan (paket, jadwal, durasi, KKM, target kelas, pengumuman) |
| `attempts` | Pengerjaan siswa (jawaban, `question_order`, `option_perm`, nilai, pelanggaran) |
| `classes` | Rombel + anggota siswa |
| `settings` | Pengaturan sekolah, ambang kesukaran, konfigurasi mode ujian ketat |
| `files` | Metadata berkas/gambar yang diunggah |

### Auth

- **JWT** (HS256) ditandatangani dengan `JWT_SECRET`, payload: `sub`, `email`, `role`, `exp`.
- Password di-hash dengan **bcrypt** — *plaintext* tidak pernah disimpan.
- Token dikirim **dua jalur**: header `Authorization: Bearer <token>` (dari `localStorage`)
  **dan** cookie `httpOnly` — memudahkan unduhan berkas langsung dari browser.
- Otorisasi berbasis dependency `require_roles("admin", "guru", ...)` di setiap endpoint,
  ditambah guard `<Protected roles={[...]}>` di sisi frontend.
- Akun admin awal di-*seed* otomatis saat startup dari `ADMIN_EMAIL` / `ADMIN_PASSWORD`.

### Storage

- **Emergent Object Storage** (`INTEGRATION_PROXY_URL`, autentikasi `EMERGENT_LLM_KEY`)
  untuk gambar soal dan logo sekolah.
- Unggah: `POST /api/uploads/image` → mengembalikan `path`.
- Baca: `GET /api/files/{path}` (autentikasi lewat header **atau** query `?auth=<token>`,
  dipakai helper `fileUrl()` di frontend agar `<img>` bisa memuat berkas terproteksi).

---

## 3. Folder Structure

```text
CBT/
├── .emergent/                  # Konfigurasi platform Emergent (image, cron, deps sistem)
│   ├── crons.yml               #   → jadwal cron auto-submit ujian (tiap 15 menit)
│   └── emergent.yml            #   → metadata environment/build
│
├── backend/                    # === APLIKASI FASTAPI ===
│   ├── server.py               # Seluruh API: model, auth, endpoint, penilaian, ekspor
│   ├── requirements.txt        # Dependensi Python (hasil `pip freeze`)
│   ├── pytest.ini              # Konfigurasi pytest
│   ├── .env                    # ⚠️ TIDAK di-commit (gitignored) — lihat bagian Setup
│   └── tests/                  # Test API per iterasi pengembangan
│       ├── test_cbt_api.py     #   → suite inti (auth, CRUD, alur ujian, penilaian)
│       └── test_iteration*.py  #   → regresi per fitur baru (±162 test)
│
├── frontend/                   # === APLIKASI REACT ===
│   ├── public/
│   │   ├── index.html          # HTML shell + preload font
│   │   └── school-logo.png     # Logo default sekolah
│   ├── src/
│   │   ├── index.js            # Entry point React
│   │   ├── index.css           # Tailwind base + CSS variables tema (light/dark)
│   │   ├── App.css             # Style global tambahan & utilitas kustom
│   │   ├── App.js              # Definisi seluruh route + guard role
│   │   ├── context/
│   │   │   └── AuthContext.js  # State user global: login, logout, restore sesi
│   │   ├── lib/
│   │   │   ├── api.js          # Instance axios, interceptor token, apiError, fileUrl
│   │   │   ├── utils.js        # `cn()` — helper merge className (shadcn)
│   │   │   └── utils2.js       # Format tanggal id-ID + peta label status/role/tipe soal
│   │   ├── hooks/
│   │   │   ├── use-toast.js        # Hook toast (shadcn)
│   │   │   └── useExamLockdown.js  # Logika Mode Ujian Ketat (fullscreen, deteksi tab)
│   │   ├── constants/testIds/  # Registry `data-testid` terpusat untuk test E2E
│   │   ├── components/
│   │   │   ├── AdminLayout.jsx    # Shell admin/guru: sidebar + header + <Outlet/>
│   │   │   ├── StudentLayout.jsx  # Shell siswa: header + notifikasi + <Outlet/>
│   │   │   ├── ChartBox.jsx       # Wrapper Recharts berukuran terukur
│   │   │   └── ui/                # Komponen shadcn/ui (button, dialog, table, ...)
│   │   └── pages/
│   │       ├── Login.jsx          # Halaman masuk (split-screen branding)
│   │       ├── admin/             # Halaman admin & guru
│   │       │   ├── Dashboard.jsx      # Statistik + grafik analitik
│   │       │   ├── Categories.jsx     # Kategori materi
│   │       │   ├── Questions.jsx      # Bank soal + impor + editor gambar
│   │       │   ├── Packages.jsx       # Paket soal + duplikasi
│   │       │   ├── Sessions.jsx       # Sesi pelaksanaan & jadwal
│   │       │   ├── Classes.jsx        # Manajemen kelas + impor siswa + rapor
│   │       │   ├── Results.jsx        # Hasil, koreksi esai, analitik butir, ekspor
│   │       │   ├── Leaderboard.jsx    # Peringkat kelas
│   │       │   ├── SchoolSettings.jsx # Identitas sekolah, tema, mode ujian ketat
│   │       │   └── Accounts.jsx       # Manajemen akun (admin-only)
│   │       └── student/           # Halaman siswa
│   │           ├── StudentHome.jsx       # Daftar sesi tersedia
│   │           ├── ExamView.jsx          # Ruang ujian (timer, palet, lockdown)
│   │           ├── StudentResults.jsx    # Riwayat nilai
│   │           ├── ResultDetail.jsx      # Rincian jawaban per ujian
│   │           └── StudentLeaderboard.jsx# Peringkat kelas siswa
│   ├── package.json            # Dependensi & script (start/build/test via craco)
│   ├── craco.config.js         # Override webpack CRA
│   ├── tailwind.config.js      # Tema Tailwind (warna, font, radius, animasi)
│   ├── components.json         # Konfigurasi generator shadcn/ui
│   └── .env                    # ⚠️ TIDAK di-commit — REACT_APP_BACKEND_URL
│
├── scripts/
│   └── seed_demo.py            # Seed data demo idempoten (akun, soal, paket, sesi, nilai)
│
├── memory/
│   ├── PRD.md                  # Dokumen produk + catatan tiap iterasi (sumber kebenaran)
│   └── test_credentials.md     # ⚠️ Gitignored — kredensial akun uji
│
├── tests/                      # Placeholder test tingkat-root
├── test_reports/               # Laporan hasil test (JSON per iterasi + XML pytest)
├── design_guidelines.json      # Panduan desain "The Calm Authority" (warna, font, layout)
└── README.md                   # Dokumen ini
```

> **Catatan penting:** semua berkas `.env`, `memory/test_credentials.md`, dan
> `node_modules/` di-*gitignore*. Setelah kloning repo, berkas tersebut **harus dibuat
> ulang** (lihat [Setup](#setup--menjalankan-lokal)).

---

## 4. Data Flow

### 4.1 Alur Umum Request

```text
┌──────────────┐   1. Aksi user      ┌─────────────────┐
│   Browser    │ ──────────────────► │  React Page     │
│   (Siswa /   │                     │  (pages/*.jsx)  │
│    Guru)     │ ◄────────────────── └────────┬────────┘
└──────────────┘   6. Render UI               │ 2. panggil api.get/post
                                              ▼
                                     ┌─────────────────────────┐
                                     │ src/lib/api.js (axios)  │
                                     │ + interceptor: sisipkan │
                                     │   Bearer token          │
                                     └────────┬────────────────┘
                                              │ 3. HTTPS  {REACT_APP_BACKEND_URL}/api/...
                                              ▼
                                     ┌─────────────────────────┐
                                     │  Kubernetes Ingress     │
                                     │  /api/*  → :8001        │
                                     │  lainnya → :3000        │
                                     └────────┬────────────────┘
                                              ▼
                              ┌───────────────────────────────────┐
                              │        FastAPI (server.py)        │
                              │ a. get_current_user  → verif JWT  │
                              │ b. require_roles(...) → otorisasi │
                              │ c. Pydantic          → validasi   │
                              │ d. Business logic                 │
                              └───────┬───────────────────┬───────┘
                                      │ 4. Motor (async)  │ 4b. gambar/berkas
                                      ▼                   ▼
                            ┌──────────────────┐  ┌────────────────────┐
                            │    MongoDB       │  │  Object Storage    │
                            │  users, questions│  │  (gambar soal,     │
                            │  packages, ...   │  │   logo sekolah)    │
                            └────────┬─────────┘  └────────────────────┘
                                     │ 5. dokumen → JSON (id UUID string)
                                     └────────────────► kembali ke frontend
```

### 4.2 Alur Autentikasi

```text
Login.jsx
  └─► POST /api/auth/login  { email, password }
        └─► server.py: cari user → bcrypt.verify(password, password_hash)
              └─► create_access_token(user_id, email, role)   [JWT HS256]
                    ├─► response body  { token, user }
                    └─► Set-Cookie httpOnly (untuk unduhan berkas)
  ◄── AuthContext: localStorage.setItem("token") + setUser(user)
        └─► App.js <Protected roles={[...]}> → arahkan ke /admin atau /beranda

Refresh halaman:
  AuthContext → GET /api/auth/me (Bearer) → pulihkan user, atau hapus token & ke /login
```

### 4.3 Alur Inti: Mengerjakan Ujian & Penilaian

```text
1. SISWA membuka /beranda
      GET /api/sessions   → hanya sesi milik kelasnya, status dihitung server

2. Mulai ujian  →  POST /api/exam/start { session_id }
      • buat dokumen `attempts` (status "berlangsung")
      • jika paket acak: simpan `question_order` + `option_perm` per siswa
      • kirim soal via sanitize_question()  ← KUNCI JAWABAN DIBUANG di server

3. Selama ujian (ExamView.jsx + useExamLockdown.js)
      • timer hitung-mundur berbasis waktu server
      • autosave  →  POST /api/exam/save/{session_id}
      • pelanggaran (pindah tab / keluar fullscreen)
                  →  POST /api/exam/violation

4. Kumpul  →  POST /api/exam/submit      (atau otomatis oleh timer / cron)
      └─► finalize_attempt()
            └─► compute_grade(package, questions, answers, essay_scores)
                  • decode `option_perm` agar jawaban teracak tetap dinilai benar
                  • metode "persentase"  → (benar / total) × 100
                  • metode "berbobot"    → Σ(bobot benar) / Σ(bobot) × 100
                  • terapkan nilai minimal (floor) → lalu pembulatan
            └─► status: "selesai" atau "menunggu_koreksi" (bila ada soal esai)

5. GURU mengoreksi esai  →  POST /api/results/grade/{attempt_id}
      └─► compute_grade dijalankan ulang dengan `essay_scores` → nilai final

6. PELAPORAN
      GET /api/results/session/{id}        → rekap kelas
      GET /api/results/me                  → riwayat nilai siswa
      GET /api/results/detail/{id}         → rincian jawaban
      GET /api/analytics/session/{id}      → analitik butir soal
      GET /api/export/session/{id}/xlsx    → Excel 4 sheet
      GET /api/report/student/{id}/pdf     → kartu hasil PDF
      GET /api/leaderboard/class/{id}      → peringkat kelas

7. CRON (tiap 15 menit)  →  POST /api/cron/auto-submit
      Bearer WEBHOOK_CRON_SECRET → finalize_attempt() untuk attempt kedaluwarsa
      (ack 2xx segera, proses di background)
```

### 4.4 Alur Impor & Unggah

```text
Impor soal / siswa:
  Questions.jsx / Classes.jsx
    └─► GET  /api/questions/import-template  (unduh template .xlsx)
    └─► POST /api/questions/import  (multipart file)
          └─► pandas/openpyxl parse → validasi per baris
                → laporan { created, skipped, errors[] } ditampilkan sebagai tabel

Unggah gambar soal:
  └─► POST /api/uploads/image → put_object() → Object Storage
        → simpan `image_path` di dokumen `questions`
  └─► Tampilkan: fileUrl(path) → GET /api/files/{path}?auth=<token>
```

---

## 5. Coding Conventions

### 5.1 Penamaan Berkas

| Jenis | Konvensi | Contoh |
|-------|----------|--------|
| Halaman React | `PascalCase.jsx` | `StudentResults.jsx`, `SchoolSettings.jsx` |
| Komponen React | `PascalCase.jsx` | `AdminLayout.jsx`, `ChartBox.jsx` |
| Komponen shadcn/ui | `kebab-case.jsx` (jangan diubah) | `alert-dialog.jsx`, `dropdown-menu.jsx` |
| Hook | `camelCase.js` diawali `use` | `useExamLockdown.js`, `use-toast.js`* |
| Utilitas / context | `camelCase.js` / `PascalCase.js` | `api.js`, `utils2.js`, `AuthContext.js` |
| Modul Python | `snake_case.py` | `server.py`, `seed_demo.py` |
| Test Python | `test_*.py` | `test_cbt_api.py`, `test_iteration15.py` |

<sub>*`use-toast.js` memakai kebab-case karena berasal dari generator shadcn/ui — dibiarkan apa adanya.</sub>

### 5.2 Penamaan Variabel & Fungsi

**Python / FastAPI**
- `snake_case` untuk variabel & fungsi: `compute_grade`, `finalize_attempt`, `attempt_question_ids`.
- `PascalCase` untuk model Pydantic, dengan akhiran **`Body`** untuk payload request:
  `QuestionBody`, `PackageBody`, `SessionBody`, `GradeEssayBody`.
- `UPPER_SNAKE_CASE` untuk konstanta & env: `STORAGE_BASE`, `EMERGENT_KEY`, `JWT_SECRET`.
- Helper privat modul diawali underscore: `_check_pkg_thresholds`.
- Fungsi endpoint selalu `async def` dan memakai `Depends` untuk auth:
  ```python
  @api_router.post("/questions")
  async def create_question(body: QuestionBody,
                            user: dict = Depends(require_roles("admin", "guru"))):
      ...
  ```

**JavaScript / React**
- `camelCase` untuk variabel, fungsi, dan handler; handler diawali `handle` atau `on`:
  `handleSubmit`, `onSelectQuestion`, `loadSessions`.
- `PascalCase` untuk komponen dan custom hook diawali `use`.
- `UPPER_SNAKE_CASE` untuk konstanta & peta label: `STATUS_LABEL`, `ROLE_LABEL`, `QTYPE_LABEL`.
- State boolean diawali kata kerja bantu: `loading`, `saving`, `open`, `isLocked`.

### 5.3 Konvensi API

- **Semua** endpoint backend wajib berprefix `/api` (syarat routing Kubernetes ingress).
  Route didaftarkan pada `api_router = APIRouter(prefix="/api")`.
- Path resource memakai **kata benda jamak** dalam bahasa Inggris:
  `/api/questions`, `/api/packages`, `/api/sessions`, `/api/classes`.
- **Field JSON** memakai `snake_case`: `question_ids`, `start_time`, `scoring_method`,
  `image_path`, `min_score`.
- **Nilai enum** ditulis dalam bahasa Indonesia agar konsisten dengan domain:
  role `admin` / `guru` / `siswa`; status sesi `akan_datang` / `berlangsung` / `selesai` /
  `menunggu_koreksi`; metode nilai `persentase` / `berbobot`; tipe soal `pg` / `truefalse` / `essay`.
- **Identitas dokumen** memakai `id` bertipe UUID string (`new_id()`), **bukan** `_id`
  ObjectId — supaya langsung aman diserialisasi ke JSON.
- **Waktu** selalu **ISO-8601 UTC** (`now_iso()`); konversi ke waktu lokal hanya di
  frontend via `fmtDateTime()` / `toLocalInput()` / `fromLocalInput()`.
- **Error** dikembalikan sebagai `HTTPException(status_code, detail="pesan Indonesia")`
  dan dibaca frontend melalui helper `apiError(e)` lalu ditampilkan dengan `toast.error()`.

### 5.4 Konvensi Frontend

- **Satu instance axios** (`src/lib/api.js`) untuk semua request. **Jangan** memanggil
  `fetch`/`axios` langsung dari komponen, dan **jangan** menuliskan URL backend secara
  hardcode — selalu lewat `process.env.REACT_APP_BACKEND_URL`.
- **Styling** hanya dengan utility class Tailwind + **token semantik** shadcn
  (`bg-background`, `text-foreground`, `bg-card`, `text-muted-foreground`, `bg-primary`).
  Hindari warna mentah seperti `bg-[#123456]` agar fitur ganti tema sekolah tetap bekerja.
  Gabungkan class kondisional dengan `cn()` dari `lib/utils.js`.
- **Latar belakang selalu solid** (`bg-background` / `bg-card`) — tidak transparan.
- **Setiap elemen interaktif wajib punya `data-testid`** (kebab-case, deskriptif:
  `login-submit`, `question-save`, `exam-finish`) supaya bisa diuji otomatis. Nilai yang
  dipakai bersama didaftarkan di `src/constants/testIds/`.
- **Selalu tangani semua state**: `loading` (skeleton/spinner), `empty` (pesan kosong),
  `error` (toast), dan `success`.
- **Label UI berbahasa Indonesia**; nama kode/variabel tetap bahasa Inggris.
- Route path memakai bahasa Indonesia (`/admin/soal`, `/hasil`, `/peringkat`, `/ujian/:sessionId`).

### 5.5 Gaya Desain

Mengikuti `design_guidelines.json` — tema **"The Calm Authority"**:

| Aspek | Nilai |
|-------|-------|
| Palet | Hijau *forest* (`--primary: 157 35% 18%`) + aksen terakota (`--accent: 10 58% 53%`) |
| Latar | Off-white hangat (`--background: 60 20% 98%`) |
| Font | **Outfit** (judul) + **IBM Plex Sans** (teks isi) |
| Mode | Light default, dark didukung (variabel HSL di `index.css`) |
| Filosofi | Admin: dasbor Swiss padat-informasi. Siswa: tenang & minim distraksi |

Warna **tidak boleh** ditulis langsung sebagai hex di komponen — gunakan CSS variable HSL
agar fitur "warna tema sekolah" pada halaman Pengaturan dapat menimpanya saat runtime.

### 5.6 Konvensi Git & Testing

- **Pesan commit** mengikuti *Conventional Commits*:
  `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
  Ringkasan singkat di baris pertama, detail dalam bullet pada body.
  Contoh: `feat: PG A-E, ekspor Excel hasil, impor siswa via Excel, mode ujian ketat`.
- **Test backend** dengan pytest, satu berkas per iterasi fitur
  (`backend/tests/test_iteration<N>.py`) agar regresi lama tetap terjaga.
  Jalankan: `cd /app/backend && python -m pytest tests -q` (±162 test).
- **`memory/PRD.md`** adalah sumber kebenaran produk — tambahkan bagian
  `## Implemented (tanggal) — Iteration N` setiap menyelesaikan fitur.
- **Jangan pernah commit** rahasia: `.env`, `*.key`, `credentials.json`,
  `memory/test_credentials.md` (sudah tercantum di `.gitignore`).
- Dependensi: backend lewat `pip install` lalu `pip freeze > requirements.txt`;
  frontend **wajib** memakai `yarn add` (jangan `npm install`).

---

## Setup & Menjalankan Lokal

### Prasyarat
Python 3.11+, Node 18+ dengan **Yarn**, dan MongoDB yang berjalan.

### 1) Backend

```bash
cd backend
pip install -r requirements.txt      # atau minimal: fastapi uvicorn motor pyjwt bcrypt
                                     # passlib openpyxl pandas reportlab python-dotenv
```

Buat `backend/.env` (tidak ada di repo):

```env
MONGO_URL="mongodb://localhost:27017"
DB_NAME="test_database"
CORS_ORIGINS="*"
JWT_SECRET="<string-acak-panjang>"
ADMIN_EMAIL="admin@sekolah.id"
ADMIN_PASSWORD="<password-admin-awal>"
EMERGENT_LLM_KEY="<kunci-object-storage>"
WEBHOOK_CRON_SECRET="<string-acak>"
```

### 2) Frontend

```bash
cd frontend
yarn install
```

Buat `frontend/.env`:

```env
REACT_APP_BACKEND_URL=https://<host-backend-anda>
WDS_SOCKET_PORT=443
```

### 3) Jalankan

Di platform Emergent kedua service dikelola supervisor:

```bash
sudo supervisorctl restart backend frontend
tail -n 50 /var/log/supervisor/backend.err.log
```

Manual (pengembangan lokal):

```bash
cd backend  && uvicorn server:app --host 0.0.0.0 --port 8001 --reload
cd frontend && yarn start
```

### 4) Seed data demo (opsional, idempoten)

```bash
python scripts/seed_demo.py
```

Menghasilkan kategori, 11 soal, 3 paket, 1 kelas, 3 sesi, akun guru & siswa, serta 2
hasil ujian yang sudah dinilai — agar setiap modul punya data untuk ditampilkan.

Akun admin awal dibuat otomatis saat startup dari `ADMIN_EMAIL` / `ADMIN_PASSWORD`.
Kredensial akun uji lainnya dicatat di `memory/test_credentials.md` (gitignored).

### 5) Jalankan test

```bash
cd backend && python -m pytest tests -q
```

---

<div align="center">
<sub>Dibangun dengan React, FastAPI, dan MongoDB · Dokumentasi produk lengkap ada di <code>memory/PRD.md</code></sub>
</div>
