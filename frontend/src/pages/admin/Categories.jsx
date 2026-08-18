import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, FolderTree } from "lucide-react";
import api, { apiError } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../../components/ui/dialog";

export default function Categories() {
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: "", description: "" });

  const load = () => api.get("/categories").then((r) => setItems(r.data));
  useEffect(() => { load(); }, []);

  const openNew = () => { setEditing(null); setForm({ name: "", description: "" }); setOpen(true); };
  const openEdit = (c) => { setEditing(c); setForm({ name: c.name, description: c.description || "" }); setOpen(true); };

  const save = async () => {
    try {
      if (editing) await api.put(`/categories/${editing.id}`, form);
      else await api.post("/categories", form);
      toast.success("Kategori disimpan");
      setOpen(false); load();
    } catch (e) { toast.error(apiError(e)); }
  };

  const remove = async (c) => {
    if (!window.confirm(`Hapus kategori "${c.name}"?`)) return;
    await api.delete(`/categories/${c.id}`);
    toast.success("Kategori dihapus"); load();
  };

  return (
    <div data-testid="categories-page">
      <div className="flex items-end justify-between mb-8 gap-4 flex-wrap">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">Materi</p>
          <h1 className="font-heading text-3xl sm:text-4xl font-semibold tracking-tight mt-1">Kategori Materi</h1>
        </div>
        <Button onClick={openNew} data-testid="add-category-btn"><Plus className="h-4 w-4 mr-2" />Tambah Kategori</Button>
      </div>

      {items.length === 0 ? (
        <div className="border border-dashed border-border rounded-md p-16 text-center text-muted-foreground">
          <FolderTree className="h-10 w-10 mx-auto mb-3 opacity-40" />
          Belum ada kategori materi.
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((c) => (
            <div key={c.id} className="bg-card border border-border rounded-md p-6 hover:shadow-sm transition-shadow" data-testid={`category-${c.id}`}>
              <div className="flex items-start justify-between">
                <h3 className="font-heading text-lg font-medium">{c.name}</h3>
                <div className="flex gap-1">
                  <button onClick={() => openEdit(c)} className="text-muted-foreground hover:text-primary p-1"><Pencil className="h-4 w-4" /></button>
                  <button onClick={() => remove(c)} className="text-muted-foreground hover:text-destructive p-1"><Trash2 className="h-4 w-4" /></button>
                </div>
              </div>
              <p className="text-sm text-muted-foreground mt-2 leading-relaxed">{c.description || "Tanpa deskripsi"}</p>
            </div>
          ))}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editing ? "Edit Kategori" : "Tambah Kategori"}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Nama Kategori</Label>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Matematika" data-testid="category-name-input" />
            </div>
            <div className="space-y-2">
              <Label>Deskripsi</Label>
              <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Deskripsi singkat" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Batal</Button>
            <Button onClick={save} data-testid="save-category-btn">Simpan</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
