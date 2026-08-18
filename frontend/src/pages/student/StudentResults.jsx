import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ClipboardList, ChevronRight } from "lucide-react";
import api from "../../lib/api";
import { fmtDateTime, STATUS_LABEL } from "../../lib/utils2";
import { Badge } from "../../components/ui/badge";

export default function StudentResults() {
  const [items, setItems] = useState([]);
  const nav = useNavigate();

  useEffect(() => { api.get("/results/me").then((r) => setItems(r.data)); }, []);

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} data-testid="student-results">
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">Laporan</p>
      <h1 className="font-heading text-3xl sm:text-4xl font-semibold tracking-tight mt-1 mb-8">Hasil Ujian Saya</h1>

      {items.length === 0 ? (
        <div className="border border-dashed border-border rounded-md p-16 text-center text-muted-foreground">
          <ClipboardList className="h-10 w-10 mx-auto mb-3 opacity-40" />Belum ada hasil ujian.
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((a) => {
            const passed = a.score != null && a.score >= a.kkm;
            return (
              <button key={a.id} onClick={() => nav(`/hasil/${a.id}`)} data-testid={`result-${a.id}`}
                className="w-full text-left bg-card border border-border rounded-md p-6 flex items-center justify-between gap-4 hover:border-primary/40 hover:bg-primary/5 transition-colors">
                <div>
                  <h3 className="font-heading text-lg font-medium">{a.session_title}</h3>
                  <p className="text-sm text-muted-foreground">Dikumpulkan {fmtDateTime(a.submitted_at)}</p>
                  {a.status === "menunggu_koreksi" && <Badge variant="outline" className="mt-2">{STATUS_LABEL.menunggu_koreksi}</Badge>}
                </div>
                <div className="flex items-center gap-4">
                  {a.score != null ? (
                    <div className="text-right">
                      <p className={`font-heading text-3xl font-bold ${passed ? "text-primary" : "text-destructive"}`}>{a.score}</p>
                      <p className="text-xs text-muted-foreground">KKM {a.kkm} · {passed ? "Lulus" : "Belum Lulus"}</p>
                    </div>
                  ) : (
                    <span className="text-sm text-muted-foreground">Menunggu nilai</span>
                  )}
                  <ChevronRight className="h-5 w-5 text-muted-foreground" />
                </div>
              </button>
            );
          })}
        </div>
      )}
    </motion.div>
  );
}
