import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Users, FileQuestion, Package, CalendarClock, GraduationCap, TrendingUp,
  ClipboardCheck, AlertCircle,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, LineChart, Line,
} from "recharts";
import api, { fileUrl } from "../../lib/api";
import ChartBox from "../../components/ChartBox";

function Stat({ icon: Icon, label, value, accent }) {
  return (
    <div className="group relative bg-card border border-border rounded-xl p-6 overflow-hidden hover:shadow-md hover:-translate-y-0.5 transition-all duration-300">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.15em] text-muted-foreground">{label}</p>
          <p className="font-heading text-3xl font-semibold mt-2">{value}</p>
        </div>
        <div className={`h-11 w-11 rounded-xl flex items-center justify-center ${accent} group-hover:scale-110 transition-transform duration-300`}>
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
  const [school, setSchool] = useState({ name: "", logo_path: null });

  useEffect(() => {
    api.get("/dashboard/stats").then((r) => setS(r.data)).catch(() => {});
    api.get("/analytics/classes").then((r) => setCa(r.data)).catch(() => {});
    api.get("/analytics/subjects").then((r) => setSubs(r.data)).catch(() => {});
    api.get("/settings/school").then((r) => setSchool(r.data)).catch(() => {});
  }, []);

  if (!s) return <div className="text-muted-foreground">Memuat...</div>;

  const today = new Date().toLocaleDateString("id-ID", { weekday: "long", day: "numeric", month: "long", year: "numeric" });

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
      <div className="relative overflow-hidden rounded-2xl bg-primary text-primary-foreground p-8 sm:p-10 mb-8 shadow-sm">
        <div className="absolute -right-16 -top-20 h-64 w-64 rounded-full bg-primary-foreground/5" />
        <div className="absolute right-24 -bottom-16 h-40 w-40 rounded-full bg-accent/15" />
        <div className="relative flex items-center gap-6 flex-wrap">
          <div className="h-24 w-24 rounded-2xl bg-primary-foreground/10 border border-primary-foreground/20 flex items-center justify-center shrink-0 overflow-hidden backdrop-blur">
            <img src={school.logo_path ? fileUrl(school.logo_path) : "/school-logo.png"} alt="Logo Sekolah" data-testid="school-logo" className="h-20 w-20 object-contain" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-bold uppercase tracking-[0.3em] text-primary-foreground/60">Selamat Datang</p>
            <h1 className="font-heading text-3xl sm:text-4xl font-semibold tracking-tight mt-1">{school.name || "Dashboard CBT Ujian"}</h1>
            <p className="text-primary-foreground/70 mt-2 text-sm capitalize">{school.address || today}</p>
          </div>
          <div className="text-right pl-4 border-l border-primary-foreground/15">
            <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-primary-foreground/60">Rata-rata Nilai</p>
            <p className="font-heading text-5xl font-bold mt-1">{s.avg_score}</p>
            <p className="text-xs text-primary-foreground/60 mt-1">{s.completed_attempts} ujian selesai</p>
          </div>
        </div>
      </div>

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

      <div className="bg-card border border-border rounded-xl p-6 mt-8">
        <h3 className="font-heading text-xl font-medium mb-6">Statistik Data</h3>
        <ChartBox className="h-72">
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
        </ChartBox>
      </div>

      <div className="grid gap-6 lg:grid-cols-2 mt-6">
        <div className="bg-card border border-border rounded-xl p-6" data-testid="class-avg-chart">
          <h3 className="font-heading text-xl font-medium mb-1">Rata-rata Nilai per Kelas</h3>
          <p className="text-sm text-muted-foreground mb-6">Perbandingan capaian antar kelas</p>
          <div className="h-64">
            {ca && ca.classes.length > 0 ? (
              <ChartBox className="h-full">
                <BarChart data={ca.classes} layout="vertical" margin={{ left: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                  <XAxis type="number" domain={[0, 100]} stroke="hsl(var(--muted-foreground))" fontSize={12} />
                  <YAxis type="category" dataKey="name" stroke="hsl(var(--muted-foreground))" fontSize={12} width={90} />
                  <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "0.5rem", fontSize: "0.85rem" }} />
                  <Bar dataKey="avg_score" name="Rata-rata" fill="hsl(var(--accent))" radius={[0, 4, 4, 0]} maxBarSize={40} />
                </BarChart>
              </ChartBox>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-muted-foreground">Belum ada data kelas.</div>
            )}
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl p-6" data-testid="score-trend-chart">
          <h3 className="font-heading text-xl font-medium mb-1">Tren Rata-rata Nilai</h3>
          <p className="text-sm text-muted-foreground mb-6">Rata-rata nilai tiap sesi ujian</p>
          <div className="h-64">
            {ca && ca.trend.length > 0 ? (
              <ChartBox className="h-full">
                <LineChart data={ca.trend} margin={{ left: -8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                  <XAxis dataKey="session" stroke="hsl(var(--muted-foreground))" fontSize={11} />
                  <YAxis domain={[0, 100]} stroke="hsl(var(--muted-foreground))" fontSize={12} />
                  <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "0.5rem", fontSize: "0.85rem" }} />
                  <Line type="monotone" dataKey="avg" name="Rata-rata" stroke="hsl(var(--primary))" strokeWidth={2.5} dot={{ r: 4, fill: "hsl(var(--primary))" }} />
                </LineChart>
              </ChartBox>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-muted-foreground">Belum ada nilai ujian.</div>
            )}
          </div>
        </div>
      </div>
      <div className="bg-card border border-border rounded-xl p-6 mt-6" data-testid="subject-stats-chart">
        <h3 className="font-heading text-xl font-medium mb-1">Rata-rata Nilai per Mata Pelajaran</h3>
        <p className="text-sm text-muted-foreground mb-6">Materi terkuat (kiri) hingga terlemah (kanan)</p>
        <div className="h-72">
          {subs && subs.some((x) => x.attempts > 0) ? (
            <ChartBox className="h-full">
              <BarChart data={subs.filter((x) => x.attempts > 0)} margin={{ left: -8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                <XAxis dataKey="name" stroke="hsl(var(--muted-foreground))" fontSize={11} />
                <YAxis domain={[0, 100]} stroke="hsl(var(--muted-foreground))" fontSize={12} />
                <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "0.5rem", fontSize: "0.85rem" }} />
                <Bar dataKey="avg_score" name="Rata-rata" fill="hsl(var(--chart-4))" radius={[4, 4, 0, 0]} maxBarSize={56} />
              </BarChart>
            </ChartBox>
          ) : (
            <div className="h-full flex items-center justify-center text-sm text-muted-foreground">Belum ada nilai per mata pelajaran.</div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
