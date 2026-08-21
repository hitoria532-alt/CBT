# Panduan Deploy CBT Ujian Online (Gratis / Murah)

Aplikasi ini terdiri dari 3 bagian, jadi kita pasang di 3 layanan yang punya paket gratis:

| Bagian | Layanan yang dipakai | Paket gratis |
|---|---|---|
| Frontend (React) | **Vercel** | Ya, cukup untuk sekolah |
| Backend (FastAPI) | **Render** (atau Railway) | Ya (Render Free: tidur bila idle) |
| Database (MongoDB) | **MongoDB Atlas** | Ya, 512 MB (M0) |

> Semua file konfigurasi sudah disiapkan di repo: `render.yaml`, `backend/Dockerfile`,
> `backend/requirements-deploy.txt`, `backend/.env.example`, `frontend/vercel.json`,
> `frontend/.env.example`.

Urutan wajib: **Database → Backend → Frontend** (frontend butuh alamat backend).

---

## Langkah 1 — Database: MongoDB Atlas

1. Daftar di https://www.mongodb.com/cloud/atlas → **Create a free cluster (M0)**,
   pilih region terdekat (mis. Singapore).
2. Menu **Database Access** → **Add New Database User**
   - Username: `cbt_admin`, Password: (buat yang kuat, catat)
   - Role: `Read and write to any database`
3. Menu **Network Access** → **Add IP Address** → **Allow access from anywhere**
   (`0.0.0.0/0`). Ini perlu karena IP Render berubah-ubah.
4. Menu **Database** → tombol **Connect** → **Drivers** → salin connection string:
   ```
   mongodb+srv://cbt_admin:PASSWORD@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
   Ganti `PASSWORD` dengan password user tadi. Simpan, ini jadi `MONGO_URL`.

---

## Langkah 2 — Backend: Render

1. Pastikan kode terbaru sudah ada di GitHub (repo `CBT`).
2. Daftar/masuk https://render.com dengan akun GitHub.
3. **New → Web Service** → pilih repository `CBT`, lalu isi:
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements-deploy.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
   > Alternatif lebih cepat: **New → Blueprint** lalu pilih repo ini, Render otomatis
   > membaca `render.yaml`.
4. Bagian **Environment Variables**, tambahkan:

   | Key | Value |
   |---|---|
   | `MONGO_URL` | connection string dari Langkah 1 |
   | `DB_NAME` | `cbt_ujian` |
   | `JWT_SECRET` | string acak panjang (lihat catatan di bawah) |
   | `ADMIN_EMAIL` | `admin@sekolahku.sch.id` |
   | `ADMIN_PASSWORD` | password admin pilihan Anda |
   | `CORS_ORIGINS` | sementara `*`, nanti diganti URL Vercel |
   | `STORAGE_MODE` | `mongo` |
   | `INTERNAL_CRON_MINUTES` | `5` |
   | `PYTHON_VERSION` | `3.11.9` |

   Membuat `JWT_SECRET`:
   ```bash
   python -c "import secrets;print(secrets.token_urlsafe(48))"
   ```
5. **Create Web Service** → tunggu build selesai. Catat URL-nya, mis.
   `https://cbt-backend.onrender.com`.
6. Uji: buka `https://cbt-backend.onrender.com/api/settings/school` di browser —
   harus muncul JSON (`{"name":"", ... "theme_color":"157 35% 18%"}`).
   Akun admin otomatis dibuat saat backend pertama kali start.

> **Catatan paket Free Render**: service "tidur" setelah ±15 menit tanpa akses, dan
> permintaan pertama sesudahnya butuh ±30–50 detik. Untuk hari-H ujian sebaiknya
> naik ke paket berbayar termurah (± $7/bulan) atau buka aplikasi beberapa menit
> sebelum ujian mulai agar sudah "bangun".

---

## Langkah 3 — Frontend: Vercel

1. Daftar/masuk https://vercel.com dengan akun GitHub.
2. **Add New → Project** → pilih repo `CBT` → isi:
   - **Root Directory**: `frontend`
   - **Framework Preset**: `Create React App` (atau *Other*)
   - **Build Command**: `yarn build`
   - **Output Directory**: `build`
3. **Environment Variables** → tambahkan:

   | Key | Value |
   |---|---|
   | `REACT_APP_BACKEND_URL` | `https://cbt-backend.onrender.com` (tanpa `/` di akhir, tanpa `/api`) |

4. **Deploy** → selesai, dapat URL mis. `https://cbt-sekolah.vercel.app`.
5. Kembali ke Render → ubah `CORS_ORIGINS` menjadi URL Vercel tadi, mis.
   `https://cbt-sekolah.vercel.app` → **Save** (service restart otomatis).
