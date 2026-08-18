import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, Users, Search, Download } from "lucide-react";
import api, { apiError } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { Badge } from "../../components/ui/badge";
import { Checkbox } from "../../components/ui/checkbox";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../../components/ui/dialog";

const EMPTY = { name: "", description: "", student_ids: [] };

export default function Classes() {
  const [items, setItems] = useState([]);
  const [students, setStudents] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [q, setQ] = useState("");

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

  const filtered = students.filter((s) =>
    s.name.toLowerCase().includes(q.toLowerCase()) || (s.identifier || "").includes(q));

  return (
    <div data-testid="classes-page">
      <div className="flex items-end justify-between mb-8 gap-4 flex-wrap">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">Rombongan Belajar</p>
          <h1 className="font-heading text-3xl sm:text-4xl font-semibold tracking-tight mt-1">Manajemen Kelas</h1>
        </div>
        <Button onClick={openNew} data-testid="add-class-btn"><Plus className="h-4 w-4 mr-2" />Tambah Kelas</Button>
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
              <div className="flex items-center justify-between gap-2">
                <Badge className="bg-primary/10 text-primary border-0">{c.student_count} siswa</Badge>
                <Button size="sm" variant="outline" onClick={() => exportGrades(c)} data-testid={`export-grades-${c.id}`}>
                  <Download className="h-4 w-4 mr-1.5" />Rekap Nilai
                </Button>
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
    </div>
  );
}
