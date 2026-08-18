import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Trophy, Medal } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import api from "../../lib/api";

const MEDAL = { 1: "text-amber-400", 2: "text-slate-400", 3: "text-amber-700" };

export default function StudentLeaderboard() {
  const { user } = useAuth();
  const [groups, setGroups] = useState([]);

  useEffect(() => { api.get("/leaderboard/me").then((r) => setGroups(r.data)); }, []);

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} data-testid="student-leaderboard">
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">Kompetisi</p>
      <h1 className="font-heading text-3xl sm:text-4xl font-semibold tracking-tight mt-1 mb-8">Peringkat Kelas</h1>

      {groups.length === 0 ? (
        <div className="border border-dashed border-border rounded-md p-16 text-center text-muted-foreground">
          <Trophy className="h-10 w-10 mx-auto mb-3 opacity-40" />Anda belum tergabung dalam kelas mana pun.
        </div>
      ) : (
        <div className="space-y-10">
          {groups.map((g) => (
            <div key={g.class_id} data-testid={`lb-class-${g.class_id}`}>
              <h2 className="font-heading text-xl font-medium mb-4">{g.class_name}</h2>
              {g.rows.length === 0 ? (
                <p className="text-sm text-muted-foreground">Belum ada data nilai.</p>
              ) : (
                <div className="space-y-3">
                  {g.rows.map((r) => {
                    const me = r.student_id === user.id;
                    return (
                      <div key={r.student_id}
                        className={`flex items-center gap-4 rounded-md border p-4 ${me ? "bg-accent/10 border-accent ring-1 ring-accent" : r.rank <= 3 ? "bg-primary/5 border-primary/30" : "bg-card border-border"}`}>
                        <div className="w-10 flex justify-center shrink-0">
                          {r.rank <= 3 ? <Medal className={`h-7 w-7 ${MEDAL[r.rank]}`} /> : <span className="font-heading text-lg font-semibold text-muted-foreground">{r.rank}</span>}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium truncate">{r.name}{me && <span className="text-accent"> (Anda)</span>}</p>
                          <p className="text-xs text-muted-foreground">{r.completed} ujian selesai</p>
                        </div>
                        <div className="text-right shrink-0">
                          <p className="font-heading text-2xl font-bold text-primary">{r.avg_score}</p>
                          <p className="text-xs text-muted-foreground">rata-rata</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
}
