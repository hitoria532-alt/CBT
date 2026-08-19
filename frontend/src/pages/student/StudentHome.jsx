import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { CalendarClock, Clock, PlayCircle, CheckCircle2, Lock, RotateCcw } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import api from "../../lib/api";
import { fmtDateTime, STATUS_LABEL, POLICY_LABEL } from "../../lib/utils2";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";

export default function StudentHome() {
  const { user } = useAuth();
  const [sessions, setSessions] = useState([]);
  const nav = useNavigate();

  useEffect(() => { api.get("/sessions").then((r) => setSessions(r.data)); }, []);

  const statusColor = {
    akan_datang: "bg-secondary/20 text-secondary-foreground",
    berlangsung: "bg-primary/10 text-primary",
    selesai: "bg-muted text-muted-foreground",
  };

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} data-testid="student-home">
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">Halo, {user.name}</p>
      <h1 className="font-heading text-3xl sm:text-4xl font-semibold tracking-tight mt-1 mb-8">Sesi Ujian</h1>

      {sessions.length === 0 ? (
        <div className="border border-dashed border-border rounded-md p-16 text-center text-muted-foreground">
          <CalendarClock className="h-10 w-10 mx-auto mb-3 opacity-40" />Belum ada sesi ujian yang dijadwalkan.
        </div>
      ) : (
        <div className="space-y-4">
          {sessions.map((s) => {
            const maxAtt = s.max_attempts || 1;
            const used = s.attempts_used || 0;
            const left = s.attempts_left != null ? s.attempts_left : (used ? 0 : 1);
            const ongoing = s.has_ongoing;
            const exhausted = !ongoing && left <= 0 && used > 0;
            const canStart = s.status === "berlangsung" && (ongoing || left > 0);
            const isRetake = !ongoing && used > 0 && left > 0;
            return (
              <div key={s.id} className="bg-card border border-border rounded-md p-6 flex items-center justify-between gap-4 flex-wrap" data-testid={`student-session-${s.id}`}>
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                    <h3 className="font-heading text-lg font-medium">{s.title}</h3>
                    <Badge className={`${statusColor[s.status]} border-0`}>{STATUS_LABEL[s.status]}</Badge>
                    {exhausted && <Badge className="bg-primary/10 text-primary border-0"><CheckCircle2 className="h-3 w-3 mr-1" />Selesai dikerjakan</Badge>}
                    {maxAtt > 1 && (
                      <Badge variant="outline" data-testid={`attempts-badge-${s.id}`}>
                        <RotateCcw className="h-3 w-3 mr-1" />Percobaan {used}/{maxAtt}
                      </Badge>
                    )}
                  </div>
                  <div className="text-sm text-muted-foreground space-y-0.5">
                    <p>{s.package_title} · {s.question_count} soal</p>
                    <p className="flex items-center gap-1.5"><Clock className="h-3.5 w-3.5" />Durasi {s.duration_minutes} menit</p>
                    <p>{fmtDateTime(s.start_time)} — {fmtDateTime(s.end_time)}</p>
                    {maxAtt > 1 && (
                      <p>
                        {left > 0 ? `Sisa kesempatan ${left}x` : "Kesempatan sudah habis"} · Nilai dipakai: {POLICY_LABEL[s.score_policy || "tertinggi"]}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex gap-2 flex-wrap">
                  {used > 0 && (
                    <Button variant="outline" onClick={() => nav("/hasil")} data-testid={`view-result-${s.id}`}>Lihat Hasil</Button>
                  )}
                  {canStart ? (
                    <Button onClick={() => nav(`/ujian/${s.id}`)} data-testid={`start-exam-${s.id}`}>
                      {ongoing ? <PlayCircle className="h-4 w-4 mr-2" /> : isRetake ? <RotateCcw className="h-4 w-4 mr-2" /> : <PlayCircle className="h-4 w-4 mr-2" />}
                      {ongoing ? "Lanjutkan" : isRetake ? "Ujian Ulang" : "Mulai Ujian"}
                    </Button>
                  ) : exhausted ? (
                    <Button variant="outline" disabled data-testid={`exhausted-${s.id}`}><Lock className="h-4 w-4 mr-2" />Batas Percobaan</Button>
                  ) : (
                    <Button variant="outline" disabled><Lock className="h-4 w-4 mr-2" />{s.status === "akan_datang" ? "Belum Dibuka" : "Ditutup"}</Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </motion.div>
  );
}
