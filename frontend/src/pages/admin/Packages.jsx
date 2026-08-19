import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, Package as PackageIcon, Copy } from "lucide-react";
import api, { apiError } from "../../lib/api";
import { QTYPE_LABEL, releaseBodyPointerEvents } from "../../lib/utils2";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { Badge } from "../../components/ui/badge";
import { Checkbox } from "../../components/ui/checkbox";
import { Switch } from "../../components/ui/switch";
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "../../components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../../components/ui/dialog";

const EMPTY = { title: "", description: "", category_id: "", question_ids: [], scoring_method: "percentage", shuffle_questions: false, shuffle_options: false, min_score: 0, rounding: "2desimal", easy_min: null, medium_min: null, is_public: false };

export default function Packages() {
  const [items, setItems] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [cats, setCats] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);

  const load = () => api.get("/packages").then((r) => setItems(r.data));
  useEffect(() => {
    load();
    api.get("/questions").then((r) => setQuestions(r.data));
    api.get("/categories").then((r) => setCats(r.data));
  }, []);

  const openNew = () => { setEditing(null); setForm(EMPTY); setOpen(true); };
  const openEdit = (p) => {
    setEditing(p);
    setForm({ title: p.title, description: p.description || "", category_id: p.category_id || "",
      question_ids: p.question_ids || [], scoring_method: p.scoring_method || "percentage",
      shuffle_questions: !!p.shuffle_questions, shuffle_options: !!p.shuffle_options,
      min_score: p.min_score ?? 0, rounding: p.rounding || "2desimal",
      easy_min: p.easy_min ?? null, medium_min: p.medium_min ?? null, is_public: !!p.is_public });
    setOpen(true);
  };

  const toggleQ = (id) => setForm((f) => ({
    ...f, question_ids: f.question_ids.includes(id) ? f.question_ids.filter((x) => x !== id) : [...f.question_ids, id],
  }));

  const save = async () => {
    if (!form.title.trim()) return toast.error("Judul paket wajib diisi");
    if (form.question_ids.length === 0) return toast.error("Pilih minimal 1 soal");
    const payload = { ...form, category_id: form.category_id || null, min_score: Number(form.min_score) || 0,
      easy_min: form.easy_min === null || form.easy_min === "" ? null : Number(form.easy_min),
      medium_min: form.medium_min === null || form.medium_min === "" ? null : Number(form.medium_min) };
    try {
      if (editing) await api.put(`/packages/${editing.id}`, payload);
      else await api.post("/packages", payload);
      toast.success("Paket disimpan"); setOpen(false); releaseBodyPointerEvents(); load();
    } catch (e) { toast.error(apiError(e)); }
  };

  const remove = async (p) => {
    if (!window.confirm(`Hapus paket "${p.title}"?`)) return;
    await api.delete(`/packages/${p.id}`); toast.success("Paket dihapus"); load();
  };

  const duplicate = async (p) => {
    try {
      await api.post(`/packages/${p.id}/duplicate`);
      toast.success("Paket disalin ke milik Anda");
      load();
    } catch (e) { toast.error(apiError(e)); }
  };

  const filteredQ = form.category_id ? questions.filter((q) => q.category_id === form.category_id) : questions;

  return (
    <div data-testid="packages-page">
      <div className="flex items-end justify-between mb-8 gap-4 flex-wrap">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">Paket</p>
          <h1 className="font-heading text-3xl sm:text-4xl font-semibold tracking-tight mt-1">Paket Soal</h1>
        </div>
        <Button onClick={openNew} data-testid="add-package-btn"><Plus className="h-4 w-4 mr-2" />Tambah Paket</Button>
      </div>

      {items.length === 0 ? (
        <div className="border border-dashed border-border rounded-md p-16 text-center text-muted-foreground">
          <PackageIcon className="h-10 w-10 mx-auto mb-3 opacity-40" />Belum ada paket soal.
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((p) => (
            <div key={p.id} className="bg-card border border-border rounded-md p-6 hover:shadow-sm transition-shadow" data-testid={`package-${p.id}`}>
              <div className="flex items-start justify-between">
                <h3 className="font-heading text-lg font-medium pr-2">{p.title}</h3>
                <div className="flex gap-1 shrink-0 items-center">
                  <button onClick={() => duplicate(p)} data-testid={`duplicate-package-${p.id}`} title="Duplikat paket" className="text-muted-foreground hover:text-primary p-1"><Copy className="h-4 w-4" /></button>
                  {p.is_owner ? (
                    <>
                      <button onClick={() => openEdit(p)} className="text-muted-foreground hover:text-primary p-1"><Pencil className="h-4 w-4" /></button>
                      <button onClick={() => remove(p)} className="text-muted-foreground hover:text-destructive p-1"><Trash2 className="h-4 w-4" /></button>
                    </>
                  ) : (
                    <Badge variant="outline" className="text-xs">oleh {p.owner_name}</Badge>
                  )}
                </div>
              </div>
              <p className="text-sm text-muted-foreground mt-1 mb-4 line-clamp-2">{p.description || "Tanpa deskripsi"}</p>
              <div className="flex gap-2 flex-wrap">
                <Badge className="bg-primary/10 text-primary border-0">{p.question_count} Soal</Badge>
                <Badge variant="outline">{p.scoring_method === "weighted" ? "Berbobot" : "Persentase"}</Badge>
                {p.shuffle_questions && <Badge variant="outline">Soal Acak</Badge>}
                {p.shuffle_options && <Badge variant="outline">Opsi Acak</Badge>}
                {p.is_public && <Badge className="bg-accent/15 text-accent border-0" data-testid={`public-badge-${p.id}`}>Publik</Badge>}
              </div>
            </div>
          ))}
        </div>
      )}

      <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) releaseBodyPointerEvents(); }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{editing ? "Edit Paket" : "Tambah Paket Soal"}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Judul Paket</Label>
              <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} data-testid="package-title-input" />
            </div>
            <div className="space-y-2">
              <Label>Deskripsi</Label>
              <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={2} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Filter Kategori</Label>
                <Select value={form.category_id || "none"} onValueChange={(v) => setForm({ ...form, category_id: v === "none" ? "" : v })}>
                  <SelectTrigger><SelectValue placeholder="Semua" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Semua Kategori</SelectItem>
                    {cats.map((c) => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Metode Penilaian</Label>
                <Select value={form.scoring_method} onValueChange={(v) => setForm({ ...form, scoring_method: v })}>
                  <SelectTrigger data-testid="scoring-method-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="percentage">Persentase (benar/total × 100)</SelectItem>
                    <SelectItem value="weighted">Berbobot per soal</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 rounded-md border border-border p-4">
              <div className="flex items-center justify-between gap-3 col-span-2 sm:col-span-1">
                <div>
                  <Label>Acak Urutan Soal</Label>
                  <p className="text-xs text-muted-foreground">Beda urutan tiap siswa</p>
                </div>
                <Switch checked={form.shuffle_questions} onCheckedChange={(v) => setForm({ ...form, shuffle_questions: v })} data-testid="shuffle-questions-switch" />
              </div>
              <div className="flex items-center justify-between gap-3 col-span-2 sm:col-span-1">
                <div>
                  <Label>Acak Opsi Jawaban</Label>
                  <p className="text-xs text-muted-foreground">Untuk soal pilihan ganda</p>
                </div>
                <Switch checked={form.shuffle_options} onCheckedChange={(v) => setForm({ ...form, shuffle_options: v })} data-testid="shuffle-options-switch" />
              </div>
              <div className="flex items-center justify-between gap-3 col-span-2">
                <div>
                  <Label>Bagikan ke Guru Lain (Publik)</Label>
                  <p className="text-xs text-muted-foreground">Guru lain bisa memakai paket ini untuk sesi mereka</p>
                </div>
                <Switch checked={form.is_public} onCheckedChange={(v) => setForm({ ...form, is_public: v })} data-testid="public-switch" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Nilai Minimal</Label>
                <Input type="number" min="0" max="100" value={form.min_score} onChange={(e) => setForm({ ...form, min_score: e.target.value })} data-testid="min-score-input" />
                <p className="text-xs text-muted-foreground">Nilai terendah yang diberikan.</p>
              </div>
              <div className="space-y-2">
                <Label>Pembulatan Nilai</Label>
                <Select value={form.rounding} onValueChange={(v) => setForm({ ...form, rounding: v })}>
                  <SelectTrigger data-testid="rounding-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="2desimal">2 desimal (85.75)</SelectItem>
                    <SelectItem value="1desimal">1 desimal (85.8)</SelectItem>
                    <SelectItem value="bulat">Bilangan bulat (86)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="rounded-md border border-border p-4 space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <Label>Ambang Kesukaran Khusus</Label>
                  <p className="text-xs text-muted-foreground">Timpa setelan global untuk paket ini</p>
                </div>
                <Switch
                  checked={form.easy_min !== null}
                  onCheckedChange={(v) => setForm({ ...form, easy_min: v ? 70 : null, medium_min: v ? 40 : null })}
                  data-testid="custom-threshold-switch"
                />
              </div>
              {form.easy_min !== null && (
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="text-xs">Mudah (≥ %)</Label>
                    <Input type="number" min="1" max="100" value={form.easy_min} onChange={(e) => setForm({ ...form, easy_min: e.target.value })} data-testid="pkg-easy-min-input" />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs">Sedang (≥ %)</Label>
                    <Input type="number" min="0" max="99" value={form.medium_min} onChange={(e) => setForm({ ...form, medium_min: e.target.value })} data-testid="pkg-medium-min-input" />
                  </div>
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label>Pilih Soal ({form.question_ids.length} dipilih)</Label>
              <div className="border border-border rounded-md max-h-64 overflow-y-auto divide-y divide-border">
                {filteredQ.length === 0 && <p className="p-4 text-sm text-muted-foreground">Tidak ada soal.</p>}
                {filteredQ.map((q) => (
                  <label key={q.id} className="flex items-start gap-3 p-3 hover:bg-muted/40 cursor-pointer" data-testid={`pick-question-${q.id}`}>
                    <Checkbox checked={form.question_ids.includes(q.id)} onCheckedChange={() => toggleQ(q.id)} className="mt-0.5" />
                    <div className="min-w-0">
                      <div className="flex gap-2 mb-1">
                        <Badge variant="outline" className="text-xs">{QTYPE_LABEL[q.type]}</Badge>
                        <Badge variant="outline" className="text-xs">Bobot {q.weight}</Badge>
                      </div>
                      <p className="text-sm line-clamp-2">{q.text}</p>
                    </div>
                  </label>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setOpen(false); releaseBodyPointerEvents(); }}>Batal</Button>
            <Button onClick={save} data-testid="save-package-btn">Simpan</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
