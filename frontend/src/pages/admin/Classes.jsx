import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import {
  Plus, Pencil, Trash2, Users, Search, Download, FileText, Upload,
  FileSpreadsheet, CheckCircle2, AlertTriangle, KeyRound, IdCard, RefreshCw,
  ChevronDown,
} from "lucide-react";
import api, { apiError } from "../../lib/api";
import { useAuth } from "../../context/AuthContext";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { Badge } from "../../components/ui/badge";
import { Checkbox } from "../../components/ui/checkbox";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../../components/ui/dialog";
import {
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator,
} from "../../components/ui/dropdown-menu";

const EMPTY = { name: "", description: "", student_ids: [] };

export default function Classes() {
  const [items, setItems] = useState([]);
  const [students, setStudents] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [q, setQ] = useState("");
  const [importOpen, setImportOpen] = useState(false);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState(null);
  const [accountBusy, setAccountBusy] = useState(false);
  const fileRef = useRef();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const load = () => api.get("/classes").then((r) => setItems(r.data));
  useEffect(() => {
    load();
    api.get("/users?role=siswa").then((r) => setStudents(r.data));
  }, []);

  const openNew = () => { setEditing(null); setForm(EMPTY); setQ(""); setOpen(true); };
  const openEdit = (c) => {
    setEditing(c);
    setForm({ name: c.name, description: c.description || "", student_ids: c.student_ids || [] });
    setQ(""); setOpen(true);
  };

  const toggle = (id) => setForm((f) => ({
    ...f, student_ids: f.student_ids.includes(id) ? f.student_ids.filter((x) => x !== id) : [...f.student_ids, id],
  }));

  const save = async () => {
    if (!form.name.trim()) return toast.error("Nama kelas wajib diisi");
    try {
      if (editing) await api.put(`/classes/${editing.id}`, form);
      else await api.post("/classes", form);
      toast.success("Kelas disimpan"); setOpen(false); load();
    } catch (e) { toast.error(apiError(e)); }
  };

  const remove = async (c) => {
    if (!window.confirm(`Hapus kelas "${c.name}"?`)) return;
    await api.delete(`/classes/${c.id}`); toast.success("Kelas dihapus"); load();
  };

  const exportGrades = async (c) => {
    try {
      const res = await api.get(`/export/class/${c.id}/xlsx`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a"); a.href = url; a.download = `rekap-nilai-${c.name}.xlsx`; a.click();
      toast.success("Rekap nilai diunduh");
    } catch (e) { toast.error(apiError(e)); }
  };

  const downloadClassReport = async (c) => {
    try {
      const res = await api.get(`/report/class/${c.id}/pdf`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a"); a.href = url; a.download = `rapor-kelas-${c.name}.pdf`; a.click();
      toast.success("Rapor kelas diunduh");
    } catch (e) { toast.error(apiError(e)); }
  };

  const downloadStudentTemplate = async () => {
    try {
      const res = await api.get("/students/import-template", { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url; a.download = "template_data_siswa.xlsx"; a.click();
      URL.revokeObjectURL(url);
      toast.success("Template terunduh");
    } catch (e) { toast.error(apiError(e)); }
  };

  const importStudents = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const fd = new FormData();
    fd.append("file", f);
    setImporting(true); setResult(null);
    try {
      const { data } = await api.post("/students/import", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(data);
      const total = (data.created || 0) + (data.updated || 0);
      if (total > 0) toast.success(`${data.created} siswa baru · ${data.updated} diperbarui`);
      else if (data.errors?.length) toast.warning("Tidak ada data yang berhasil diimpor");
      else toast.info("File tidak memuat data siswa");
      load();
      api.get("/users?role=siswa").then((r) => setStudents(r.data));
    } catch (err) { toast.error(apiError(err)); }
    finally { setImporting(false); if (fileRef.current) fileRef.current.value = ""; }
  };

  const openImport = () => { setResult(null); setImportOpen(true); };

  // ---------------------------------------------------------------- ekspor akun login
  const RESET_WARNING =
    "Password lama semua siswa di daftar ini akan DIGANTI dan tidak berlaku lagi.\n\n" +
    "Lanjutkan membuat password baru lalu mengunduh berkasnya?";

  const downloadFile = async (url, filename, okMsg) => {
    setAccountBusy(true);
    try {
      const res = await api.get(url, { responseType: "blob" });
      const objUrl = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = objUrl; a.download = filename; a.click();
      URL.revokeObjectURL(objUrl);
      toast.success(okMsg);
    } catch (e) {
      toast.error(apiError(e));
    } finally {
      setAccountBusy(false);
    }
  };

  const exportAccounts = (c, { pdf = false, reset = false } = {}) => {
    if (reset && !window.confirm(RESET_WARNING)) return;
    const q = reset ? "?reset=true" : "";
    const base = c
      ? `/export/class/${c.id}/accounts/${pdf ? "pdf" : "xlsx"}${q}`
      : `/export/accounts/${pdf ? "pdf" : "xlsx"}${q}`;
    const scope = c ? c.name : "semua-kelas";
    const name = pdf
      ? `kartu-login-${scope}.pdf`
      : `akun-siswa-${scope}.xlsx`;
    downloadFile(
      base,
      name.replace(/\s+/g, "_"),
      reset ? "Password baru dibuat & berkas diunduh" : "Berkas akun diunduh",
    );
  };

  const AccountMenu = ({ cls, size = "sm", label = "Akun" }) => (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          size={size}
          variant="outline"
          disabled={accountBusy}
          data-testid={cls ? `accounts-menu-${cls.id}` : "accounts-menu-all"}
        >
          <KeyRound className="h-4 w-4 mr-1.5" />{label}
          <ChevronDown className="h-3.5 w-3.5 ml-1 opacity-60" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-72 bg-card">
        <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">
          {cls ? cls.name : "Semua kelas"} — akun siap login
        </DropdownMenuLabel>
        <DropdownMenuItem
          onClick={() => exportAccounts(cls)}
          data-testid={cls ? `export-accounts-xlsx-${cls.id}` : "export-accounts-xlsx-all"}
        >
          <FileSpreadsheet className="h-4 w-4 mr-2" />Ekspor Akun (Excel)
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => exportAccounts(cls, { pdf: true })}
          data-testid={cls ? `export-accounts-pdf-${cls.id}` : "export-accounts-pdf-all"}
        >
          <IdCard className="h-4 w-4 mr-2" />Kartu Login Siap Potong (PDF)
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">
          Paksa password baru
        </DropdownMenuLabel>
        <DropdownMenuItem
          onClick={() => exportAccounts(cls, { reset: true })}
          className="text-accent focus:text-accent"
          data-testid={cls ? `reset-accounts-xlsx-${cls.id}` : "reset-accounts-xlsx-all"}
        >
          <RefreshCw className="h-4 w-4 mr-2" />Reset &amp; Ekspor (Excel)
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => exportAccounts(cls, { pdf: true, reset: true })}
          className="text-accent focus:text-accent"
          data-testid={cls ? `reset-accounts-pdf-${cls.id}` : "reset-accounts-pdf-all"}
        >
          <RefreshCw className="h-4 w-4 mr-2" />Reset &amp; Ekspor Kartu (PDF)
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );

  const filtered = students.filter((s) =>
    s.name.toLowerCase().includes(q.toLowerCase()) || (s.identifier || "").includes(q));

  return (
    <div data-testid="classes-page">
      <div className="flex items-end justify-between mb-8 gap-4 flex-wrap">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">Rombongan Belajar</p>
          <h1 className="font-heading text-3xl sm:text-4xl font-semibold tracking-tight mt-1">Manajemen Kelas</h1>
        </div>
        <div className="flex gap-3 flex-wrap">
          {isAdmin && <AccountMenu cls={null} size="default" label="Akun Semua Kelas" />}
          {isAdmin && (
            <Button variant="outline" onClick={openImport} data-testid="import-students-btn">
              <Upload className="h-4 w-4 mr-2" />Impor Siswa
            </Button>
          )}
          <Button onClick={openNew} data-testid="add-class-btn"><Plus className="h-4 w-4 mr-2" />Tambah Kelas</Button>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="border border-dashed border-border rounded-md p-16 text-center text-muted-foreground">
          <Users className="h-10 w-10 mx-auto mb-3 opacity-40" />Belum ada kelas.
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((c) => (
            <div key={c.id} className="bg-card border border-border rounded-md p-6 hover:shadow-sm transition-shadow" data-testid={`class-${c.id}`}>
              <div className="flex items-start justify-between">
                <h3 className="font-heading text-lg font-medium">{c.name}</h3>
                <div className="flex gap-1">
                  <button onClick={() => openEdit(c)} className="text-muted-foreground hover:text-primary p-1"><Pencil className="h-4 w-4" /></button>
                  <button onClick={() => remove(c)} className="text-muted-foreground hover:text-destructive p-1"><Trash2 className="h-4 w-4" /></button>
                </div>
              </div>
              <p className="text-sm text-muted-foreground mt-1 mb-4">{c.description || "Tanpa deskripsi"}</p>
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <Badge className="bg-primary/10 text-primary border-0">{c.student_count} siswa</Badge>
                <div className="flex gap-2 flex-wrap">
                  <Button size="sm" variant="outline" onClick={() => exportGrades(c)} data-testid={`export-grades-${c.id}`}>
                    <Download className="h-4 w-4 mr-1.5" />Rekap
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => downloadClassReport(c)} data-testid={`class-report-${c.id}`}>
                    <FileText className="h-4 w-4 mr-1.5" />Rapor
                  </Button>
                  {isAdmin && <AccountMenu cls={c} />}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{editing ? "Edit Kelas" : "Tambah Kelas"}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Nama Kelas</Label>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Kelas X IPA 1" data-testid="class-name-input" />
            </div>
            <div className="space-y-2">
              <Label>Deskripsi</Label>
              <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={2} />
            </div>
            <div className="space-y-2">
              <Label>Anggota Siswa ({form.student_ids.length} dipilih)</Label>
              <div className="relative">
                <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cari siswa..." className="pl-9" />
              </div>
              <div className="border border-border rounded-md max-h-52 overflow-y-auto divide-y divide-border">
                {filtered.length === 0 && <p className="p-4 text-sm text-muted-foreground">Tidak ada siswa.</p>}
                {filtered.map((s) => (
                  <label key={s.id} className="flex items-center gap-3 p-2.5 hover:bg-muted/40 cursor-pointer" data-testid={`pick-student-${s.id}`}>
                    <Checkbox checked={form.student_ids.includes(s.id)} onCheckedChange={() => toggle(s.id)} />
                    <span className="text-sm">{s.name} {s.identifier && <span className="text-muted-foreground">· {s.identifier}</span>}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Batal</Button>
            <Button onClick={save} data-testid="save-class-btn">Simpan</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={importOpen} onOpenChange={setImportOpen}>
        <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>Impor Siswa dari Excel</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <p className="text-sm text-muted-foreground leading-relaxed">
              Unggah file <b>Excel (.xlsx)</b> atau <b>CSV</b> berisi data siswa. Akun login siswa
              dibuat otomatis, dan siswa langsung dimasukkan ke kelasnya.
            </p>

            <div className="rounded-md border border-border overflow-hidden">
              <div className="bg-muted/50 px-4 py-2 text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Kolom yang dibutuhkan
              </div>
              <table className="w-full text-xs">
                <tbody className="divide-y divide-border">
                  {[
                    ["nama", "Nama lengkap siswa", "Wajib"],
                    ["kelas", "Nama kelas / rombel — dibuat otomatis bila belum ada", "Opsional"],
                    ["nis", "NIS / NISN siswa", "Opsional"],
                    ["username", "Email untuk login siswa, mis. ani@sekolah.id", "Wajib"],
                    ["password", "Password awal login, minimal 5 karakter", "Wajib"],
                  ].map(([col, desc, req]) => (
                    <tr key={col}>
                      <td className="px-4 py-2 font-mono font-medium whitespace-nowrap align-top">{col}</td>
                      <td className="px-2 py-2 text-muted-foreground">{desc}</td>
                      <td className="px-4 py-2 text-right whitespace-nowrap">
                        <Badge variant="outline" className="text-[10px]">{req}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="text-xs text-muted-foreground">
              Bila <b>username</b> sudah terdaftar, data siswa akan diperbarui — bukan diduplikasi.
              Template sudah berisi lembar <b>Petunjuk</b> dan contoh pengisian.
            </p>

            <Button variant="outline" onClick={downloadStudentTemplate} className="w-full" data-testid="download-student-template-btn">
              <FileSpreadsheet className="h-4 w-4 mr-2" />Unduh Template Excel
            </Button>
            <input ref={fileRef} type="file" accept=".xlsx,.xls,.csv" onChange={importStudents} className="hidden" data-testid="student-file-input" />
            <Button onClick={() => fileRef.current?.click()} disabled={importing} className="w-full" data-testid="upload-students-btn">
              <Upload className="h-4 w-4 mr-2" />{importing ? "Mengimpor..." : "Pilih File & Impor"}
            </Button>

            {result && (
              <div className="rounded-md border border-border p-4 space-y-3" data-testid="import-result">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <CheckCircle2 className="h-4 w-4 text-primary" />Hasil Impor
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  {[
                    ["Siswa Baru", result.created],
                    ["Diperbarui", result.updated],
                    ["Masuk Kelas", result.added_to_class],
                  ].map(([label, val]) => (
                    <div key={label} className="bg-muted/40 rounded-md py-2">
                      <p className="font-heading text-xl font-semibold">{val ?? 0}</p>
                      <p className="text-[11px] text-muted-foreground">{label}</p>
                    </div>
                  ))}
                </div>
                {result.classes_created?.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    Kelas baru dibuat: <b>{result.classes_created.join(", ")}</b>
                  </p>
                )}
                {result.errors?.length > 0 && (
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 text-sm font-medium text-destructive">
                      <AlertTriangle className="h-4 w-4" />{result.errors.length} baris dilewati
                    </div>
                    <ul className="text-xs text-muted-foreground list-disc pl-5 space-y-0.5 max-h-40 overflow-y-auto">
                      {result.errors.map((er, i) => <li key={i}>{er}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setImportOpen(false)}>Tutup</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
