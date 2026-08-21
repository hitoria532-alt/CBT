import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ClipboardCheck, ChevronRight, ArrowLeft, Download, BarChart3, SlidersHorizontal, FileSpreadsheet, ShieldAlert, CalendarPlus } from "lucide-react";import api, { apiError } from "../../lib/api";
import { fmtDateTime, STATUS_LABEL, QTYPE_LABEL } from "../../lib/utils2";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Badge } from "../../components/ui/badge";
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "../../components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../../components/ui/dialog";

export default function Results() {
  const [sessions, setSessions] = useState([]);
  const [active, setActive] = useState(null);
  const [data, setData] = useState(null);
  const [grading, setGrading] = useState(null); // attempt detail being graded
  const [scores, setScores] = useState({});
  const [analytics, setAnalytics] = useState(null);
  const [thresholdOpen, setThresholdOpen] = useState(false);
  const [thForm, setThForm] = useState({ easy_min: 70, medium_min: 40 });
  const [exporting, setExporting] = useState(false);

  useEffect(() => { api.get("/sessions").then((r) => setSessions(r.data)); }, []);

  const openSession = async (s) => {
    setActive(s);
    const r = await api.get(`/results/session/${s.id}`);
    setData(r.data);
  };

  const openGrade = async (attempt) => {
    const r = await api.get(`/results/detail/${attempt.id}`);
    setGrading(r.data);
    const init = {};
    r.data.details.filter((d) => d.type === "essay").forEach((d) => { init[d.question_id] = d.points_earned ?? 0; });
    setScores(init);
  };

  const submitGrade = async () => {
    try {
      await api.post(`/results/grade/${grading.id}`, { scores });
      toast.success("Nilai esai tersimpan");
      setGrading(null);
      openSession(active);
    } catch (e) { toast.error(apiError(e)); }
  };

  const exportCSV = () => {
    const rows = [["Nama", "NISN/NIP", "Status", "Nilai", "Jalur", "Waktu Kumpul"]];
    data.attempts.forEach((a) => rows.push([
      a.student_name, a.student_identifier || "-", STATUS_LABEL[a.status] || a.status,
      a.score ?? "-", a.is_makeup ? "Susulan" : "Reguler", fmtDateTime(a.submitted_at),
    ]));
    const csv = rows.map((r) => r.map((c) => `"${c}"`).join(",")).join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url; a.download = `hasil-${active.title}.csv`; a.click();
  };

  const exportExcel = async () => {
    setExporting(true);
    try {
      const res = await api.get(`/export/session/${active.id}/xlsx`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const el = document.createElement("a");
      el.href = url;
      el.download = `hasil-${active.title.replace(/\s+/g, "_")}.xlsx`;
      el.click();
      URL.revokeObjectURL(url);
      toast.success("Rekap nilai Excel terunduh");
    } catch (e) { toast.error(apiError(e)); }
    finally { setExporting(false); }
  };

  const downloadPdf = async (attemptId) => {
    const res = await api.get(`/results/detail/${attemptId}/pdf`, { responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const el = document.createElement("a"); el.href = url; el.download = "kartu-hasil.pdf"; el.click();
  };

  const openAnalytics = async () => {
    const r = await api.get(`/analytics/session/${active.id}`);
    setAnalytics(r.data);
  };

  const openThreshold = () => {
    setThForm(analytics?.thresholds || { easy_min: 70, medium_min: 40 });
    setThresholdOpen(true);
  };

  const saveThreshold = async () => {
    try {
      await api.put("/settings/difficulty", { easy_min: Number(thForm.easy_min), medium_min: Number(thForm.medium_min) });
      toast.success("Ambang kesukaran disimpan");
      setThresholdOpen(false);
      const r = await api.get(`/analytics/session/${active.id}`);
      setAnalytics(r.data);
    } catch (e) { toast.error(apiError(e)); }
  };

  // ---- Detail (grade) view
  if (grading) {
    return (
      <div data-testid="grade-page">
        <button onClick={() => setGrading(null)} className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-6">
          <ArrowLeft className="h-4 w-4" /> Kembali ke daftar hasil
        </button>
        <h1 className="font-heading text-2xl font-semibold mb-1">Koreksi: {grading.student_name}</h1>
        <p className="text-muted-foreground mb-6">{grading.session_title}</p>

        {grading.violations?.length > 0 && (
          <div className="mb-6 rounded-md border border-destructive/30 bg-destructive/5 p-4" data-testid="violation-log">
            <div className="flex items-center gap-2 text-sm font-medium text-destructive mb-2">
              <ShieldAlert className="h-4 w-4" />
              {grading.violations.length} pelanggaran mode ujian ketat
              {grading.auto_submitted_reason === "pelanggaran" && " · jawaban dikumpulkan otomatis"}
            </div>
            <ul className="text-xs text-muted-foreground space-y-1">
              {grading.violations.map((v, i) => (
                <li key={i}>
                  <b>{i + 1}.</b> {v.label || v.type} — {fmtDateTime(v.at)}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="space-y-4">
          {grading.details.map((d, i) => (
            <div key={i} className="bg-card border border-border rounded-md p-5">
              <div className="flex gap-2 mb-2">
                <Badge variant="outline" className="text-xs">{QTYPE_LABEL[d.type]}</Badge>
                <Badge variant="outline" className="text-xs">Bobot {d.points_possible}</Badge>
                {d.type !== "essay" && (
                  <Badge className={`text-xs border-0 ${d.is_correct ? "bg-primary/10 text-primary" : "bg-destructive/10 text-destructive"}`}>
                    {d.is_correct ? "Benar" : "Salah"}
                  </Badge>
                )}
              </div>
              <p className="text-sm font-medium mb-2">{i + 1}. {d.text}</p>
              {d.type === "pg" && (
                <p className="text-sm text-muted-foreground">Jawaban siswa: {d.answer != null ? `${String.fromCharCode(65 + Number(d.answer))}. ${d.options?.[Number(d.answer)] ?? ""}` : "(kosong)"}</p>
              )}
              {d.type === "truefalse" && (
                <p className="text-sm text-muted-foreground">Jawaban siswa: {d.answer === "true" ? "Benar" : d.answer === "false" ? "Salah" : "(kosong)"}</p>
              )}
              {d.type === "essay" && (
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground bg-muted/40 rounded-md p-3 whitespace-pre-wrap">{d.answer || "(kosong)"}</p>
                  <div className="flex items-center gap-2">
                    <Label className="text-xs">Nilai (maks {d.points_possible}):</Label>
                    <Input type="number" min="0" max={d.points_possible} step="0.5" value={scores[d.question_id] ?? 0}
                      onChange={(e) => setScores({ ...scores, [d.question_id]: e.target.value })}
                      className="w-28 h-9" data-testid={`essay-score-${d.question_id}`} />
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
        <div className="mt-6 flex justify-end">
          <Button onClick={submitGrade} data-testid="submit-grade-btn">Simpan Nilai</Button>
        </div>
      </div>
    );
  }

  // ---- Item analytics view
  if (analytics && active) {
    const diffColor = { Mudah: "bg-primary/10 text-primary", Sedang: "bg-secondary/20 text-secondary-foreground", Sulit: "bg-destructive/10 text-destructive" };
    return (
      <div data-testid="analytics-view">
        <button onClick={() => setAnalytics(null)} className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-6">
          <ArrowLeft className="h-4 w-4" /> Kembali ke hasil
        </button>
        <div className="flex items-end justify-between gap-4 flex-wrap mb-6">
          <div>
            <h1 className="font-heading text-2xl font-semibold">Analitik Butir Soal</h1>
            <p className="text-muted-foreground">{analytics.session_title} · {analytics.participants} peserta</p>
            {analytics.thresholds && (
              <p className="text-xs text-muted-foreground mt-1">Ambang ({analytics.thresholds.source === "paket" ? "khusus paket" : "global"}): Mudah ≥ {analytics.thresholds.easy_min}% · Sedang ≥ {analytics.thresholds.medium_min}% · Sulit &lt; {analytics.thresholds.medium_min}%</p>
            )}
          </div>
          <Button variant="outline" onClick={openThreshold} data-testid="edit-threshold-btn"><SlidersHorizontal className="h-4 w-4 mr-2" />Atur Ambang</Button>
        </div>
        {analytics.participants === 0 ? (
          <div className="border border-dashed border-border rounded-md p-12 text-center text-muted-foreground">Belum ada peserta yang mengumpulkan.</div>
        ) : (
          <div className="space-y-3">
            {analytics.items.map((it, i) => (
              <div key={it.question_id} className="bg-card border border-border rounded-md p-5" data-testid={`analytics-item-${i}`}>
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <p className="text-sm font-medium leading-relaxed mb-2"><span className="text-muted-foreground">{i + 1}.</span> {it.text}</p>
                    <p className="text-xs text-muted-foreground">
                      {it.correct != null ? `${it.correct}/${it.total} menjawab benar` : `Rerata nilai esai`} · {it.answered}/{it.total} menjawab
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="font-heading text-2xl font-bold">{it.percent_correct}%</p>
                    <Badge className={`${diffColor[it.difficulty]} border-0 text-xs`}>{it.difficulty}</Badge>
                  </div>
                </div>
                <div className="h-2 bg-muted rounded-full mt-3 overflow-hidden">
                  <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${it.percent_correct}%` }} />
                </div>
              </div>
            ))}
          </div>
        )}
        <Dialog open={thresholdOpen} onOpenChange={setThresholdOpen}>
          <DialogContent>
            <DialogHeader><DialogTitle>Atur Ambang Kesukaran</DialogTitle></DialogHeader>
            <div className="space-y-4 py-2">
              <p className="text-sm text-muted-foreground">Batas persen jawaban benar untuk menentukan label kesukaran soal. Berlaku untuk semua analitik.</p>
              <div className="space-y-2">
                <Label>Ambang "Mudah" (≥ %)</Label>
                <Input type="number" min="1" max="100" value={thForm.easy_min} onChange={(e) => setThForm({ ...thForm, easy_min: e.target.value })} data-testid="easy-min-input" />
              </div>
              <div className="space-y-2">
                <Label>Ambang "Sedang" (≥ %)</Label>
                <Input type="number" min="0" max="99" value={thForm.medium_min} onChange={(e) => setThForm({ ...thForm, medium_min: e.target.value })} data-testid="medium-min-input" />
                <p className="text-xs text-muted-foreground">Di bawah nilai ini akan dilabeli "Sulit". Harus lebih kecil dari ambang "Mudah".</p>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setThresholdOpen(false)}>Batal</Button>
              <Button onClick={saveThreshold} data-testid="save-threshold-btn">Simpan</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    );
  }

  // ---- Session results table
  if (active && data) {
    const scored = data.attempts.filter((a) => a.score != null);
    const avg = scored.length ? (scored.reduce((s, a) => s + a.score, 0) / scored.length).toFixed(1) : "-";
    return (
      <div data-testid="session-results">
        <button onClick={() => { setActive(null); setData(null); }} className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-6">
          <ArrowLeft className="h-4 w-4" /> Kembali ke daftar sesi
        </button>
        <div className="flex items-end justify-between mb-6 gap-4 flex-wrap">
          <div>
            <h1 className="font-heading text-2xl font-semibold">{active.title}</h1>
            <p className="text-muted-foreground">{data.attempts.length} peserta · rata-rata {avg}</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={openAnalytics} data-testid="analytics-btn"><BarChart3 className="h-4 w-4 mr-2" />Analitik Butir</Button>
            <Button variant="outline" onClick={exportCSV} disabled={!data.attempts.length} data-testid="export-csv-btn"><Download className="h-4 w-4 mr-2" />Export CSV</Button>
            <Button onClick={exportExcel} disabled={exporting || !data.attempts.length} data-testid="export-excel-btn">
              <FileSpreadsheet className="h-4 w-4 mr-2" />{exporting ? "Menyiapkan..." : "Ekspor Excel"}
            </Button>
          </div>
        </div>
        <div className="bg-card border border-border rounded-md overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nama Siswa</TableHead>
                <TableHead>NISN/NIP</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Nilai</TableHead>
                <TableHead>Pelanggaran</TableHead>
                <TableHead>Kumpul</TableHead>
                <TableHead className="text-right">Aksi</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.attempts.map((a) => (
                <TableRow key={a.id} data-testid={`result-row-${a.id}`}>
                  <TableCell className="font-medium">
                    <span className="flex items-center gap-2 flex-wrap">
                      {a.student_name}
                      {a.is_makeup && (
                        <Badge
                          className="bg-accent/10 text-accent border-0 text-xs"
                          title="Dikerjakan melalui jadwal ujian susulan"
                          data-testid={`makeup-tag-${a.id}`}
                        >
                          <CalendarPlus className="h-3 w-3 mr-1" />Susulan
                        </Badge>
                      )}
                    </span>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{a.student_identifier || "-"}</TableCell>
                  <TableCell><Badge variant="outline">{STATUS_LABEL[a.status] || a.status}</Badge></TableCell>
                  <TableCell className="font-semibold">{a.score != null ? a.score : "—"}</TableCell>
                  <TableCell data-testid={`violations-${a.id}`}>
                    {a.violations?.length ? (
                      <Badge
                        className="bg-destructive/10 text-destructive border-0"
                        title={a.auto_submitted_reason === "pelanggaran"
                          ? "Dikumpulkan otomatis karena melewati batas pelanggaran"
                          : "Keluar dari layar ujian"}
                      >
                        <ShieldAlert className="h-3 w-3 mr-1" />{a.violations.length}
                        {a.auto_submitted_reason === "pelanggaran" && " · auto"}
                      </Badge>
                    ) : (
                      <span className="text-muted-foreground text-sm">—</span>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{fmtDateTime(a.submitted_at)}</TableCell>
                  <TableCell className="text-right">
                    <Button size="sm" variant="ghost" onClick={() => downloadPdf(a.id)} data-testid={`pdf-btn-${a.id}`} className="mr-1"><Download className="h-4 w-4" /></Button>
                    <Button size="sm" variant={a.status === "menunggu_koreksi" ? "default" : "outline"} onClick={() => openGrade(a)} data-testid={`grade-btn-${a.id}`}>
                      {a.status === "menunggu_koreksi" ? "Koreksi" : "Lihat"}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {data.attempts.length === 0 && (
                <TableRow><TableCell colSpan={7} className="text-center text-muted-foreground py-10">Belum ada peserta.</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    );
  }

  // ---- Session list
  return (
    <div data-testid="results-page">
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">Penilaian</p>
      <h1 className="font-heading text-3xl sm:text-4xl font-semibold tracking-tight mt-1 mb-8">Hasil & Koreksi</h1>
      {sessions.length === 0 ? (
        <div className="border border-dashed border-border rounded-md p-16 text-center text-muted-foreground">
          <ClipboardCheck className="h-10 w-10 mx-auto mb-3 opacity-40" />Belum ada sesi ujian.
        </div>
      ) : (
        <div className="space-y-3">
          {sessions.map((s) => (
            <button key={s.id} onClick={() => openSession(s)} data-testid={`open-results-${s.id}`}
              className="w-full text-left bg-card border border-border rounded-md p-5 flex items-center justify-between hover:border-primary/40 hover:bg-primary/5 transition-colors">
              <div>
                <h3 className="font-heading text-lg font-medium">{s.title}</h3>
                <p className="text-sm text-muted-foreground">{s.package_title} · {fmtDateTime(s.start_time)}</p>
              </div>
              <ChevronRight className="h-5 w-5 text-muted-foreground" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
