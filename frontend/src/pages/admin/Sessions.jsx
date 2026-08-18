import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, CalendarClock } from "lucide-react";
import api, { apiError } from "../../lib/api";
import { fmtDateTime, toLocalInput, fromLocalInput, STATUS_LABEL } from "../../lib/utils2";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Badge } from "../../components/ui/badge";
import { Checkbox } from "../../components/ui/checkbox";
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "../../components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../../components/ui/dialog";

const EMPTY = { title: "", package_id: "", start_time: "", end_time: "", duration_minutes: 60, kkm: 75, class_ids: [] };

const statusColor = {
  akan_datang: "bg-secondary/20 text-secondary-foreground",
  berlangsung: "bg-primary/10 text-primary",
  selesai: "bg-muted text-muted-foreground",
};

export default function Sessions() {
  const [items, setItems] = useState([]);
  const [packages, setPackages] = useState([]);
  const [classes, setClasses] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);

  const load = () => api.get("/sessions").then((r) => setItems(r.data));
  useEffect(() => {
    load();
    api.get("/packages").then((r) => setPackages(r.data));
    api.get("/classes").then((r) => setClasses(r.data));
  }, []);

  const openNew = () => { setEditing(null); setForm(EMPTY); setOpen(true); };
  const openEdit = (s) => {
    setEditing(s);
    setForm({ title: s.title, package_id: s.package_id,
      start_time: toLocalInput(s.start_time), end_time: toLocalInput(s.end_time),
      duration_minutes: s.duration_minutes, kkm: s.kkm, class_ids: s.class_ids || [] });
    setOpen(true);
  };

  const toggleClass = (id) => setForm((f) => ({
    ...f, class_ids: f.class_ids.includes(id) ? f.class_ids.filter((x) => x !== id) : [...f.class_ids, id],
  }));

  const save = async () => {
    if (!form.title.trim() || !form.package_id || !form.start_time || !form.end_time)
      return toast.error("Lengkapi semua field");
    const payload = {
      title: form.title, package_id: form.package_id,
      start_time: fromLocalInput(form.start_time), end_time: fromLocalInput(form.end_time),
      duration_minutes: Number(form.duration_minutes), kkm: Number(form.kkm), class_ids: form.class_ids,
    };
    try {
      if (editing) await api.put(`/sessions/${editing.id}`, payload);
      else await api.post("/sessions", payload);
      toast.success("Sesi disimpan"); setOpen(false); load();
    } catch (e) { toast.error(apiError(e)); }
  };

  const remove = async (s) => {
    if (!window.confirm(`Hapus sesi "${s.title}"?`)) return;
    await api.delete(`/sessions/${s.id}`); toast.success("Sesi dihapus"); load();
  };

  return (
    <div data-testid="sessions-page">
      <div className="flex items-end justify-between mb-8 gap-4 flex-wrap">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">Jadwal</p>
          <h1 className="font-heading text-3xl sm:text-4xl font-semibold tracking-tight mt-1">Sesi Pelaksanaan</h1>
        </div>
        <Button onClick={openNew} data-testid="add-session-btn"><Plus className="h-4 w-4 mr-2" />Tambah Sesi</Button>
      </div>

      {items.length === 0 ? (
        <div className="border border-dashed border-border rounded-md p-16 text-center text-muted-foreground">
          <CalendarClock className="h-10 w-10 mx-auto mb-3 opacity-40" />Belum ada sesi ujian.
        </div>
      ) : (
        <div className="space-y-4">
          {items.map((s) => (
            <div key={s.id} className="bg-card border border-border rounded-md p-6 flex items-center justify-between gap-4 flex-wrap" data-testid={`session-${s.id}`}>
              <div className="min-w-0">
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  <h3 className="font-heading text-lg font-medium">{s.title}</h3>
                  <Badge className={`${statusColor[s.status]} border-0`}>{STATUS_LABEL[s.status]}</Badge>
                </div>
                <div className="text-sm text-muted-foreground space-y-0.5">
                  <p>Paket: <span className="text-foreground">{s.package_title}</span> · {s.question_count} soal</p>
                  <p>{fmtDateTime(s.start_time)} — {fmtDateTime(s.end_time)}</p>
                  <p>Durasi {s.duration_minutes} menit · KKM {s.kkm}</p>
                  <p>Kelas: {s.class_names?.length ? s.class_names.join(", ") : "Semua siswa"}</p>
                </div>
              </div>
              <div className="flex gap-1">
                <button onClick={() => openEdit(s)} className="text-muted-foreground hover:text-primary p-1"><Pencil className="h-4 w-4" /></button>
                <button onClick={() => remove(s)} className="text-muted-foreground hover:text-destructive p-1"><Trash2 className="h-4 w-4" /></button>
              </div>
            </div>
          ))}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editing ? "Edit Sesi" : "Tambah Sesi Ujian"}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Judul Sesi</Label>
              <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="UAS Matematika Kelas X" data-testid="session-title-input" />
            </div>
            <div className="space-y-2">
              <Label>Paket Soal</Label>
              <Select value={form.package_id} onValueChange={(v) => setForm({ ...form, package_id: v })}>
                <SelectTrigger data-testid="session-package-select"><SelectValue placeholder="Pilih paket" /></SelectTrigger>
                <SelectContent>
                  {packages.map((p) => <SelectItem key={p.id} value={p.id}>{p.title} ({p.question_count} soal)</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Waktu Mulai</Label>
                <Input type="datetime-local" value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} data-testid="session-start-input" />
              </div>
              <div className="space-y-2">
                <Label>Waktu Selesai</Label>
                <Input type="datetime-local" value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} data-testid="session-end-input" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Durasi (menit)</Label>
                <Input type="number" min="1" value={form.duration_minutes} onChange={(e) => setForm({ ...form, duration_minutes: e.target.value })} data-testid="session-duration-input" />
              </div>
              <div className="space-y-2">
                <Label>KKM</Label>
                <Input type="number" min="0" max="100" value={form.kkm} onChange={(e) => setForm({ ...form, kkm: e.target.value })} />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Kelas Peserta {form.class_ids.length === 0 && <span className="text-muted-foreground font-normal">(kosong = semua siswa)</span>}</Label>
              {classes.length === 0 ? (
                <p className="text-xs text-muted-foreground">Belum ada kelas. Tambahkan di menu Kelas.</p>
              ) : (
                <div className="border border-border rounded-md max-h-36 overflow-y-auto divide-y divide-border">
                  {classes.map((c) => (
                    <label key={c.id} className="flex items-center gap-3 p-2.5 hover:bg-muted/40 cursor-pointer" data-testid={`pick-class-${c.id}`}>
                      <Checkbox checked={form.class_ids.includes(c.id)} onCheckedChange={() => toggleClass(c.id)} />
                      <span className="text-sm">{c.name} <span className="text-muted-foreground">({c.student_count} siswa)</span></span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Batal</Button>
            <Button onClick={save} data-testid="save-session-btn">Simpan</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
