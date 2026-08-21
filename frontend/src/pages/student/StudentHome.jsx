import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  CalendarClock, Clock, PlayCircle, CheckCircle2, Lock, CalendarPlus,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import api from "../../lib/api";
import { fmtDateTime, STATUS_LABEL } from "../../lib/utils2";
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
            const mk = s.makeup;
            // Susulan yang masih berhak dikerjakan membatalkan status "selesai" dari
            // pengerjaan lama, sehingga siswa tetap bisa masuk lewat jendela susulan.
            const done =
              s.attempt_status && s.attempt_status !== "berlangsung" &&
              (!mk || mk.status === "sudah_dikerjakan");
            const viaMakeup = s.active_window === "susulan";
            const canStart = s.status === "berlangsung" && !done;
            const duration = viaMakeup ? (s.effective_duration || mk?.duration_minutes) : s.duration_minutes;
            return (
              <div
                key={s.id}
                className={`bg-card border rounded-md p-6 flex items-center justify-between gap-4 flex-wrap ${mk && mk.status !== "sudah_dikerjakan" ? "border-accent/40" : "border-border"}`}
                data-testid={`student-session-${s.id}`}
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                    <h3 className="font-heading text-lg font-medium">{s.title}</h3>
                    <Badge className={`${statusColor[s.status]} border-0`}>{STATUS_LABEL[s.status]}</Badge>
                    {mk && (
                      <Badge className="bg-accent/10 text-accent border-0" data-testid={`makeup-badge-${s.id}`}>
                        <CalendarPlus className="h-3 w-3 mr-1" />Ujian Susulan
                      </Badge>
                    )}
                    {done && <Badge className="bg-primary/10 text-primary border-0"><CheckCircle2 className="h-3 w-3 mr-1" />Selesai dikerjakan</Badge>}
                  </div>
                  <div className="text-sm text-muted-foreground space-y-0.5">
                    <p>{s.package_title} · {s.question_count} soal</p>
                    <p className="flex items-center gap-1.5"><Clock className="h-3.5 w-3.5" />Durasi {duration} menit</p>
                    <p>{fmtDateTime(s.start_time)} — {fmtDateTime(s.end_time)}</p>
                  </div>

                  {mk && mk.status !== "sudah_dikerjakan" && (
                    <div
                      className="mt-3 rounded-md border border-accent/30 bg-accent/5 px-3 py-2 text-sm"
                      data-testid={`makeup-info-${s.id}`}
                    >
                      <p className="font-medium text-accent flex items-center gap-1.5">
                        <CalendarPlus className="h-3.5 w-3.5" />
                        {mk.status === "berlangsung"
                          ? "Jadwal susulan Anda sedang dibuka"
                          : mk.status === "akan_datang"
                            ? "Jadwal susulan khusus untuk Anda"
                            : "Jadwal susulan sudah berakhir"}
                      </p>
                      <p className="text-muted-foreground text-xs mt-1">
                        {fmtDateTime(mk.start_time)} — {fmtDateTime(mk.end_time)} · durasi {mk.duration_minutes} menit
                      </p>
                      {mk.reason && (
                        <p className="text-muted-foreground text-xs mt-0.5 italic">Alasan: {mk.reason}</p>
                      )}
                    </div>
                  )}
                </div>
                <div>
                  {done ? (
                    <Button variant="outline" onClick={() => nav("/hasil")} data-testid={`view-result-${s.id}`}>Lihat Hasil</Button>
                  ) : canStart ? (
                    <Button onClick={() => nav(`/ujian/${s.id}`)} data-testid={`start-exam-${s.id}`}>
                      <PlayCircle className="h-4 w-4 mr-2" />
                      {s.attempt_status === "berlangsung"
                        ? "Lanjutkan"
                        : viaMakeup ? "Mulai Ujian Susulan" : "Mulai Ujian"}
                    </Button>
                  ) : (
                    <Button variant="outline" disabled data-testid={`locked-exam-${s.id}`}>
                      <Lock className="h-4 w-4 mr-2" />{s.status === "akan_datang" ? "Belum Dibuka" : "Ditutup"}
                    </Button>
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
