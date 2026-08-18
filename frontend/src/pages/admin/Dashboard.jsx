import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Users, FileQuestion, Package, CalendarClock, GraduationCap, TrendingUp,
  ClipboardCheck, AlertCircle,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid,
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

  useEffect(() => {
    api.get("/dashboard/stats").then((r) => setS(r.data)).catch(() => {});
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
    </motion.div>
  );
}
