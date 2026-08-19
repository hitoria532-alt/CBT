import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ClipboardList, ChevronRight, FileDown, RotateCcw } from "lucide-react";
import api, { apiError } from "../../lib/api";
import { fmtDateTime, STATUS_LABEL, POLICY_LABEL } from "../../lib/utils2";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { toast } from "sonner";

export default function StudentResults() {
  const [items, setItems] = useState([]);
  const nav = useNavigate();

  useEffect(() => { api.get("/results/me").then((r) => setItems(r.data)); }, []);

  const downloadReport = async () => {
    try {
      const res = await api.get(`/report/student/me/pdf`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a"); a.href = url; a.download = "rapor-saya.pdf"; a.click();
      toast.success("Rapor diunduh");
    } catch (e) { toast.error(apiError(e)); }
  };

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} data-testid="student-results">
      <div className="flex items-end justify-between gap-4 flex-wrap mb-8">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">Laporan</p>
          <h1 className="font-heading text-3xl sm:text-4xl font-semibold tracking-tight mt-1">Hasil Ujian Saya</h1>
        </div>
        <Button variant="outline" onClick={downloadReport} data-testid="download-report-btn"><FileDown className="h-4 w-4 mr-2" />Unduh Rapor (PDF)</Button>
      </div>

      {items.length === 0 ? (
        <div className="border border-dashed border-border rounded-md p-16 text-center text-muted-foreground">
          <ClipboardList className="h-10 w-10 mx-auto mb-3 opacity-40" />Belum ada hasil ujian.
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((a) => {
            const passed = a.score != null && a.score >= a.kkm;
            const multi = (a.max_attempts || 1) > 1;
            return (
              <button key={a.id} onClick={() => nav(`/hasil/${a.id}`)} data-testid={`result-${a.id}`}
                className="w-full text-left bg-card border border-border rounded-md p-6 flex items-center justify-between gap-4 hover:border-primary/40 hover:bg-primary/5 transition-colors">
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-heading text-lg font-medium">{a.session_title}</h3>
                    {multi && (
                      <Badge variant="outline" className="text-xs" data-testid={`attempt-no-${a.id}`}>
                        <RotateCcw className="h-3 w-3 mr-1" />Percobaan {a.attempt_number || 1}/{a.max_attempts}
                      </Badge>
                    )}
                    {multi && a.counted && (
                      <Badge className="bg-primary/10 text-primary border-0 text-xs" data-testid={`counted-${a.id}`}>Nilai dipakai</Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">Dikumpulkan {fmtDateTime(a.submitted_at)}</p>
                  {multi && a.counted && a.effective_score != null && (
                    <p className="text-xs text-muted-foreground mt-0.5">{POLICY_LABEL[a.score_policy]} = {a.effective_score}</p>
                  )}
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
