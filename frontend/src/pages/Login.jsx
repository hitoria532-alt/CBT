import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { GraduationCap, Loader2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { apiError } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

const BG =
  "https://images.unsplash.com/photo-1601662528567-526cd06f6582?crop=entropy&cs=srgb&fm=jpg&q=85&w=1600";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const u = await login(email, password);
      nav(u.role === "siswa" ? "/beranda" : "/admin", { replace: true });
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-background">
      {/* Left brand panel */}
      <div className="relative hidden lg:flex flex-col justify-between bg-primary text-primary-foreground p-14 overflow-hidden">
        <img
          src={BG}
          alt=""
          className="absolute inset-0 w-full h-full object-cover opacity-10 mix-blend-overlay"
        />
        <div className="relative flex items-center gap-3">
          <div className="h-11 w-11 rounded-lg bg-primary-foreground/10 border border-primary-foreground/20 flex items-center justify-center">
            <GraduationCap className="h-6 w-6" />
          </div>
          <span className="font-heading text-xl font-semibold tracking-tight">CBT Ujian</span>
        </div>
        <div className="relative">
          <p className="text-xs font-bold uppercase tracking-[0.3em] text-primary-foreground/60 mb-4">
            Platform Ujian Berbasis Komputer
          </p>
          <h1 className="font-heading text-4xl xl:text-5xl font-semibold leading-tight tracking-tight">
            Kelola ujian, olah nilai, dan pantau hasil siswa dalam satu tempat.
          </h1>
          <p className="mt-6 text-primary-foreground/70 leading-relaxed max-w-md">
            Paket soal, sesi terjadwal, penilaian otomatis, dan laporan hasil yang rapi
            untuk admin, guru, dan siswa.
          </p>
        </div>
        <div className="relative text-sm text-primary-foreground/50">
          &copy; {new Date().getFullYear()} CBT Ujian Online
        </div>
      </div>

      {/* Right form */}
      <div className="flex items-center justify-center p-6 sm:p-12">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="w-full max-w-sm"
        >
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <div className="h-10 w-10 rounded-lg bg-primary flex items-center justify-center">
              <GraduationCap className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="font-heading text-lg font-semibold">CBT Ujian</span>
          </div>

          <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">
            Selamat datang
          </p>
          <h2 className="font-heading text-3xl font-semibold tracking-tight mt-2 mb-8">
            Masuk ke akun Anda
          </h2>

          <form onSubmit={submit} className="space-y-5" data-testid="login-form">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                data-testid="login-email-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="nama@sekolah.id"
                required
                className="h-11"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                data-testid="login-password-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="h-11"
              />
            </div>

            {error && (
              <div
                data-testid="login-error"
                className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md px-3 py-2"
              >
                {error}
              </div>
            )}

            <Button
              type="submit"
              disabled={loading}
              data-testid="login-submit-button"
              className="w-full h-11 active:scale-[0.98] transition-transform"
            >
              {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Masuk
            </Button>
          </form>

          <p className="text-xs text-muted-foreground mt-8 leading-relaxed">
            Belum punya akun? Hubungi administrator sekolah untuk pembuatan akun
            siswa, guru, atau admin.
          </p>
        </motion.div>
      </div>
    </div>
  );
}
