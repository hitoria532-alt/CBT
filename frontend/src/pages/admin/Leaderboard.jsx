import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Trophy, Medal, Download, Filter, X } from "lucide-react";
import api, { apiError } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "../../components/ui/select";

const MEDAL = { 1: "text-amber-400", 2: "text-slate-400", 3: "text-amber-700" };
const ALL = "__all__";

export default function Leaderboard() {
  const [classes, setClasses] = useState([]);
  const [categories, setCategories] = useState([]);
  const [cid, setCid] = useState(ALL);
  const [data, setData] = useState(null);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [catId, setCatId] = useState("all");

  useEffect(() => {
    api.get("/classes").then((r) => setClasses(r.data));
    api.get("/categories").then((r) => setCategories(r.data));
  }, []);

  const globalParams = () => {
    const p = new URLSearchParams();
    if (start) p.set("start", start);
    if (end) p.set("end", end);
    if (catId && catId !== "all") p.set("category_id", catId);
    return p.toString();
  };

  const loadData = () => {
    if (cid === ALL) {
      const qs = globalParams();
      api.get(`/leaderboard/global${qs ? `?${qs}` : ""}`).then((r) => setData({ rows: r.data.rows }));
    } else if (cid) {
      api.get(`/leaderboard/class/${cid}`).then((r) => setData(r.data));
    }
  };

  useEffect(loadData, [cid, start, end, catId]); // eslint-disable-line

  const clearFilters = () => { setStart(""); setEnd(""); setCatId("all"); };
  const hasFilter = start || end || (catId && catId !== "all");

  const exportXlsx = async () => {
    try {
      const qs = globalParams();
      const res = await api.get(`/export/leaderboard/xlsx${qs ? `?${qs}` : ""}`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a"); a.href = url; a.download = "peringkat-angkatan.xlsx"; a.click();
      toast.success("Peringkat diunduh");
    } catch (e) { toast.error(apiError(e)); }
  };

  const isGlobal = cid === ALL;

  return (
    <div data-testid="leaderboard-page">
      <div className="flex items-end justify-between mb-6 gap-4 flex-wrap">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">Kompetisi</p>
          <h1 className="font-heading text-3xl sm:text-4xl font-semibold tracking-tight mt-1">Peringkat</h1>
        </div>
        <div className="flex gap-3">
          {isGlobal && (
            <Button variant="outline" onClick={exportXlsx} data-testid="export-leaderboard-btn"><Download className="h-4 w-4 mr-2" />Ekspor Excel</Button>
          )}
          <Select value={cid} onValueChange={setCid}>
            <SelectTrigger className="w-64" data-testid="leaderboard-class-select"><SelectValue placeholder="Pilih" /></SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL} data-testid="leaderboard-angkatan-option">🏆 Angkatan (Semua Siswa)</SelectItem>
              {classes.map((c) => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
      </div>

      {isGlobal && (
        <div className="bg-card border border-border rounded-md p-4 mb-6 flex flex-wrap items-end gap-4" data-testid="leaderboard-filters">
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <Filter className="h-4 w-4" /> Filter
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Dari Tanggal</Label>
            <Input type="date" value={start} onChange={(e) => setStart(e.target.value)} className="h-9 w-40" data-testid="filter-start-date" />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Sampai Tanggal</Label>
            <Input type="date" value={end} onChange={(e) => setEnd(e.target.value)} className="h-9 w-40" data-testid="filter-end-date" />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Mata Pelajaran</Label>
            <Select value={catId} onValueChange={setCatId}>
              <SelectTrigger className="h-9 w-48" data-testid="filter-category"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Semua Mapel</SelectItem>
                {categories.map((c) => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          {hasFilter && (
            <Button variant="ghost" size="sm" onClick={clearFilters} data-testid="clear-filters-btn"><X className="h-4 w-4 mr-1" />Reset</Button>
          )}
        </div>
      )}

      {!data || data.rows.length === 0 ? (
        <div className="border border-dashed border-border rounded-md p-16 text-center text-muted-foreground">
          <Trophy className="h-10 w-10 mx-auto mb-3 opacity-40" />Belum ada data nilai untuk filter ini.
        </div>
      ) : (
        <div className="space-y-3">
          {data.rows.map((r) => (
            <div key={r.student_id} data-testid={`rank-row-${r.rank}`}
              className={`flex items-center gap-4 rounded-md border p-4 ${r.rank <= 3 ? "bg-primary/5 border-primary/30" : "bg-card border-border"}`}>
              <div className="w-10 flex justify-center shrink-0">
                {r.rank <= 3 ? <Medal className={`h-7 w-7 ${MEDAL[r.rank]}`} /> : <span className="font-heading text-lg font-semibold text-muted-foreground">{r.rank}</span>}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{r.name}</p>
                <p className="text-xs text-muted-foreground">
                  {r.identifier || "—"} · {r.completed} ujian selesai
                  {r.classes && r.classes.length > 0 && ` · ${r.classes.join(", ")}`}
                </p>
              </div>
              <div className="text-right shrink-0">
                <p className="font-heading text-2xl font-bold text-primary">{r.avg_score}</p>
                <p className="text-xs text-muted-foreground">rata-rata</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
