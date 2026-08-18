import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Users, FileQuestion, Package, CalendarClock, GraduationCap, TrendingUp,
  ClipboardCheck, AlertCircle,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid,
  LineChart, Line,
} from "recharts";
import api from "../../lib/api";

function Stat({ icon: Icon, label, value, accent }) {
  return (
    <div className="bg-card border border-border rounded-md p-6 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.15em] text-muted-foreground">{label}</p>
          <p className="font-heading text-3xl font-semibold mt-2">{value}</p>
        </div>
        <div className={`h-10 w-10 rounded-md flex items-center justify-center ${accent}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [s, setS] = useState(null);
  const [ca, setCa] = useState(null);
  const [subs, setSubs] = useState(null);

  useEffect(() => {
    api.get("/dashboard/stats").then((r) => setS(r.data)).catch(() => {});
    api.get("/analytics/classes").then((r) => setCa(r.data)).catch(() => {});
    api.get("/analytics/subjects").then((r) => setSubs(r.data)).catch(() => {});
  }, []);

  if (!s) return <div className="text-muted-foreground">Memuat...</div>;

  const chartData = [
    { name: "Siswa", jumlah: s.students },
    { name: "Guru", jumlah: s.teachers },
    { name: "Soal", jumlah: s.questions },
    { name: "Paket", jumlah: s.packages },
    { name: "Sesi", jumlah: s.sessions },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      data-testid="admin-dashboard"
    >
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">Ringkasan</p>
      <h1 className="font-heading text-3xl sm:text-4xl font-semibold tracking-tight mt-1 mb-8">
        Dashboard
      </h1>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <Stat icon={GraduationCap} label="Total Siswa" value={s.students} accent="bg-primary/10 text-primary" />
        <Stat icon={Users} label="Total Guru" value={s.teachers} accent="bg-secondary/20 text-secondary-foreground" />
        <Stat icon={FileQuestion} label="Bank Soal" value={s.questions} accent="bg-primary/10 text-primary" />
        <Stat icon={Package} label="Paket Soal" value={s.packages} accent="bg-secondary/20 text-secondary-foreground" />
        <Stat icon={CalendarClock} label="Sesi Ujian" value={s.sessions} accent="bg-primary/10 text-primary" />
        <Stat icon={TrendingUp} label="Rata-rata Nilai" value={s.avg_score} accent="bg-accent/10 text-accent" />
        <Stat icon={ClipboardCheck} label="Ujian Selesai" value={s.completed_attempts} accent="bg-primary/10 text-primary" />
        <Stat icon={AlertCircle} label="Perlu Dikoreksi" value={s.pending_grading} accent="bg-accent/10 text-accent" />
      </div>

      <div className="bg-card border border-border rounded-md p-6 mt-8">
        <h3 className="font-heading text-xl font-medium mb-6">Statistik Data</h3>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
              <XAxis dataKey="name" stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} allowDecimals={false} />
              <Tooltip
                contentStyle={{
                  background: "hsl(var(--card))", border: "1px solid hsl(var(--border))",
                  borderRadius: "0.5rem", fontSize: "0.85rem",
                }}
              />
              <Bar dataKey="jumlah" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} maxBarSize={64} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2 mt-6">
        <div className="bg-card border border-border rounded-md p-6" data-testid="class-avg-chart">
          <h3 className="font-heading text-xl font-medium mb-1">Rata-rata Nilai per Kelas</h3>
          <p className="text-sm text-muted-foreground mb-6">Perbandingan capaian antar kelas</p>
          <div className="h-64">
            {ca && ca.classes.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={ca.classes} layout="vertical" margin={{ left: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                  <XAxis type="number" domain={[0, 100]} stroke="hsl(var(--muted-foreground))" fontSize={12} />
                  <YAxis type="category" dataKey="name" stroke="hsl(var(--muted-foreground))" fontSize={12} width={90} />
                  <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "0.5rem", fontSize: "0.85rem" }} />
                  <Bar dataKey="avg_score" name="Rata-rata" fill="hsl(var(--accent))" radius={[0, 4, 4, 0]} maxBarSize={40} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-muted-foreground">Belum ada data kelas.</div>
            )}
          </div>
        </div>

        <div className="bg-card border border-border rounded-md p-6" data-testid="score-trend-chart">
          <h3 className="font-heading text-xl font-medium mb-1">Tren Rata-rata Nilai</h3>
          <p className="text-sm text-muted-foreground mb-6">Rata-rata nilai tiap sesi ujian</p>
          <div className="h-64">
            {ca && ca.trend.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={ca.trend} margin={{ left: -8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                  <XAxis dataKey="session" stroke="hsl(var(--muted-foreground))" fontSize={11} />
                  <YAxis domain={[0, 100]} stroke="hsl(var(--muted-foreground))" fontSize={12} />
                  <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "0.5rem", fontSize: "0.85rem" }} />
                  <Line type="monotone" dataKey="avg" name="Rata-rata" stroke="hsl(var(--primary))" strokeWidth={2.5} dot={{ r: 4, fill: "hsl(var(--primary))" }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-muted-foreground">Belum ada nilai ujian.</div>
            )}
          </div>
        </div>
      </div>
      <div className="bg-card border border-border rounded-md p-6 mt-6" data-testid="subject-stats-chart">
        <h3 className="font-heading text-xl font-medium mb-1">Rata-rata Nilai per Mata Pelajaran</h3>
        <p className="text-sm text-muted-foreground mb-6">Materi terkuat (kiri) hingga terlemah (kanan)</p>
        <div className="h-72">
          {subs && subs.some((x) => x.attempts > 0) ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={subs.filter((x) => x.attempts > 0)} margin={{ left: -8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                <XAxis dataKey="name" stroke="hsl(var(--muted-foreground))" fontSize={11} />
                <YAxis domain={[0, 100]} stroke="hsl(var(--muted-foreground))" fontSize={12} />
                <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "0.5rem", fontSize: "0.85rem" }} />
                <Bar dataKey="avg_score" name="Rata-rata" fill="hsl(var(--chart-4))" radius={[4, 4, 0, 0]} maxBarSize={56} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-sm text-muted-foreground">Belum ada nilai per mata pelajaran.</div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
