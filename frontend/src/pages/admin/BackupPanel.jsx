import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import {
  DatabaseBackup, Download, Upload, AlertTriangle, CheckCircle2, HardDriveDownload,
} from "lucide-react";
import api, { apiError } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";

const LABELS = {
  users: "Akun (admin, guru, siswa)",
  classes: "Kelas",
  categories: "Kategori materi",
  questions: "Bank soal",
  packages: "Paket soal",
  sessions: "Sesi ujian",
  attempts: "Hasil pengerjaan siswa",
  settings: "Pengaturan sekolah",
  files: "Metadata gambar",
  file_blobs: "Berkas gambar / logo",
};

function human(bytes) {
  if (!bytes) return "0 KB";
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(0)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

/** Full-database backup: download one file, restore it on any server. */
export default function BackupPanel() {
  const [stats, setStats] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [mode, setMode] = useState("merge");
  const [result, setResult] = useState(null);
  const fileRef = useRef();

  const loadStats = () =>
    api.get("/backup/stats").then((r) => setStats(r.data)).catch(() => {});

  useEffect(() => { loadStats(); }, []);

  const exportBackup = async () => {
    setExporting(true);
    try {
      const res = await api.get("/backup/export", { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      const stamp = new Date().toISOString().slice(0, 16).replace(/[:T]/g, "-");
      a.href = url; a.download = `backup-cbt-${stamp}.json.gz`; a.click();
      URL.revokeObjectURL(url);
      toast.success("Backup terunduh — simpan di tempat aman");
    } catch (e) {
      toast.error(apiError(e));
    } finally {
      setExporting(false);
    }
  };

  const importBackup = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const warn = mode === "replace"
      ? `GANTI SEMUA DATA dengan isi file "${f.name}"? Semua data saat ini (siswa, soal, hasil ujian) akan dihapus lebih dulu.`
      : `Gabungkan data dari "${f.name}" ke database saat ini? Data dengan ID sama akan ditimpa.`;
    if (!window.confirm(warn)) {
      if (fileRef.current) fileRef.current.value = "";
      return;
    }
    const fd = new FormData();
    fd.append("file", f);
    fd.append("mode", mode);
    setImporting(true); setResult(null);
    try {
      const { data } = await api.post("/backup/import", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(data);
      toast.success("Backup berhasil dipulihkan");
      loadStats();
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setImporting(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <div className="bg-card border border-border rounded-xl p-6 sm:p-8 mt-6 space-y-6" data-testid="backup-panel">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">Data Sekolah</p>
        <h2 className="font-heading text-2xl font-semibold tracking-tight mt-1">Backup &amp; Pindah Data</h2>
        <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
          Unduh seluruh data sekolah (akun, kelas, bank soal, sesi, hasil ujian, logo, dan
          gambar soal) dalam satu berkas. Berkas ini bisa dipulihkan kapan saja — termasuk
          saat Anda memindahkan aplikasi ke server atau hosting lain.
        </p>
      </div>

      {stats && (
        <div className="rounded-md border border-border overflow-hidden" data-testid="backup-stats">
          <div className="bg-muted/50 px-4 py-2 text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center justify-between">
            <span>Isi backup saat ini</span>
            <span>Ukuran gambar: {human(stats.files_bytes)}</span>
          </div>
          <div className="grid sm:grid-cols-2 divide-y sm:divide-y-0 divide-border">
            {Object.entries(LABELS).map(([key, label]) => (
              <div key={key} className="flex items-center justify-between px-4 py-2 text-sm">
                <span className="text-muted-foreground">{label}</span>
                <Badge variant="outline" className="font-mono">{stats.counts?.[key] ?? 0}</Badge>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <Button onClick={exportBackup} disabled={exporting} data-testid="backup-export-btn">
          <Download className="h-4 w-4 mr-2" />
          {exporting ? "Menyiapkan..." : "Unduh Backup Sekarang"}
        </Button>
        <Button variant="outline" onClick={loadStats} data-testid="backup-refresh-btn">
          <HardDriveDownload className="h-4 w-4 mr-2" />Segarkan Ringkasan
        </Button>
      </div>

      <div className="border-t border-border pt-6 space-y-3">
        <p className="text-sm font-medium flex items-center gap-2">
          <DatabaseBackup className="h-4 w-4 text-primary" />Pulihkan dari berkas backup
        </p>
        <div className="space-y-2">
          {[
            ["merge", "Gabungkan (aman)", "Data dari backup ditambahkan; data dengan ID sama ditimpa. Data lain tetap ada."],
            ["replace", "Ganti semua data", "Semua data saat ini dihapus dulu, lalu diganti isi backup. Untuk pindah server."],
          ].map(([val, title, desc]) => (
            <label
              key={val}
              className={`flex gap-3 rounded-md border p-3 cursor-pointer transition-colors ${
                mode === val ? "border-primary bg-primary/5" : "border-border bg-card hover:border-primary/40"
              }`}
              data-testid={`backup-mode-${val}`}
            >
              <input
                type="radio"
                name="backup-mode"
                className="mt-1"
                checked={mode === val}
                onChange={() => setMode(val)}
              />
              <span>
                <span className="block text-sm font-medium">{title}</span>
                <span className="block text-xs text-muted-foreground">{desc}</span>
              </span>
            </label>
          ))}
        </div>

        {mode === "replace" && (
          <div className="flex items-start gap-2 rounded-md border border-destructive/25 bg-destructive/5 px-3 py-2.5">
            <AlertTriangle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
            <p className="text-xs text-muted-foreground leading-relaxed">
              Mode ini menghapus seluruh data sekarang. Pastikan Anda sudah mengunduh backup
              terbaru. Setelah dipulihkan, gunakan akun admin dari backup tersebut untuk login.
            </p>
          </div>
        )}

        <input
          ref={fileRef}
          type="file"
          accept=".gz,.json"
          onChange={importBackup}
          className="hidden"
          data-testid="backup-file-input"
        />
        <Button
          variant={mode === "replace" ? "destructive" : "outline"}
          onClick={() => fileRef.current?.click()}
          disabled={importing}
          data-testid="backup-import-btn"
        >
          <Upload className="h-4 w-4 mr-2" />
          {importing ? "Memulihkan..." : "Pilih Berkas Backup & Pulihkan"}
        </Button>

        {result && (
          <div className="rounded-md border border-border p-4 space-y-2" data-testid="backup-import-result">
            <div className="flex items-center gap-2 text-sm font-medium">
              <CheckCircle2 className="h-4 w-4 text-primary" />
              Pemulihan selesai (mode: {result.mode === "replace" ? "ganti semua" : "gabungkan"})
            </div>
            {result.exported_at && (
              <p className="text-xs text-muted-foreground">
                Backup dibuat: {new Date(result.exported_at).toLocaleString("id-ID")}
              </p>
            )}
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="text-muted-foreground">
                  <tr>
                    <th className="text-left py-1 pr-3">Data</th>
                    <th className="text-right py-1 pr-3">Baru</th>
                    <th className="text-right py-1">Diperbarui</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {Object.entries(result.result || {}).map(([k, v]) => (
                    <tr key={k}>
                      <td className="py-1.5 pr-3">{LABELS[k] || k}</td>
                      <td className="py-1.5 pr-3 text-right font-mono">{v.inserted}</td>
                      <td className="py-1.5 text-right font-mono">{v.updated}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-muted-foreground">
              Muat ulang halaman agar semua data tampil terbaru.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
