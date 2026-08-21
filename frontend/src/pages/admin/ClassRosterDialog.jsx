import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import {
  Users, UserPlus, Upload, Download, Search, KeyRound, Pencil, Trash2,
  LogOut, FileSpreadsheet, CheckCircle2, AlertTriangle, Copy, X, Info,
} from "lucide-react";
import api, { apiError } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Badge } from "../../components/ui/badge";
import { Checkbox } from "../../components/ui/checkbox";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../../components/ui/dialog";

const EMPTY_NEW = { name: "", email: "", identifier: "", password: "" };

function slugEmail(name) {
  return (
    name
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9\s]/g, "")
      .trim()
      .replace(/\s+/g, ".") || ""
  );
}

/**
 * Full student-account manager for one class: create login-ready accounts,
 * import from Excel straight into this class, attach existing students,
 * reset passwords and hand out credentials.
 */
export default function ClassRosterDialog({ cls, open, onOpenChange, onChanged }) {
  const [data, setData] = useState({ students: [], available: [] });
  const [loading, setLoading] = useState(false);
  const [q, setQ] = useState("");
  const [mode, setMode] = useState(null); // null | "new" | "attach" | "import"
  const [form, setForm] = useState(EMPTY_NEW);
  const [saving, setSaving] = useState(false);
  const [pick, setPick] = useState([]);
  const [pickQ, setPickQ] = useState("");
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState(null);
  const [created, setCreated] = useState([]); // credentials created in this session
  const [editing, setEditing] = useState(null);
  const [editForm, setEditForm] = useState({ name: "", identifier: "", password: "" });
  const fileRef = useRef();

  const load = async () => {
    if (!cls) return;
    setLoading(true);
    try {
      const { data: d } = await api.get(`/classes/${cls.id}/students`);
      setData(d);
    } catch (e) {
      toast.error(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open && cls) {
      setQ(""); setMode(null); setForm(EMPTY_NEW); setPick([]); setPickQ("");
      setResult(null); setCreated([]); setEditing(null);
      load();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, cls?.id]);

  const students = useMemo(() => {
    const s = q.toLowerCase();
    return (data.students || []).filter(
      (x) =>
        x.name.toLowerCase().includes(s) ||
        x.email.toLowerCase().includes(s) ||
        (x.identifier || "").toLowerCase().includes(s)
    );
  }, [data.students, q]);

  const available = useMemo(() => {
    const s = pickQ.toLowerCase();
    return (data.available || []).filter(
      (x) => x.name.toLowerCase().includes(s) || x.email.toLowerCase().includes(s)
    );
  }, [data.available, pickQ]);

  const refresh = async () => { await load(); onChanged?.(); };

  const createStudent = async () => {
    if (!form.name.trim()) return toast.error("Nama siswa wajib diisi");
    if (!form.email.trim()) return toast.error("Username (email) wajib diisi");
    if ((form.password || "").length < 5) return toast.error("Password minimal 5 karakter");
    setSaving(true);
    try {
      await api.post(`/classes/${cls.id}/students`, {
        name: form.name.trim(),
        email: form.email.trim().toLowerCase(),
        identifier: form.identifier.trim(),
        password: form.password,
      });
      setCreated((c) => [
        { name: form.name.trim(), email: form.email.trim().toLowerCase(), password: form.password },
        ...c,
      ]);
      toast.success(`Akun siswa "${form.name.trim()}" dibuat & bisa langsung login`);
      setForm(EMPTY_NEW);
      await refresh();
    } catch (e) {
      toast.error(apiError(e));
    } finally {
      setSaving(false);
    }
  };

  const attach = async () => {
    if (pick.length === 0) return toast.error("Pilih minimal satu siswa");
    try {
      const { data: r } = await api.post(`/classes/${cls.id}/students/attach`, { student_ids: pick });
      toast.success(`${r.added} siswa ditambahkan ke ${cls.name}`);
      setPick([]); setMode(null);
      await refresh();
    } catch (e) {
      toast.error(apiError(e));
    }
  };

  const removeFromClass = async (s) => {
    if (!window.confirm(`Keluarkan ${s.name} dari kelas ${cls.name}? Akun login tetap ada.`)) return;
    try {
      await api.delete(`/classes/${cls.id}/students/${s.id}`);
      toast.success("Siswa dikeluarkan dari kelas");
      await refresh();
    } catch (e) {
      toast.error(apiError(e));
    }
  };

  const deleteAccount = async (s) => {
    if (!window.confirm(`Hapus akun siswa ${s.name} (${s.email}) secara permanen?`)) return;
    try {
      await api.delete(`/classes/${cls.id}/students/${s.id}?delete_account=true`);
      toast.success("Akun siswa dihapus");
      await refresh();
    } catch (e) {
      toast.error(apiError(e));
    }
  };

  const openEdit = (s) => {
    setEditing(s);
    setEditForm({ name: s.name, identifier: s.identifier || "", password: "" });
  };

  const saveEdit = async () => {
    if (!editForm.name.trim()) return toast.error("Nama wajib diisi");
    if (editForm.password && editForm.password.length < 5)
      return toast.error("Password minimal 5 karakter");
    try {
      const body = { name: editForm.name.trim(), identifier: editForm.identifier.trim() };
      if (editForm.password) body.password = editForm.password;
      await api.put(`/users/${editing.id}`, body);
      if (editForm.password) {
        setCreated((c) => [
          { name: editForm.name.trim(), email: editing.email, password: editForm.password },
          ...c,
        ]);
      }
      toast.success("Data siswa disimpan");
      setEditing(null);
      await refresh();
    } catch (e) {
      toast.error(apiError(e));
    }
  };

  const downloadTemplate = async () => {
    try {
      const res = await api.get("/students/import-template", { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url; a.download = "template_data_siswa.xlsx"; a.click();
      URL.revokeObjectURL(url);
      toast.success("Template terunduh");
    } catch (e) { toast.error(apiError(e)); }
  };

  const importFile = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const fd = new FormData();
    fd.append("file", f);
    fd.append("class_id", cls.id);
    setImporting(true); setResult(null);
    try {
      const { data: r } = await api.post("/students/import", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(r);
      const total = (r.created || 0) + (r.updated || 0);
      if (total > 0) toast.success(`${r.created} siswa baru · ${r.updated} diperbarui`);
      else if (r.errors?.length) toast.warning("Tidak ada data yang berhasil diimpor");
      else toast.info("File tidak memuat data siswa");
      await refresh();
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setImporting(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const exportRoster = async () => {
    try {
      const res = await api.get(`/classes/${cls.id}/students/xlsx`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url; a.download = `akun-siswa-${cls.name}.xlsx`; a.click();
      URL.revokeObjectURL(url);
      toast.success("Daftar akun diunduh");
    } catch (e) { toast.error(apiError(e)); }
  };

  const copyCreds = () => {
    const text = created
      .map((c) => `${c.name}\t${c.email}\t${c.password}`)
      .join("\n");
    navigator.clipboard?.writeText(`Nama\tUsername\tPassword\n${text}`);
    toast.success("Daftar akun baru disalin");
  };

  if (!cls) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-3xl max-h-[92vh] overflow-y-auto bg-card"
        data-testid="class-roster-dialog"
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            Akun Siswa — {cls.name}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-5 py-1">
          <div className="flex items-start gap-2 rounded-md bg-primary/5 border border-primary/15 px-3 py-2.5">
            <Info className="h-4 w-4 text-primary mt-0.5 shrink-0" />
            <p className="text-xs text-muted-foreground leading-relaxed">
              Setiap siswa di kelas ini punya akun login sendiri. Siswa masuk lewat halaman
              login aplikasi memakai <b>Username (email)</b> dan <b>password</b> yang dibuat
              di sini, lalu langsung melihat daftar ujian kelasnya.
            </p>
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              onClick={() => setMode(mode === "new" ? null : "new")}
              data-testid="roster-add-student-btn"
            >
              <UserPlus className="h-4 w-4 mr-1.5" />Tambah Akun Siswa
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setMode(mode === "import" ? null : "import")}
              data-testid="roster-import-btn"
            >
              <Upload className="h-4 w-4 mr-1.5" />Impor Excel ke Kelas Ini
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setMode(mode === "attach" ? null : "attach")}
              data-testid="roster-attach-btn"
            >
              <Users className="h-4 w-4 mr-1.5" />Tambah dari Akun Ada
            </Button>
            <Button size="sm" variant="outline" onClick={exportRoster} data-testid="roster-export-btn">
              <Download className="h-4 w-4 mr-1.5" />Unduh Daftar Akun
            </Button>
          </div>

          {/* Create account */}
          {mode === "new" && (
            <div className="rounded-md border border-border p-4 space-y-3 bg-muted/20" data-testid="roster-new-form">
              <p className="text-sm font-medium">Buat akun siswa baru</p>
              <div className="grid sm:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label>Nama Siswa</Label>
                  <Input
                    value={form.name}
                    onChange={(e) => {
                      const name = e.target.value;
                      setForm((f) => ({
                        ...f,
                        name,
                        email: f.email && f.email !== `${slugEmail(f.name)}@sekolah.id`
                          ? f.email
                          : (slugEmail(name) ? `${slugEmail(name)}@sekolah.id` : ""),
                      }));
                    }}
                    placeholder="Ani Rahmawati"
                    data-testid="roster-name-input"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>NIS / NISN</Label>
                  <Input
                    value={form.identifier}
                    onChange={(e) => setForm({ ...form, identifier: e.target.value })}
                    placeholder="0051234561"
                    data-testid="roster-nis-input"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>Username (Email Login)</Label>
                  <Input
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    placeholder="ani.rahmawati@sekolah.id"
                    data-testid="roster-email-input"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>Password Awal</Label>
                  <div className="flex gap-2">
                    <Input
                      value={form.password}
                      onChange={(e) => setForm({ ...form, password: e.target.value })}
                      placeholder="minimal 5 karakter"
                      data-testid="roster-password-input"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setForm((f) => ({ ...f, password: `siswa${Math.floor(1000 + Math.random() * 9000)}` }))}
                      data-testid="roster-genpass-btn"
                    >
                      Acak
                    </Button>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <Button onClick={createStudent} disabled={saving} data-testid="roster-save-student-btn">
                  {saving ? "Menyimpan..." : "Simpan & Masukkan ke Kelas"}
                </Button>
                <Button variant="ghost" onClick={() => { setMode(null); setForm(EMPTY_NEW); }}>Batal</Button>
              </div>
            </div>
          )}

          {/* Import excel */}
          {mode === "import" && (
            <div className="rounded-md border border-border p-4 space-y-3 bg-muted/20" data-testid="roster-import-panel">
              <p className="text-sm font-medium">Impor siswa dari Excel</p>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Kolom: <b>nama</b> (wajib), <b>username</b> (email login, wajib), <b>password</b>{" "}
                (wajib untuk siswa baru), <b>nis</b> dan <b>kelas</b> (opsional). Baris yang
                kolom <b>kelas</b>-nya kosong otomatis masuk ke <b>{cls.name}</b>. Username yang
                sudah ada akan diperbarui, bukan diduplikasi.
              </p>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" onClick={downloadTemplate} data-testid="roster-template-btn">
                  <FileSpreadsheet className="h-4 w-4 mr-1.5" />Unduh Template
                </Button>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  onChange={importFile}
                  className="hidden"
                  data-testid="roster-file-input"
                />
                <Button onClick={() => fileRef.current?.click()} disabled={importing} data-testid="roster-upload-btn">
                  <Upload className="h-4 w-4 mr-1.5" />{importing ? "Mengimpor..." : "Pilih File & Impor"}
                </Button>
              </div>

              {result && (
                <div className="rounded-md border border-border p-3 space-y-2 bg-card" data-testid="roster-import-result">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <CheckCircle2 className="h-4 w-4 text-primary" />Hasil Impor
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    {[
                      ["Siswa Baru", result.created],
                      ["Diperbarui", result.updated],
                      ["Masuk Kelas", result.added_to_class],
                    ].map(([label, val]) => (
                      <div key={label} className="bg-muted/50 rounded-md py-2">
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
                      <ul className="text-xs text-muted-foreground list-disc pl-5 space-y-0.5 max-h-32 overflow-y-auto">
                        {result.errors.map((er, i) => <li key={i}>{er}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Attach existing */}
          {mode === "attach" && (
            <div className="rounded-md border border-border p-4 space-y-3 bg-muted/20" data-testid="roster-attach-panel">
              <p className="text-sm font-medium">Tambahkan siswa yang sudah punya akun</p>
              <div className="relative">
                <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={pickQ}
                  onChange={(e) => setPickQ(e.target.value)}
                  placeholder="Cari nama atau email..."
                  className="pl-9 bg-card"
                />
              </div>
              <div className="border border-border rounded-md max-h-48 overflow-y-auto divide-y divide-border bg-card">
                {available.length === 0 && (
                  <p className="p-4 text-sm text-muted-foreground">Tidak ada akun siswa lain.</p>
                )}
                {available.map((s) => (
                  <label
                    key={s.id}
                    className="flex items-center gap-3 p-2.5 hover:bg-muted/40 cursor-pointer"
                    data-testid={`roster-pick-${s.id}`}
                  >
                    <Checkbox
                      checked={pick.includes(s.id)}
                      onCheckedChange={() =>
                        setPick((p) => (p.includes(s.id) ? p.filter((x) => x !== s.id) : [...p, s.id]))
                      }
                    />
                    <span className="text-sm">
                      {s.name}
                      <span className="text-muted-foreground"> · {s.email}</span>
                      {s.class_names?.length > 0 && (
                        <Badge variant="outline" className="ml-2 text-[10px]">{s.class_names.join(", ")}</Badge>
                      )}
                    </span>
                  </label>
                ))}
              </div>
              <div className="flex gap-2">
                <Button onClick={attach} data-testid="roster-attach-save-btn">
                  Tambahkan {pick.length > 0 ? `(${pick.length})` : ""}
                </Button>
                <Button variant="ghost" onClick={() => { setMode(null); setPick([]); }}>Batal</Button>
              </div>
            </div>
          )}

          {/* Credentials created in this session */}
          {created.length > 0 && (
            <div className="rounded-md border border-primary/25 bg-primary/5 p-4 space-y-2" data-testid="roster-credentials">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-medium">Akun / password baru (catat sekarang)</p>
                <Button size="sm" variant="outline" onClick={copyCreds}>
                  <Copy className="h-3.5 w-3.5 mr-1.5" />Salin
                </Button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="text-muted-foreground">
                    <tr>
                      <th className="text-left py-1 pr-3">Nama</th>
                      <th className="text-left py-1 pr-3">Username</th>
                      <th className="text-left py-1">Password</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {created.map((c, i) => (
                      <tr key={i}>
                        <td className="py-1.5 pr-3">{c.name}</td>
                        <td className="py-1.5 pr-3 font-mono">{c.email}</td>
                        <td className="py-1.5 font-mono">{c.password}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Roster table */}
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <p className="text-sm font-medium">
                Daftar Siswa{" "}
                <Badge className="bg-primary/10 text-primary border-0 ml-1">
                  {data.students?.length || 0}
                </Badge>
              </p>
              <div className="relative w-full sm:w-64">
                <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Cari siswa..."
                  className="pl-9 h-9"
                  data-testid="roster-search"
                />
              </div>
            </div>

            {loading ? (
              <p className="text-sm text-muted-foreground py-6 text-center">Memuat...</p>
            ) : students.length === 0 ? (
              <div className="border border-dashed border-border rounded-md p-10 text-center text-muted-foreground text-sm" data-testid="roster-empty">
                <Users className="h-8 w-8 mx-auto mb-2 opacity-40" />
                Belum ada akun siswa di kelas ini. Gunakan <b>Tambah Akun Siswa</b> atau{" "}
                <b>Impor Excel</b>.
              </div>
            ) : (
              <div className="border border-border rounded-md overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50 text-xs uppercase tracking-wider text-muted-foreground">
                    <tr>
                      <th className="text-left px-3 py-2 font-semibold">Nama</th>
                      <th className="text-left px-3 py-2 font-semibold hidden sm:table-cell">NIS</th>
                      <th className="text-left px-3 py-2 font-semibold">Username</th>
                      <th className="text-center px-3 py-2 font-semibold hidden sm:table-cell">Ujian</th>
                      <th className="px-3 py-2" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {students.map((s) => (
                      <tr key={s.id} className="hover:bg-muted/30" data-testid={`roster-row-${s.id}`}>
                        <td className="px-3 py-2 font-medium">{s.name}</td>
                        <td className="px-3 py-2 text-muted-foreground hidden sm:table-cell">
                          {s.identifier || "-"}
                        </td>
                        <td className="px-3 py-2 font-mono text-xs">{s.email}</td>
                        <td className="px-3 py-2 text-center text-muted-foreground hidden sm:table-cell">
                          {s.exams_done}
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex items-center justify-end gap-1">
                            <button
                              title="Edit / reset password"
                              onClick={() => openEdit(s)}
                              className="p-1.5 text-muted-foreground hover:text-primary"
                              data-testid={`roster-edit-${s.id}`}
                            >
                              <Pencil className="h-4 w-4" />
                            </button>
                            <button
                              title="Keluarkan dari kelas"
                              onClick={() => removeFromClass(s)}
                              className="p-1.5 text-muted-foreground hover:text-foreground"
                              data-testid={`roster-remove-${s.id}`}
                            >
                              <LogOut className="h-4 w-4" />
                            </button>
                            <button
                              title="Hapus akun"
                              onClick={() => deleteAccount(s)}
                              className="p-1.5 text-muted-foreground hover:text-destructive"
                              data-testid={`roster-delete-${s.id}`}
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Inline edit panel */}
          {editing && (
            <div className="rounded-md border border-border p-4 space-y-3 bg-muted/20" data-testid="roster-edit-panel">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">Edit siswa — {editing.email}</p>
                <button onClick={() => setEditing(null)} className="text-muted-foreground hover:text-foreground">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="grid sm:grid-cols-3 gap-3">
                <div className="space-y-1.5">
                  <Label>Nama</Label>
                  <Input
                    value={editForm.name}
                    onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                    data-testid="roster-edit-name"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>NIS / NISN</Label>
                  <Input
                    value={editForm.identifier}
                    onChange={(e) => setEditForm({ ...editForm, identifier: e.target.value })}
                    data-testid="roster-edit-nis"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>Password Baru (opsional)</Label>
                  <Input
                    value={editForm.password}
                    onChange={(e) => setEditForm({ ...editForm, password: e.target.value })}
                    placeholder="biarkan kosong bila tidak diubah"
                    data-testid="roster-edit-password"
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <Button onClick={saveEdit} data-testid="roster-edit-save">
                  <KeyRound className="h-4 w-4 mr-1.5" />Simpan Perubahan
                </Button>
                <Button variant="ghost" onClick={() => setEditing(null)}>Batal</Button>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} data-testid="roster-close-btn">
            Tutup
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
