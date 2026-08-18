import { useEffect, useState, useRef } from "react";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, FileQuestion, Upload, Download, Image as ImageIcon, X } from "lucide-react";
import api, { apiError, fileUrl } from "../../lib/api";
import { QTYPE_LABEL } from "../../lib/utils2";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { Badge } from "../../components/ui/badge";
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "../../components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../../components/ui/dialog";

const EMPTY = { category_id: "", type: "pg", text: "", options: ["", "", "", ""], correct_answer: "0", weight: 1, image_path: null };

export default function Questions() {
  const [items, setItems] = useState([]);
  const [cats, setCats] = useState([]);
  const [filter, setFilter] = useState("all");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [importOpen, setImportOpen] = useState(false);
  const [importing, setImporting] = useState(false);
  const fileRef = useRef();
  const imgRef = useRef();
  const [uploadingImg, setUploadingImg] = useState(false);

  const uploadImage = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const fd = new FormData();
    fd.append("file", f);
    setUploadingImg(true);
    try {
      const { data } = await api.post("/uploads/image", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setForm((prev) => ({ ...prev, image_path: data.path }));
      toast.success("Gambar terunggah");
    } catch (err) { toast.error(apiError(err)); }
    finally { setUploadingImg(false); if (imgRef.current) imgRef.current.value = ""; }
  };

  const reloadCats = () => api.get("/categories").then((r) => setCats(r.data));

  const downloadTemplate = async () => {
    const res = await api.get("/questions/import-template", { responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a"); a.href = url; a.download = "template_soal.csv"; a.click();
  };

  const doImport = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const fd = new FormData();
    fd.append("file", f);
    setImporting(true);
    try {
      const { data } = await api.post("/questions/import", fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success(`${data.imported} soal berhasil diimpor`);
      if (data.errors?.length) toast.warning(`${data.errors.length} baris dilewati`);
      setImportOpen(false); load(); reloadCats();
    } catch (err) { toast.error(apiError(err)); }
    finally { setImporting(false); if (fileRef.current) fileRef.current.value = ""; }
  };

  const load = () => api.get("/questions").then((r) => setItems(r.data));
  useEffect(() => { load(); api.get("/categories").then((r) => setCats(r.data)); }, []);

  const openNew = () => { setEditing(null); setForm(EMPTY); setOpen(true); };
  const openEdit = (q) => {
    setEditing(q);
    setForm({
      category_id: q.category_id || "", type: q.type, text: q.text,
      options: q.options?.length ? q.options : ["", "", "", ""],
      correct_answer: q.correct_answer ?? (q.type === "truefalse" ? "true" : "0"),
      weight: q.weight ?? 1,
      image_path: q.image_path || null,
    });
    setOpen(true);
  };

  const setType = (type) => {
    setForm((f) => ({
      ...f, type,
      options: type === "pg" ? (f.options.length ? f.options : ["", "", "", ""]) : [],
      correct_answer: type === "pg" ? "0" : type === "truefalse" ? "true" : null,
    }));
  };

  const save = async () => {
    const payload = {
      category_id: form.category_id || null, type: form.type, text: form.text,
      options: form.type === "pg" ? form.options.filter((o) => o.trim() !== "" || true) : [],
      correct_answer: form.type === "essay" ? null : String(form.correct_answer),
      weight: Number(form.weight) || 1,
      image_path: form.image_path || null,
    };
    if (!payload.text.trim()) return toast.error("Teks soal wajib diisi");
    try {
      if (editing) await api.put(`/questions/${editing.id}`, payload);
      else await api.post("/questions", payload);
      toast.success("Soal disimpan"); setOpen(false); load();
    } catch (e) { toast.error(apiError(e)); }
  };

  const remove = async (q) => {
    if (!window.confirm("Hapus soal ini?")) return;
    await api.delete(`/questions/${q.id}`); toast.success("Soal dihapus"); load();
  };

  const catName = (id) => cats.find((c) => c.id === id)?.name || "Umum";
  const shown = filter === "all" ? items : items.filter((q) => q.category_id === filter);
  const setOpt = (i, v) => setForm((f) => { const o = [...f.options]; o[i] = v; return { ...f, options: o }; });

  return (
    <div data-testid="questions-page">
      <div className="flex items-end justify-between mb-8 gap-4 flex-wrap">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">Bank Soal</p>
          <h1 className="font-heading text-3xl sm:text-4xl font-semibold tracking-tight mt-1">Kelola Soal</h1>
        </div>
        <div className="flex gap-3">
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-48"><SelectValue placeholder="Filter kategori" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Semua Kategori</SelectItem>
              {cats.map((c) => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={() => setImportOpen(true)} data-testid="import-question-btn"><Upload className="h-4 w-4 mr-2" />Impor</Button>
          <Button onClick={openNew} data-testid="add-question-btn"><Plus className="h-4 w-4 mr-2" />Tambah Soal</Button>
        </div>
      </div>

      {shown.length === 0 ? (
        <div className="border border-dashed border-border rounded-md p-16 text-center text-muted-foreground">
          <FileQuestion className="h-10 w-10 mx-auto mb-3 opacity-40" />Belum ada soal.
        </div>
      ) : (
        <div className="space-y-3">
          {shown.map((q, i) => (
            <div key={q.id} className="bg-card border border-border rounded-md p-5 flex items-start gap-4" data-testid={`question-${q.id}`}>
              <span className="font-heading font-semibold text-muted-foreground w-6 shrink-0">{i + 1}.</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  <Badge variant="outline" className="text-xs">{QTYPE_LABEL[q.type]}</Badge>
                  <Badge variant="outline" className="text-xs">{catName(q.category_id)}</Badge>
                  <Badge className="text-xs bg-primary/10 text-primary border-0">Bobot {q.weight}</Badge>
                </div>
                <p className="text-sm leading-relaxed">{q.text}</p>
                {q.image_path && <img src={fileUrl(q.image_path)} alt="" className="mt-2 max-h-32 rounded border border-border" />}
                {q.type === "pg" && (
                  <ul className="mt-2 text-sm text-muted-foreground space-y-1">
                    {q.options.map((o, oi) => (
                      <li key={oi} className={String(oi) === String(q.correct_answer) ? "text-primary font-medium" : ""}>
                        {String.fromCharCode(65 + oi)}. {o} {String(oi) === String(q.correct_answer) && "✓"}
                      </li>
                    ))}
                  </ul>
                )}
                {q.type === "truefalse" && (
                  <p className="mt-2 text-sm text-primary font-medium">Jawaban: {q.correct_answer === "true" ? "Benar" : "Salah"}</p>
                )}
              </div>
              <div className="flex gap-1 shrink-0">
                <button onClick={() => openEdit(q)} className="text-muted-foreground hover:text-primary p-1"><Pencil className="h-4 w-4" /></button>
                <button onClick={() => remove(q)} className="text-muted-foreground hover:text-destructive p-1"><Trash2 className="h-4 w-4" /></button>
              </div>
            </div>
          ))}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{editing ? "Edit Soal" : "Tambah Soal"}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Tipe Soal</Label>
                <Select value={form.type} onValueChange={setType}>
                  <SelectTrigger data-testid="question-type-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pg">Pilihan Ganda</SelectItem>
                    <SelectItem value="truefalse">Benar / Salah</SelectItem>
                    <SelectItem value="essay">Esai</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Kategori</Label>
                <Select value={form.category_id || "none"} onValueChange={(v) => setForm({ ...form, category_id: v === "none" ? "" : v })}>
                  <SelectTrigger><SelectValue placeholder="Umum" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Umum</SelectItem>
                    {cats.map((c) => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label>Teks Soal</Label>
              <Textarea value={form.text} onChange={(e) => setForm({ ...form, text: e.target.value })} rows={3} data-testid="question-text-input" />
            </div>

            <div className="space-y-2">
              <Label>Gambar Soal (opsional)</Label>
              {form.image_path ? (
                <div className="relative inline-block">
                  <img src={fileUrl(form.image_path)} alt="soal" className="max-h-40 rounded-md border border-border" />
                  <button type="button" onClick={() => setForm({ ...form, image_path: null })} data-testid="remove-image-btn"
                    className="absolute -top-2 -right-2 bg-destructive text-destructive-foreground rounded-full p-1 shadow"><X className="h-3 w-3" /></button>
                </div>
              ) : (
                <div>
                  <input ref={imgRef} type="file" accept="image/*" onChange={uploadImage} className="hidden" data-testid="question-image-input" />
                  <Button type="button" variant="outline" onClick={() => imgRef.current?.click()} disabled={uploadingImg} data-testid="upload-image-btn">
                    <ImageIcon className="h-4 w-4 mr-2" />{uploadingImg ? "Mengunggah..." : "Unggah Gambar"}
                  </Button>
                </div>
              )}
            </div>

            {form.type === "pg" && (
              <div className="space-y-2">
                <Label>Opsi Jawaban (pilih yang benar)</Label>
                {form.options.map((o, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <input type="radio" name="correct" checked={String(form.correct_answer) === String(i)}
                      onChange={() => setForm({ ...form, correct_answer: String(i) })}
                      className="accent-[hsl(var(--primary))] h-4 w-4" data-testid={`correct-opt-${i}`} />
                    <span className="font-medium w-5">{String.fromCharCode(65 + i)}</span>
                    <Input value={o} onChange={(e) => setOpt(i, e.target.value)} placeholder={`Opsi ${String.fromCharCode(65 + i)}`} data-testid={`option-input-${i}`} />
                  </div>
                ))}
              </div>
            )}

            {form.type === "truefalse" && (
              <div className="space-y-2">
                <Label>Kunci Jawaban</Label>
                <Select value={form.correct_answer} onValueChange={(v) => setForm({ ...form, correct_answer: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="true">Benar</SelectItem>
                    <SelectItem value="false">Salah</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            {form.type === "essay" && (
              <p className="text-sm text-muted-foreground bg-muted/50 rounded-md p-3">
                Soal esai dinilai manual oleh guru pada halaman Hasil & Koreksi.
              </p>
            )}

            <div className="space-y-2">
              <Label>Bobot Nilai</Label>
              <Input type="number" min="0.5" step="0.5" value={form.weight} onChange={(e) => setForm({ ...form, weight: e.target.value })} data-testid="question-weight-input" />
              <p className="text-xs text-muted-foreground">Digunakan bila paket memakai metode penilaian berbobot.</p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Batal</Button>
            <Button onClick={save} data-testid="save-question-btn">Simpan</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={importOpen} onOpenChange={setImportOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Impor Soal Massal</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <p className="text-sm text-muted-foreground leading-relaxed">
              Unggah file <b>CSV</b> atau <b>Excel (.xlsx)</b> dengan kolom:
              <code className="block bg-muted rounded px-2 py-1 mt-2 text-xs">type, text, option_a, option_b, option_c, option_d, correct, weight, category</code>
            </p>
            <ul className="text-xs text-muted-foreground list-disc pl-5 space-y-1">
              <li><b>type</b>: pg / truefalse / essay</li>
              <li><b>correct</b>: untuk PG isi A/B/C/D · untuk B/S isi benar/salah</li>
              <li><b>category</b>: nama kategori (dibuat otomatis bila belum ada)</li>
            </ul>
            <Button variant="outline" onClick={downloadTemplate} className="w-full" data-testid="download-template-btn">
              <Download className="h-4 w-4 mr-2" />Unduh Template CSV
            </Button>
            <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls" onChange={doImport} className="hidden" data-testid="import-file-input" />
            <Button onClick={() => fileRef.current?.click()} disabled={importing} className="w-full" data-testid="upload-file-btn">
              <Upload className="h-4 w-4 mr-2" />{importing ? "Mengimpor..." : "Pilih File & Impor"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
