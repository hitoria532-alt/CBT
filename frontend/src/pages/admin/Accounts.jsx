import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, FileText } from "lucide-react";
import api, { apiError } from "../../lib/api";
import { ROLE_LABEL } from "../../lib/utils2";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Badge } from "../../components/ui/badge";
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "../../components/ui/select";
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "../../components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../../components/ui/dialog";

const EMPTY = { email: "", password: "", name: "", role: "siswa", identifier: "" };

export default function Accounts() {
  const [users, setUsers] = useState([]);
  const [filter, setFilter] = useState("all");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);

  const load = () => api.get("/users").then((r) => setUsers(r.data));
  useEffect(() => { load(); }, []);

  const openNew = () => { setEditing(null); setForm(EMPTY); setOpen(true); };
  const openEdit = (u) => {
    setEditing(u);
    setForm({ email: u.email, password: "", name: u.name, role: u.role, identifier: u.identifier || "" });
    setOpen(true);
  };

  const save = async () => {
    try {
      if (editing) {
        await api.put(`/users/${editing.id}`, {
          name: form.name, role: form.role, identifier: form.identifier,
          ...(form.password ? { password: form.password } : {}),
        });
      } else {
        await api.post("/users", form);
      }
      toast.success("Akun disimpan"); setOpen(false); load();
    } catch (e) { toast.error(apiError(e)); }
  };

  const remove = async (u) => {
    if (!window.confirm(`Hapus akun ${u.name}?`)) return;
    await api.delete(`/users/${u.id}`); toast.success("Akun dihapus"); load();
  };

  const downloadReport = async (u) => {
    try {
      const res = await api.get(`/report/student/${u.id}/pdf`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a"); a.href = url; a.download = `rapor-${u.name}.pdf`; a.click();
      toast.success("Rapor diunduh");
    } catch (e) { toast.error(apiError(e)); }
  };

  const shown = filter === "all" ? users : users.filter((u) => u.role === filter);

  const roleColor = { admin: "bg-accent/15 text-accent", guru: "bg-primary/10 text-primary", siswa: "bg-secondary/20 text-secondary-foreground" };

  return (
    <div data-testid="accounts-page">
      <div className="flex items-end justify-between mb-8 gap-4 flex-wrap">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">Pengguna</p>
          <h1 className="font-heading text-3xl sm:text-4xl font-semibold tracking-tight mt-1">Manajemen Akun</h1>
        </div>
        <div className="flex gap-3">
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-40" data-testid="filter-role"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Semua Role</SelectItem>
              <SelectItem value="admin">Admin</SelectItem>
              <SelectItem value="guru">Guru</SelectItem>
              <SelectItem value="siswa">Siswa</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={openNew} data-testid="add-user-btn"><Plus className="h-4 w-4 mr-2" />Tambah Akun</Button>
        </div>
      </div>

      <div className="bg-card border border-border rounded-md overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nama</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>NISN / NIP</TableHead>
              <TableHead>Role</TableHead>
              <TableHead className="text-right">Aksi</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {shown.map((u) => (
              <TableRow key={u.id} data-testid={`user-row-${u.id}`}>
                <TableCell className="font-medium">{u.name}</TableCell>
                <TableCell className="text-muted-foreground">{u.email}</TableCell>
                <TableCell className="text-muted-foreground">{u.identifier || "-"}</TableCell>
                <TableCell><Badge className={`${roleColor[u.role]} border-0`}>{ROLE_LABEL[u.role]}</Badge></TableCell>
                <TableCell className="text-right">
                  {u.role === "siswa" && (
                    <button onClick={() => downloadReport(u)} data-testid={`report-btn-${u.id}`} className="text-muted-foreground hover:text-primary p-1 mr-1" title="Unduh Rapor"><FileText className="h-4 w-4" /></button>
                  )}
                  <button onClick={() => openEdit(u)} className="text-muted-foreground hover:text-primary p-1 mr-1"><Pencil className="h-4 w-4" /></button>
                  <button onClick={() => remove(u)} className="text-muted-foreground hover:text-destructive p-1"><Trash2 className="h-4 w-4" /></button>
                </TableCell>
              </TableRow>
            ))}
            {shown.length === 0 && (
              <TableRow><TableCell colSpan={5} className="text-center text-muted-foreground py-10">Belum ada akun.</TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editing ? "Edit Akun" : "Tambah Akun"}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Nama Lengkap</Label>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="user-name-input" />
            </div>
            <div className="space-y-2">
              <Label>Email</Label>
              <Input type="email" value={form.email} disabled={!!editing} onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="user-email-input" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Role</Label>
                <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                  <SelectTrigger data-testid="user-role-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="siswa">Siswa</SelectItem>
                    <SelectItem value="guru">Guru</SelectItem>
                    <SelectItem value="admin">Admin</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>NISN / NIP</Label>
                <Input value={form.identifier} onChange={(e) => setForm({ ...form, identifier: e.target.value })} placeholder="Opsional" />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Password {editing && <span className="text-muted-foreground font-normal">(kosongkan jika tidak diubah)</span>}</Label>
              <Input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} data-testid="user-password-input" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Batal</Button>
            <Button onClick={save} data-testid="save-user-btn">Simpan</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
