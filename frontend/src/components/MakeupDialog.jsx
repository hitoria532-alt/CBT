import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import {
  CalendarPlus, Clock, Trash2, Pencil, UserX, CheckCircle2, Loader2, X,
} from "lucide-react";
import api, { apiError } from "../lib/api";
import { fmtDateTime, toLocalInput, fromLocalInput, MAKEUP_STATUS_LABEL } from "../lib/utils2";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import { Label } from "./ui/label";
import { Badge } from "./ui/badge";
import { Checkbox } from "./ui/checkbox";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "./ui/dialog";

const makeupStatusColor = {
  akan_datang: "bg-secondary/20 text-secondary-foreground",
  berlangsung: "bg-primary/10 text-primary",
  selesai: "bg-destructive/10 text-destructive",
  sudah_dikerjakan: "bg-primary text-primary-foreground",
};

function plusHours(h) {
  return toLocalInput(new Date(Date.now() + h * 3600000).toISOString());
}

/**
 * Dialog pengelolaan Ujian Susulan untuk satu sesi.
 * Guru memilih siswa yang belum mengerjakan, lalu memberi jendela waktu khusus
 * tanpa mengubah jadwal sesi asli sehingga kelas lain tidak terganggu.
 */
export default function MakeupDialog({ session, open, onOpenChange, onChanged }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [absentees, setAbsentees] = useState([]);
  const [makeups, setMakeups] = useState([]);
  const [picked, setPicked] = useState([]);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({
    start_time: "", end_time: "", duration_minutes: "", reason: "",
  });

  const resetForm = useCallback(() => {
    setEditing(null);
    setPicked([]);
    setForm({
      start_time: plusHours(0), end_time: plusHours(2),
      duration_minutes: "", reason: "",
    });
  }, []);

  const load = useCallback(async () => {
    if (!session) return;
    setLoading(true);
    try {
      const [a, m] = await Promise.all([
        api.get(`/makeups/absentees/${session.id}`),
        api.get("/makeups", { params: { session_id: session.id } }),
      ]);
      setAbsentees(a.data.absentees || []);
      setMakeups(m.data || []);
    } catch (e) {
      toast.error(apiError(e));
    } finally {
      setLoading(false);
    }
  }, [session]);

  useEffect(() => {
    if (open) { resetForm(); load(); }
  }, [open, load, resetForm]);

  const unscheduled = useMemo(() => absentees.filter((a) => !a.makeup), [absentees]);

  const toggle = (id) =>
    setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));

  const allPicked = unscheduled.length > 0 && picked.length === unscheduled.length;
  const toggleAll = () => setPicked(allPicked ? [] : unscheduled.map((a) => a.id));

  const startEdit = (mk) => {
    setEditing(mk);
    setPicked([]);
    setForm({
      start_time: toLocalInput(mk.start_time),
      end_time: toLocalInput(mk.end_time),
      duration_minutes: mk.duration_minutes ?? "",
      reason: mk.reason || "",
    });
  };

  const submit = async () => {
    if (!form.start_time || !form.end_time) return toast.error("Lengkapi waktu mulai dan selesai");
    if (!editing && picked.length === 0) return toast.error("Pilih minimal satu siswa");
    const payload = {
      start_time: fromLocalInput(form.start_time),
      end_time: fromLocalInput(form.end_time),
      duration_minutes: form.duration_minutes === "" ? null : Number(form.duration_minutes),
      reason: form.reason,
    };
    setSaving(true);
    try {
      if (editing) {
        await api.put(`/makeups/${editing.id}`, payload);
        toast.success(`Jadwal susulan ${editing.student_name} diperbarui`);
      } else {
        const r = await api.post("/makeups", {
          ...payload, session_id: session.id, student_ids: picked,
        });
        const { created = 0, updated = 0, skipped = [] } = r.data;
        toast.success(`Susulan dijadwalkan — ${created} baru, ${updated} diperbarui`);
        if (skipped.length) toast.warning(`${skipped.length} siswa dilewati`);
      }
      resetForm();
      await load();
      onChanged?.();
    } catch (e) {
      toast.error(apiError(e));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (mk) => {
    if (!window.confirm(`Batalkan jadwal susulan untuk ${mk.student_name}?`)) return;
    try {
      await api.delete(`/makeups/${mk.id}`);
      toast.success("Jadwal susulan dibatalkan");
      if (editing?.id === mk.id) resetForm();
      await load();
      onChanged?.();
    } catch (e) {
      toast.error(apiError(e));
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="sm:max-w-3xl max-h-[90vh] overflow-y-auto bg-card"
        data-testid="makeup-dialog"
      >
        <DialogHeader>
          <DialogTitle className="font-heading">Ujian Susulan</DialogTitle>
          <DialogDescription>
            {session?.title} — beri jendela waktu khusus untuk siswa yang belum mengerjakan.
            Jadwal sesi asli tidak berubah, jadi kelas lain tidak terganggu.
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="py-16 flex items-center justify-center text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin mr-2" />Memuat data…
          </div>
        ) : (
          <div className="space-y-8 py-1">
            {/* ---------------------------------------- Jadwal terpasang */}
            <section>
              <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground mb-3">
                Susulan Terjadwal ({makeups.length})
              </h3>
              {makeups.length === 0 ? (
                <p className="text-sm text-muted-foreground border border-dashed border-border rounded-md p-6 text-center">
                  Belum ada jadwal susulan pada sesi ini.
                </p>
              ) : (
                <div className="border border-border rounded-md divide-y divide-border overflow-hidden">
                  {makeups.map((mk) => (
                    <div
                      key={mk.id}
                      className={`p-4 flex items-start justify-between gap-3 flex-wrap ${editing?.id === mk.id ? "bg-muted/60" : "bg-card"}`}
                      data-testid={`makeup-item-${mk.id}`}
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap mb-1">
                          <span className="font-medium text-sm">{mk.student_name}</span>
                          {mk.student_identifier && (
                            <span className="text-xs text-muted-foreground">{mk.student_identifier}</span>
                          )}
                          <Badge className={`${makeupStatusColor[mk.status]} border-0 text-xs`}>
                            {mk.status === "sudah_dikerjakan" && <CheckCircle2 className="h-3 w-3 mr-1" />}
                            {MAKEUP_STATUS_LABEL[mk.status] || mk.status}
                          </Badge>
                          {mk.score != null && (
                            <Badge variant="outline" className="text-xs">Nilai {mk.score}</Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {fmtDateTime(mk.start_time)} — {fmtDateTime(mk.end_time)}
                          {" · "}durasi {mk.effective_duration} menit
                          {mk.duration_minutes == null && " (ikut sesi)"}
                        </p>
                        {mk.reason && (
                          <p className="text-xs text-muted-foreground mt-1 italic">Alasan: {mk.reason}</p>
                        )}
                      </div>
                      <div className="flex gap-1 shrink-0">
                        <button
                          onClick={() => startEdit(mk)}
                          className="text-muted-foreground hover:text-primary p-1"
                          title="Ubah jadwal"
                          data-testid={`edit-makeup-${mk.id}`}
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => remove(mk)}
                          className="text-muted-foreground hover:text-destructive p-1"
                          title="Batalkan susulan"
                          data-testid={`delete-makeup-${mk.id}`}
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* ---------------------------------------- Pilih siswa */}
            {!editing && (
              <section>
                <div className="flex items-end justify-between gap-3 mb-3 flex-wrap">
                  <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">
                    Siswa Belum Mengerjakan ({unscheduled.length})
                  </h3>
                  {unscheduled.length > 0 && (
                    <button
                      onClick={toggleAll}
                      className="text-xs font-medium text-primary hover:underline"
                      data-testid="makeup-toggle-all"
                    >
                      {allPicked ? "Kosongkan pilihan" : "Pilih semua"}
                    </button>
                  )}
                </div>
                {unscheduled.length === 0 ? (
                  <div className="border border-dashed border-border rounded-md p-8 text-center text-sm text-muted-foreground">
                    <CheckCircle2 className="h-8 w-8 mx-auto mb-2 opacity-40" />
                    Semua peserta sudah mengerjakan atau sudah dijadwalkan susulan.
                  </div>
                ) : (
                  <div className="border border-border rounded-md max-h-56 overflow-y-auto divide-y divide-border">
                    {unscheduled.map((a) => (
                      <label
                        key={a.id}
                        className="flex items-start gap-3 p-3 hover:bg-muted/40 cursor-pointer bg-card"
                        data-testid={`pick-absentee-${a.id}`}
                      >
                        <Checkbox
                          checked={picked.includes(a.id)}
                          onCheckedChange={() => toggle(a.id)}
                          className="mt-0.5"
                        />
                        <span className="min-w-0">
                          <span className="block text-sm font-medium">
                            {a.name}
                            {a.identifier && (
                              <span className="text-muted-foreground font-normal ml-2 text-xs">{a.identifier}</span>
                            )}
                          </span>
                          <span className="block text-xs text-muted-foreground mt-0.5 flex items-center gap-1">
                            <UserX className="h-3 w-3" />{a.reason_hint}
                          </span>
                        </span>
                      </label>
                    ))}
                  </div>
                )}
              </section>
            )}

            {/* ---------------------------------------- Form jadwal */}
            {(editing || unscheduled.length > 0) && (
              <section className="border border-border rounded-md p-5 bg-muted/30">
                <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
                  <h3 className="text-sm font-medium font-heading">
                    {editing
                      ? `Ubah Jadwal — ${editing.student_name}`
                      : `Jadwal Susulan${picked.length ? ` (${picked.length} siswa dipilih)` : ""}`}
                  </h3>
                  {editing && (
                    <button
                      onClick={resetForm}
                      className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
                      data-testid="cancel-edit-makeup"
                    >
                      <X className="h-3 w-3" />Batal ubah
                    </button>
                  )}
                </div>
                <div className="space-y-4">
                  <div className="grid sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Mulai Susulan</Label>
                      <Input
                        type="datetime-local"
                        value={form.start_time}
                        onChange={(e) => setForm({ ...form, start_time: e.target.value })}
                        data-testid="makeup-start-input"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Selesai Susulan</Label>
                      <Input
                        type="datetime-local"
                        value={form.end_time}
                        onChange={(e) => setForm({ ...form, end_time: e.target.value })}
                        data-testid="makeup-end-input"
                      />
                    </div>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>
                        Durasi (menit){" "}
                        <span className="text-muted-foreground font-normal">
                          kosong = ikut sesi ({session?.duration_minutes})
                        </span>
                      </Label>
                      <Input
                        type="number"
                        min="1"
                        placeholder={String(session?.duration_minutes ?? "")}
                        value={form.duration_minutes}
                        onChange={(e) => setForm({ ...form, duration_minutes: e.target.value })}
                        data-testid="makeup-duration-input"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Alasan (opsional)</Label>
                      <Textarea
                        rows={1}
                        value={form.reason}
                        onChange={(e) => setForm({ ...form, reason: e.target.value })}
                        placeholder="Sakit, izin keluarga, kendala jaringan…"
                        data-testid="makeup-reason-input"
                      />
                    </div>
                  </div>
                  <div className="flex justify-end gap-2 pt-1">
                    <Button variant="outline" onClick={() => onOpenChange(false)}>Tutup</Button>
                    <Button onClick={submit} disabled={saving} data-testid="save-makeup-btn">
                      {saving ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : editing ? (
                        <Clock className="h-4 w-4 mr-2" />
                      ) : (
                        <CalendarPlus className="h-4 w-4 mr-2" />
                      )}
                      {editing ? "Simpan Perubahan" : "Jadwalkan Susulan"}
                    </Button>
                  </div>
                </div>
              </section>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
