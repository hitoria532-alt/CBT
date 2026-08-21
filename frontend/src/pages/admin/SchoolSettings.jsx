import { useEffect, useState, useRef } from "react";
import { toast } from "sonner";
import { Building2, Upload, X, Check, ShieldCheck } from "lucide-react";
import api, { apiError, fileUrl } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import BackupPanel from "./BackupPanel";

export const THEMES = [
  { id: "157 35% 18%", name: "Hijau Forest", hex: "#1e3a30" },
  { id: "215 60% 30%", name: "Biru", hex: "#1f4e8c" },
  { id: "265 45% 40%", name: "Ungu", hex: "#5b3a94" },
  { id: "0 60% 40%", name: "Merah", hex: "#a32626" },
  { id: "200 70% 30%", name: "Teal", hex: "#106688" },
  { id: "25 60% 35%", name: "Cokelat", hex: "#8a4b1e" },
];

export const DEFAULT_THEME = THEMES[0].id;

/** Accepts only a valid Tailwind HSL triplet like "157 35% 18%". */
export function normalizeTheme(value) {
  if (typeof value !== "string") return null;
  const v = value.trim();
  if (/^-?\d+(\.\d+)?\s+\d+(\.\d+)?%\s+\d+(\.\d+)?%$/.test(v)) return v;
  // Legacy/invalid values (e.g. "green", "#1e3a30") -> try to map by name/hex.
  const byName = THEMES.find(
    (t) => t.hex.toLowerCase() === v.toLowerCase() || t.name.toLowerCase() === v.toLowerCase()
  );
  if (byName) return byName.id;
  const legacy = { green: THEMES[0].id, blue: THEMES[1].id, purple: THEMES[2].id, red: THEMES[3].id, teal: THEMES[4].id, brown: THEMES[5].id };
  return legacy[v.toLowerCase()] || null;
}

export function applyTheme(hsl) {
  const safe = normalizeTheme(hsl) || DEFAULT_THEME;
  document.documentElement.style.setProperty("--primary", safe);
  document.documentElement.style.setProperty("--ring", safe);
}

