import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { Clock, ChevronLeft, ChevronRight, Send, LayoutGrid } from "lucide-react";
import api, { apiError } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Textarea } from "../../components/ui/textarea";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../../components/ui/dialog";

function fmtTime(sec) {
  if (sec < 0) sec = 0;
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  const p = (n) => String(n).padStart(2, "0");
  return h > 0 ? `${p(h)}:${p(m)}:${p(s)}` : `${p(m)}:${p(s)}`;
}

export default function ExamView() {
  const { sessionId } = useParams();
  const nav = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [answers, setAnswers] = useState({});
  const [idx, setIdx] = useState(0);
  const [dir, setDir] = useState(1);
  const [remaining, setRemaining] = useState(0);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [showPalette, setShowPalette] = useState(false);
  const submittedRef = useRef(false);

  useEffect(() => {
    api.post("/exam/start", { session_id: sessionId })
      .then((r) => {
        setData(r.data);
        setAnswers(r.data.answers || {});
        const endLimit = new Date(r.data.started_at).getTime() + r.data.session.duration_minutes * 60000;
        const endSession = new Date(r.data.session.end_time).getTime();
        const end = Math.min(endLimit, endSession);
        setRemaining(Math.floor((end - Date.now()) / 1000));
        setLoading(false);
      })
      .catch((e) => { toast.error(apiError(e)); nav("/beranda", { replace: true }); });
  }, [sessionId, nav]);

  const doSubmit = useCallback(async (auto = false) => {
    if (submittedRef.current) return;
    submittedRef.current = true;
    try {
      const r = await api.post("/exam/submit", { session_id: sessionId, answers });
      toast.success(auto ? "Waktu habis — jawaban otomatis dikumpulkan" :
        r.data.needs_grading ? "Terkumpul. Sebagian soal menunggu koreksi guru." :
        `Terkumpul! Nilai Anda: ${r.data.score}`);
      nav("/hasil", { replace: true });
    } catch (e) { toast.error(apiError(e)); submittedRef.current = false; }
  }, [answers, sessionId, nav]);

  // Timer
  useEffect(() => {
    if (loading) return;
    const t = setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 1) { clearInterval(t); doSubmit(true); return 0; }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(t);
  }, [loading, doSubmit]);

  // Autosave
  useEffect(() => {
    if (loading) return;
    const t = setTimeout(() => { api.post(`/exam/save/${sessionId}`, { answers }).catch(() => {}); }, 1200);
    return () => clearTimeout(t);
  }, [answers, loading, sessionId]);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center"><div className="h-8 w-8 rounded-full border-2 border-primary border-t-transparent animate-spin" /></div>;
  }

  const questions = data.questions;
  const q = questions[idx];
  const answered = questions.filter((qq) => {
    const a = answers[qq.id];
    return a !== undefined && a !== null && a !== "";
  }).length;
  const go = (n) => { setDir(n > idx ? 1 : -1); setIdx(n); setShowPalette(false); };
  const setAns = (val) => setAnswers((a) => ({ ...a, [q.id]: val }));
  const critical = remaining <= 300;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-20 border-b border-border bg-background/80 backdrop-blur-xl">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
          <div className="min-w-0">
            <p className="text-sm font-medium truncate">{data.session.title}</p>
            <p className="text-xs text-muted-foreground">{answered}/{questions.length} terjawab</p>
          </div>
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-md font-mono text-lg tracking-widest ${critical ? "bg-destructive/10 text-destructive animate-pulse" : "bg-muted text-foreground"}`} data-testid="exam-timer">
            <Clock className="h-4 w-4" />{fmtTime(remaining)}
          </div>
          <Button variant="outline" size="sm" onClick={() => setShowPalette(true)} data-testid="open-palette-btn"><LayoutGrid className="h-4 w-4" /></Button>
        </div>
        <div className="h-1 bg-muted">
          <div className="h-full bg-primary transition-all" style={{ width: `${(answered / questions.length) * 100}%` }} />
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-8 py-10">
        <AnimatePresence mode="wait" custom={dir}>
          <motion.div
            key={idx}
            custom={dir}
            initial={{ opacity: 0, x: dir * 40 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: dir * -40 }}
            transition={{ duration: 0.25 }}
          >
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground mb-3">Soal {idx + 1} dari {questions.length}</p>
            <p className="text-lg sm:text-xl leading-loose font-medium mb-8" data-testid="question-text">{q.text}</p>

            {q.type === "pg" && (
              <div className="space-y-3" data-testid="options-list">
                {q.options.map((opt, i) => {
                  const selected = String(answers[q.id]) === String(i);
                  return (
                    <button key={i} onClick={() => setAns(String(i))} data-testid={`option-${i}`}
                      className={`w-full text-left p-4 border rounded-md transition-colors flex items-start gap-4 ${selected ? "border-primary bg-primary/10 ring-1 ring-primary" : "border-border hover:border-primary/50 hover:bg-primary/5"}`}>
                      <span className={`h-7 w-7 rounded-full flex items-center justify-center text-sm font-semibold shrink-0 ${selected ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>{String.fromCharCode(65 + i)}</span>
                      <span className="pt-0.5">{opt}</span>
                    </button>
                  );
                })}
              </div>
            )}

            {q.type === "truefalse" && (
              <div className="grid grid-cols-2 gap-3">
                {[["true", "Benar"], ["false", "Salah"]].map(([val, label]) => {
                  const selected = answers[q.id] === val;
                  return (
                    <button key={val} onClick={() => setAns(val)} data-testid={`tf-${val}`}
                      className={`p-6 border rounded-md font-medium transition-colors ${selected ? "border-primary bg-primary/10 ring-1 ring-primary text-primary" : "border-border hover:border-primary/50 hover:bg-primary/5"}`}>
                      {label}
                    </button>
                  );
                })}
              </div>
            )}

            {q.type === "essay" && (
              <Textarea value={answers[q.id] || ""} onChange={(e) => setAns(e.target.value)} rows={8} placeholder="Tulis jawaban Anda di sini..." data-testid="essay-answer" className="text-base leading-relaxed" />
            )}
          </motion.div>
        </AnimatePresence>

        <div className="flex items-center justify-between mt-10">
          <Button variant="outline" onClick={() => go(idx - 1)} disabled={idx === 0} data-testid="prev-question-btn"><ChevronLeft className="h-4 w-4 mr-1" />Sebelumnya</Button>
          {idx < questions.length - 1 ? (
            <Button onClick={() => go(idx + 1)} data-testid="next-question-btn">Berikutnya<ChevronRight className="h-4 w-4 ml-1" /></Button>
          ) : (
            <Button onClick={() => setConfirmOpen(true)} data-testid="finish-exam-btn"><Send className="h-4 w-4 mr-2" />Kumpulkan</Button>
          )}
        </div>
      </main>

      {/* Palette */}
      <Dialog open={showPalette} onOpenChange={setShowPalette}>
        <DialogContent>
          <DialogHeader><DialogTitle>Navigasi Soal</DialogTitle></DialogHeader>
          <div className="grid grid-cols-6 gap-2 py-2">
            {questions.map((qq, i) => {
              const a = answers[qq.id];
              const done = a !== undefined && a !== null && a !== "";
              return (
                <button key={qq.id} onClick={() => go(i)} data-testid={`palette-${i}`}
                  className={`h-10 rounded-md text-sm font-medium border transition-colors ${i === idx ? "border-primary ring-1 ring-primary" : "border-border"} ${done ? "bg-primary text-primary-foreground" : "bg-background hover:bg-muted"}`}>
                  {i + 1}
                </button>
              );
            })}
          </div>
          <Button onClick={() => setConfirmOpen(true)} className="w-full"><Send className="h-4 w-4 mr-2" />Kumpulkan Ujian</Button>
        </DialogContent>
      </Dialog>

      {/* Confirm submit */}
      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Kumpulkan ujian?</DialogTitle></DialogHeader>
          <p className="text-sm text-muted-foreground">Anda telah menjawab {answered} dari {questions.length} soal. Jawaban tidak dapat diubah setelah dikumpulkan.</p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>Batal</Button>
            <Button onClick={() => doSubmit(false)} data-testid="confirm-submit-btn">Ya, Kumpulkan</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
