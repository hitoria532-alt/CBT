import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Trophy, Medal, Globe } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import api from "../../lib/api";
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "../../components/ui/select";

const MEDAL = { 1: "text-amber-400", 2: "text-slate-400", 3: "text-amber-700" };

function RankRow({ r, me }) {
  return (
    <div className={`flex items-center gap-4 rounded-md border p-4 ${me ? "bg-accent/10 border-accent ring-1 ring-accent" : r.rank <= 3 ? "bg-primary/5 border-primary/30" : "bg-card border-border"}`}>
      <div className="w-10 flex justify-center shrink-0">
        {r.rank <= 3 ? <Medal className={`h-7 w-7 ${MEDAL[r.rank]}`} /> : <span className="font-heading text-lg font-semibold text-muted-foreground">{r.rank}</span>}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate">{r.name}{me && <span className="text-accent"> (Anda)</span>}</p>
        <p className="text-xs text-muted-foreground">{r.completed} ujian selesai{r.classes && r.classes.length > 0 && ` · ${r.classes.join(", ")}`}</p>
      </div>
      <div className="text-right shrink-0">
        <p className="font-heading text-2xl font-bold text-primary">{r.avg_score}</p>
        <p className="text-xs text-muted-foreground">rata-rata</p>
      </div>
    </div>
  );
}

export default function StudentLeaderboard() {
  const { user } = useAuth();
  const [groups, setGroups] = useState([]);
  const [global, setGlobal] = useState(null);
  const [categories, setCategories] = useState([]);
  const [catId, setCatId] = useState("all");

  useEffect(() => { api.get("/categories").then((r) => setCategories(r.data)); }, []);

  useEffect(() => {
    const q = catId && catId !== "all" ? `?category_id=${catId}` : "";
    api.get(`/leaderboard/me${q}`).then((r) => setGroups(r.data));
    api.get(`/leaderboard/global${q}`).then((r) => setGlobal(r.data.rows));
  }, [catId]);

  let globalView = [];
  if (global) {
    globalView = global.slice(0, 10);
    if (!globalView.some((r) => r.student_id === user.id)) {
      const mine = global.find((r) => r.student_id === user.id);
      if (mine) globalView = [...globalView, mine];
    }
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} data-testid="student-leaderboard">
      <div className="flex items-end justify-between gap-4 flex-wrap mb-8">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">Kompetisi</p>
          <h1 className="font-heading text-3xl sm:text-4xl font-semibold tracking-tight mt-1">Peringkat</h1>
        </div>
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Mata Pelajaran</label>
          <Select value={catId} onValueChange={setCatId}>
            <SelectTrigger className="w-52" data-testid="student-subject-filter"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Semua Mapel</SelectItem>
              {categories.map((c) => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="mb-10" data-testid="lb-angkatan">
        <div className="flex items-center gap-2 mb-4">
          <Globe className="h-5 w-5 text-primary" />
          <h2 className="font-heading text-xl font-medium">Peringkat Angkatan</h2>
        </div>
        {globalView.length === 0 ? (
          <p className="text-sm text-muted-foreground">Belum ada data nilai.</p>
        ) : (
          <div className="space-y-3">
            {globalView.map((r) => <RankRow key={r.student_id} r={r} me={r.student_id === user.id} />)}
          </div>
        )}
      </div>

      {groups.map((g) => (
        <div key={g.class_id} className="mb-10" data-testid={`lb-class-${g.class_id}`}>
          <h2 className="font-heading text-xl font-medium mb-4">{g.class_name}</h2>
          {g.rows.length === 0 ? (
            <p className="text-sm text-muted-foreground">Belum ada data nilai.</p>
          ) : (
            <div className="space-y-3">
              {g.rows.map((r) => <RankRow key={r.student_id} r={r} me={r.student_id === user.id} />)}
            </div>
          )}
        </div>
      ))}

      {groups.length === 0 && globalView.length === 0 && (
        <div className="border border-dashed border-border rounded-md p-16 text-center text-muted-foreground">
          <Trophy className="h-10 w-10 mx-auto mb-3 opacity-40" />Belum ada data peringkat.
        </div>
      )}
    </motion.div>
  );
}