6. Buka URL Vercel → login dengan `ADMIN_EMAIL` / `ADMIN_PASSWORD`.

---

## Langkah 4 — Domain sendiri (opsional)

- **Vercel**: Project → *Settings → Domains* → tambahkan `cbt.sekolahku.sch.id`,
  lalu buat record `CNAME` ke `cname.vercel-dns.com` di penyedia domain Anda.
- Setelah domain aktif, tambahkan domain itu ke `CORS_ORIGINS` di Render
  (boleh beberapa, pisahkan dengan koma).

---

## Langkah 5 — Memindahkan data dari aplikasi lama (opsional)

GitHub hanya menyimpan **kode**, bukan isi database. Cara termudah memindahkan data:

**Cara A — lewat aplikasi (disarankan, tanpa tool tambahan)**
1. Di aplikasi **lama**: masuk sebagai admin → *Pengaturan Sekolah* → **Backup & Pindah Data** →
   **Unduh Backup Sekarang** (menghasilkan satu berkas `backup-cbt-*.json.gz` berisi akun,
   kelas, bank soal, sesi, hasil ujian, logo, dan gambar soal).
2. Di aplikasi **baru** (hasil deploy): login admin → *Pengaturan Sekolah* →
   **Backup & Pindah Data** → pilih mode **Ganti semua data** → unggah berkas backup.
3. Setelah pemulihan, login memakai akun admin/siswa dari backup (password ikut terbawa).

**Cara B — `mongodump` / `mongorestore`**

> Aplikasi ini sudah disetel `STORAGE_MODE=mongo` juga di preview, sehingga logo
> sekolah dan gambar soal tersimpan di dalam MongoDB — ikut terbawa saat `mongodump`,
> tidak ada file yang tertinggal.

```bash
# dari sumber (mis. mongodb lokal Emergent)
mongodump --uri="mongodb://localhost:27017" --db=test_database --out=./dump

# ke MongoDB Atlas
mongorestore --uri="mongodb+srv://cbt_admin:PASSWORD@cluster0.xxxxx.mongodb.net" \
  --nsFrom="test_database.*" --nsTo="cbt_ujian.*" ./dump
```

---

## Penjelasan variabel penting

| Variabel | Fungsi |
|---|---|
| `MONGO_URL` | koneksi database |
| `DB_NAME` | nama database |
| `JWT_SECRET` | kunci token login — **jangan diganti sembarangan**, semua sesi login akan logout |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | akun admin yang di-seed setiap backend start; ubah nilainya = password admin ikut berubah |
| `CORS_ORIGINS` | daftar alamat frontend yang diizinkan memanggil API |
| `STORAGE_MODE` | `mongo` = gambar soal & logo disimpan di MongoDB (untuk self-hosting), `emergent` = pakai object storage Emergent || `INTERNAL_CRON_MINUTES` | tiap N menit aplikasi menutup otomatis ujian yang waktunya sudah habis (`0` = mati) |

---

## Ceklis setelah deploy

- [ ] `GET /api/settings/school` di URL backend membalas JSON
- [ ] Bisa login sebagai admin di URL Vercel
- [ ] Buat kelas → Akun Siswa → tambah 1 siswa → siswa bisa login
- [ ] Unggah logo sekolah di *Pengaturan Sekolah* dan gambar muncul (uji `STORAGE_MODE=mongo`)
- [ ] Unduh *Rapor* PDF dan *Rekap* Excel dari halaman kelas
- [ ] Buat sesi ujian singkat, kerjakan sebagai siswa, cek nilai muncul di *Hasil & Koreksi*

---

## Masalah yang sering terjadi

| Gejala | Penyebab & solusi |
|---|---|
| Halaman login tampil, tapi login gagal / "Network Error" | `REACT_APP_BACKEND_URL` salah (ada `/` atau `/api` di akhir), atau `CORS_ORIGINS` belum berisi URL Vercel |
| Refresh halaman `/admin/kelas` jadi 404 di Vercel | `frontend/vercel.json` (rewrite ke `index.html`) belum ikut ter-deploy |
| Login lambat ±40 detik di akses pertama | Render Free sedang "tidur" — normal; naikkan paket bila dipakai serentak |
| Gambar soal/logo tidak tampil | `STORAGE_MODE` belum diisi `mongo` pada deployment self-host |
| Ujian tidak tertutup otomatis saat waktu habis | `INTERNAL_CRON_MINUTES` masih `0` |
| `Unable to connect to MongoDB` | Network Access Atlas belum `0.0.0.0/0`, atau password di connection string mengandung karakter khusus (harus di-URL-encode) |