export default function SchoolSettings() {
  const [form, setForm] = useState({ name: "", address: "", logo_path: null, theme_color: null });
  const [uploading, setUploading] = useState(false);
  const [lock, setLock] = useState({ enabled: true, max_violations: 3 });
  const [savingLock, setSavingLock] = useState(false);
  const imgRef = useRef();

  useEffect(() => {
    api.get("/settings/school").then((r) => setForm(r.data));
    api.get("/settings/exam-lock").then((r) => setLock(r.data)).catch(() => {});
  }, []);

  const saveLock = async () => {
    setSavingLock(true);
    try {
      const { data } = await api.put("/settings/exam-lock", {
        enabled: Boolean(lock.enabled),
        max_violations: Number(lock.max_violations) || 3,
      });
      setLock(data);
      toast.success("Pengaturan mode ujian ketat disimpan");
    } catch (e) { toast.error(apiError(e)); }
    finally { setSavingLock(false); }
  };

  const upload = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const fd = new FormData(); fd.append("file", f);
    setUploading(true);
    try {
      const { data } = await api.post("/uploads/image", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setForm((p) => ({ ...p, logo_path: data.path }));
      toast.success("Logo terunggah");
    } catch (err) { toast.error(apiError(err)); }
    finally { setUploading(false); if (imgRef.current) imgRef.current.value = ""; }
  };

  const save = async () => {
    try {
      await api.put("/settings/school", form);
      applyTheme(form.theme_color);
      toast.success("Pengaturan sekolah disimpan");
    } catch (e) { toast.error(apiError(e)); }
  };

  const logoSrc = form.logo_path ? fileUrl(form.logo_path) : "/school-logo.png";

  return (
    <div className="max-w-2xl" data-testid="school-settings-page">
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">Konfigurasi</p>
      <h1 className="font-heading text-3xl sm:text-4xl font-semibold tracking-tight mt-1 mb-8">Pengaturan Sekolah</h1>

      <div className="bg-card border border-border rounded-xl p-6 space-y-6">
        <div className="flex items-center gap-5">
          <div className="h-20 w-20 rounded-xl border border-border bg-muted/40 flex items-center justify-center overflow-hidden shrink-0">
            <img src={logoSrc} alt="Logo" className="h-16 w-16 object-contain" data-testid="settings-logo-preview" />
          </div>
          <div className="flex gap-2">
            <input ref={imgRef} type="file" accept="image/*" onChange={upload} className="hidden" data-testid="logo-input" />
            <Button variant="outline" onClick={() => imgRef.current?.click()} disabled={uploading} data-testid="upload-logo-btn">
              <Upload className="h-4 w-4 mr-2" />{uploading ? "Mengunggah..." : "Unggah Logo"}
            </Button>
            {form.logo_path && (
              <Button variant="ghost" onClick={() => setForm({ ...form, logo_path: null })}><X className="h-4 w-4 mr-1" />Hapus</Button>
            )}
          </div>
        </div>

        <div className="space-y-2">
          <Label>Nama Sekolah</Label>
          <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="SMA Negeri 1" data-testid="school-name-input" />
        </div>
        <div className="space-y-2">
          <Label>Alamat Sekolah</Label>
          <Textarea value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} rows={2} placeholder="Jl. Pendidikan No. 1, Kota" data-testid="school-address-input" />
        </div>

        <div className="space-y-2">
          <Label>Tema Warna Dashboard</Label>
          <div className="flex flex-wrap gap-3" data-testid="theme-options">
            {THEMES.map((t) => (
              <button key={t.id} onClick={() => setForm({ ...form, theme_color: t.id })}
                data-testid={`theme-${t.hex}`}
                className={`h-11 w-11 rounded-full flex items-center justify-center transition-transform hover:scale-110 ${form.theme_color === t.id ? "ring-2 ring-offset-2 ring-foreground" : ""}`}
                style={{ background: t.hex }} title={t.name}>
                {form.theme_color === t.id && <Check className="h-5 w-5 text-white" />}
              </button>
            ))}
          </div>
        </div>

        <Button onClick={save} data-testid="save-school-btn" className="w-full sm:w-auto"><Building2 className="h-4 w-4 mr-2" />Simpan Pengaturan</Button>
      </div>

      <div className="bg-card border border-border rounded-xl p-6 sm:p-8 mt-6 space-y-6" data-testid="exam-lock-settings">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">Keamanan Ujian</p>
          <h2 className="font-heading text-2xl font-semibold tracking-tight mt-1">Mode Ujian Ketat</h2>
          <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
            Saat ujian berlangsung, layar siswa dibuat penuh dan setiap kali siswa pindah tab,
            keluar aplikasi, atau keluar dari layar penuh akan dicatat sebagai pelanggaran.
            Setelah batas terlampaui, jawaban dikumpulkan otomatis dan guru dapat melihat
            catatannya di Hasil &amp; Koreksi.
          </p>
        </div>

        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={Boolean(lock.enabled)}
            onChange={(e) => setLock({ ...lock, enabled: e.target.checked })}
            className="accent-[hsl(var(--primary))] h-4 w-4 mt-0.5"
            data-testid="lock-enabled-input"
          />
          <span className="text-sm">
            Aktifkan mode ujian ketat untuk semua sesi
            <span className="block text-xs text-muted-foreground mt-0.5">
              Bila dimatikan, ujian berjalan seperti biasa tanpa layar penuh dan tanpa pencatatan pelanggaran.
            </span>
          </span>
        </label>

        <div className="space-y-2 max-w-xs">
          <Label>Batas pelanggaran sebelum kumpul otomatis</Label>
          <Input
            type="number" min="1" max="20"
            value={lock.max_violations}
            onChange={(e) => setLock({ ...lock, max_violations: e.target.value })}
            data-testid="max-violations-input"
          />
          <p className="text-xs text-muted-foreground">
            Disarankan 3. Siswa mendapat peringatan pada setiap pelanggaran sebelum batas ini tercapai.
          </p>
        </div>

        <div className="rounded-md bg-muted/50 p-4 text-xs text-muted-foreground leading-relaxed">
          <b className="text-foreground">Catatan penting:</b> aplikasi web tidak dapat mengunci HP
          sepenuhnya seperti aplikasi Android. Layar penuh berfungsi pada Android Chrome, sedangkan
          iPhone/Safari tidak mendukung layar penuh — namun deteksi keluar aplikasi tetap berjalan
          di semua perangkat.
        </div>

        <Button onClick={saveLock} disabled={savingLock} data-testid="save-lock-btn" className="w-full sm:w-auto">
          <ShieldCheck className="h-4 w-4 mr-2" />{savingLock ? "Menyimpan..." : "Simpan Mode Ujian"}
        </Button>
      </div>

      <BackupPanel />
    </div>
  );
}
