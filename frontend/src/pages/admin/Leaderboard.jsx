import { useEffect, useState } from "react";
import { Trophy, Medal } from "lucide-react";
import api from "../../lib/api";
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "../../components/ui/select";

const MEDAL = { 1: "text-amber-400", 2: "text-slate-400", 3: "text-amber-700" };
const ALL = "__all__";

export default function Leaderboard() {
  const [classes, setClasses] = useState([]);
  const [cid, setCid] = useState(ALL);
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/classes").then((r) => setClasses(r.data));
  }, []);

  useEffect(() => {
    if (cid === ALL) {
      api.get("/leaderboard/global").then((r) => setData({ class_name: "Angkatan (Semua Siswa)", rows: r.data.rows }));
    } else if (cid) {
      api.get(`/leaderboard/class/${cid}`).then((r) => setData(r.data));
    }
  }, [cid]);

  return (
    <div data-testid="leaderboard-page">
      <div className="flex items-end justify-between mb-8 gap-4 flex-wrap">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">Kompetisi</p>
          <h1 className="font-heading text-3xl sm:text-4xl font-semibold tracking-tight mt-1">Peringkat</h1>
        </div>
        <Select value={cid} onValueChange={setCid}>
          <SelectTrigger className="w-64" data-testid="leaderboard-class-select"><SelectValue placeholder="Pilih" /></SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL} data-testid="leaderboard-angkatan-option">🏆 Angkatan (Semua Siswa)</SelectItem>
            {classes.map((c) => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {!data || data.rows.length === 0 ? (
        <div className="border border-dashed border-border rounded-md p-16 text-center text-muted-foreground">
          <Trophy className="h-10 w-10 mx-auto mb-3 opacity-40" />Belum ada data nilai.
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
