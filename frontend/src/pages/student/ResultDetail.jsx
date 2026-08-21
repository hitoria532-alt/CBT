import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, CheckCircle2, XCircle, Clock, Download } from "lucide-react";
import api, { fileUrl } from "../../lib/api";
import { QTYPE_LABEL } from "../../lib/utils2";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";

export default function ResultDetail() {
  const { attemptId } = useParams();
  const nav = useNavigate();
  const [a, setA] = useState(null);

  useEffect(() => { api.get(`/results/detail/${attemptId}`).then((r) => setA(r.data)); }, [attemptId]);

  const downloadPdf = async () => {
    const res = await api.get(`/results/detail/${attemptId}/pdf`, { responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const el = document.createElement("a"); el.href = url; el.download = "kartu-hasil.pdf"; el.click();
  };

  if (!a) return <div className="text-muted-foreground">Memuat...</div>;

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} data-testid="result-detail">
      <div className="flex items-center justify-between mb-6">
        <button onClick={() => nav("/hasil")} className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Kembali
        </button>
        <Button variant="outline" onClick={downloadPdf} data-testid="download-pdf-btn"><Download className="h-4 w-4 mr-2" />Unduh Kartu Hasil (PDF)</Button>
      </div>

      <div className="bg-card border border-border rounded-md p-8 mb-8 flex items-center justify-between gap-6 flex-wrap">
        <div>
          <h1 className="font-heading text-2xl font-semibold">{a.session_title}</h1>
          <p className="text-muted-foreground mt-1">Metode: {a.scoring_method === "weighted" ? "Berbobot per soal" : "Persentase"} · Skor {a.earned}/{a.total_possible} poin</p>
        </div>
        <div className="text-right">
          {a.score != null ? (
            <p className="font-heading text-5xl font-bold text-primary" data-testid="final-score">{a.score}</p>
          ) : (
            <Badge variant="outline"><Clock className="h-3 w-3 mr-1" />Menunggu Koreksi</Badge>
          )}
        </div>
      </div>

      <h3 className="font-heading text-xl font-medium mb-4">Detail Jawaban</h3>
      <div className="space-y-4">
        {a.details.map((d, i) => (
          <div key={i} className="bg-card border border-border rounded-md p-6" data-testid={`detail-${i}`}>
            <div className="flex items-center gap-2 mb-3 flex-wrap">
              <span className="font-heading font-semibold text-muted-foreground">Soal {i + 1}</span>
              <Badge variant="outline" className="text-xs">{QTYPE_LABEL[d.type]}</Badge>
              {d.type !== "essay" ? (
                d.is_correct ? <Badge className="bg-primary/10 text-primary border-0 text-xs"><CheckCircle2 className="h-3 w-3 mr-1" />Benar</Badge>
                             : <Badge className="bg-destructive/10 text-destructive border-0 text-xs"><XCircle className="h-3 w-3 mr-1" />Salah</Badge>
              ) : (
                <Badge variant="outline" className="text-xs">{d.needs_grading ? "Menunggu koreksi" : `Nilai ${d.points_earned}/${d.points_possible}`}</Badge>
              )}
            </div>
            <p className="text-sm font-medium leading-relaxed mb-3">{d.text}</p>
            {d.image_path && <img src={fileUrl(d.image_path)} alt="" className="mb-3 max-h-40 rounded border border-border" />}

            {d.type === "pg" && (
              <div className="space-y-1.5 text-sm">
                {d.options.map((o, oi) => {
                  const isAns = String(d.answer) === String(oi);
                  const isCorrect = String(d.correct_answer) === String(oi);
                  return (
                    <div key={oi} className={`px-3 py-2 rounded-md border ${isCorrect ? "border-primary bg-primary/5 text-primary" : isAns ? "border-destructive bg-destructive/5 text-destructive" : "border-transparent text-muted-foreground"}`}>
                      {String.fromCharCode(65 + oi)}. {o}
                      {isCorrect && " ✓ (kunci)"}
                      {isAns && !isCorrect && " ← jawaban Anda"}
                    </div>
                  );
                })}
              </div>
            )}
            {d.type === "truefalse" && (
              <p className="text-sm">Jawaban Anda: <span className="font-medium">{d.answer === "true" ? "Benar" : d.answer === "false" ? "Salah" : "(kosong)"}</span> · Kunci: <span className="font-medium text-primary">{d.correct_answer === "true" ? "Benar" : "Salah"}</span></p>
            )}
            {d.type === "essay" && (
              <p className="text-sm text-muted-foreground bg-muted/40 rounded-md p-3 whitespace-pre-wrap">{d.answer || "(tidak dijawab)"}</p>
            )}
          </div>
        ))}
      </div>
    </motion.div>
  );
}
