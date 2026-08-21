import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, FolderTree, FileQuestion, Package, CalendarClock,
  ClipboardCheck, Users, LogOut, GraduationCap, Menu, X, School, Trophy, Settings,
} from "lucide-react";
import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { ROLE_LABEL } from "../lib/utils2";
import { Button } from "./ui/button";

const LINKS = [
  { to: "/admin", end: true, label: "Dashboard", icon: LayoutDashboard },
  { to: "/admin/kategori", label: "Kategori Materi", icon: FolderTree },
  { to: "/admin/soal", label: "Bank Soal", icon: FileQuestion },
  { to: "/admin/paket", label: "Paket Soal", icon: Package },
  { to: "/admin/sesi", label: "Sesi Pelaksanaan", icon: CalendarClock },
  { to: "/admin/kelas", label: "Manajemen Kelas", icon: School },
  { to: "/admin/hasil", label: "Hasil & Koreksi", icon: ClipboardCheck },
  { to: "/admin/peringkat", label: "Peringkat Kelas", icon: Trophy },
  { to: "/admin/pengaturan", label: "Pengaturan Sekolah", icon: Settings, adminOnly: true },
  { to: "/admin/akun", label: "Manajemen Akun", icon: Users, adminOnly: true },
];

export default function AdminLayout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);

  const doLogout = async () => {
    await logout();
    nav("/login", { replace: true });
  };

  const links = LINKS.filter((l) => !l.adminOnly || user.role === "admin");

  const SidebarInner = () => (
    <div className="flex flex-col h-full">
      <div className="h-16 flex items-center gap-3 px-6 border-b border-border">
        <div className="h-9 w-9 rounded-lg bg-primary flex items-center justify-center">
          <GraduationCap className="h-5 w-5 text-primary-foreground" />
        </div>
        <span className="font-heading text-lg font-semibold tracking-tight">CBT Ujian</span>
      </div>
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.end}
            onClick={() => setOpen(false)}
            data-testid={`nav-${l.label.toLowerCase().replace(/\s+/g, "-")}`}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`
            }
          >
            <l.icon className="h-4 w-4 shrink-0" />
            {l.label}
          </NavLink>
        ))}
      </nav>
      <div className="p-4 border-t border-border">
        <div className="flex items-center gap-3 px-2 py-2 mb-2">
          <div className="h-9 w-9 rounded-full bg-secondary/30 flex items-center justify-center text-sm font-semibold text-primary">
            {user.name?.[0]?.toUpperCase()}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium truncate">{user.name}</p>
            <p className="text-xs text-muted-foreground">{ROLE_LABEL[user.role]}</p>
          </div>
        </div>
        <Button
          variant="ghost"
          onClick={doLogout}
          data-testid="logout-button"
          className="w-full justify-start text-muted-foreground hover:text-destructive"
        >
          <LogOut className="h-4 w-4 mr-2" /> Keluar
        </Button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-background">
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex flex-col fixed inset-y-0 left-0 w-64 bg-card border-r border-border z-30">
        <SidebarInner />
      </aside>

      {/* Mobile drawer */}
      {open && (
        <div className="lg:hidden fixed inset-0 z-40">
          <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-64 bg-card border-r border-border">
            <SidebarInner />
          </aside>
        </div>
      )}

      <div className="lg:pl-64">
        <header className="h-16 lg:hidden flex items-center justify-between px-4 border-b border-border sticky top-0 bg-background/80 backdrop-blur-xl z-20">
          <button onClick={() => setOpen(true)} data-testid="mobile-menu-btn">
            <Menu className="h-6 w-6" />
          </button>
          <span className="font-heading font-semibold">CBT Ujian</span>
          <button onClick={doLogout}><LogOut className="h-5 w-5" /></button>
        </header>
        <main className="p-6 lg:p-10 max-w-7xl mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
