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
