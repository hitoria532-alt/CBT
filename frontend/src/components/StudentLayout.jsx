import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useEffect, useState, useRef } from "react";
import { GraduationCap, Home, ClipboardList, LogOut, Bell, Radio, Clock, Megaphone, Trophy } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import api from "../lib/api";
import { fmtDateTime } from "../lib/utils2";
import { Button } from "./ui/button";

const ICON = { live: Radio, upcoming: Clock, info: Megaphone };
const TONE = { live: "text-primary", upcoming: "text-secondary-foreground", info: "text-accent" };

export default function StudentLayout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [notes, setNotes] = useState([]);
  const [open, setOpen] = useState(false);
  const [lastSeen, setLastSeen] = useState(() => Number(localStorage.getItem("notif_seen") || 0));
  const ref = useRef();

  useEffect(() => {
    const fetchNotes = () => api.get("/notifications").then((r) => setNotes(r.data)).catch(() => {});
    fetchNotes();
    const t = setInterval(fetchNotes, 60000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const onClick = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const unread = notes.filter((n) => new Date(n.time).getTime() > lastSeen).length;
  const toggle = () => {
    const next = !open;
    setOpen(next);
    if (next) { const now = Date.now(); localStorage.setItem("notif_seen", String(now)); setLastSeen(now); }
  };

  const doLogout = async () => { await logout(); nav("/login", { replace: true }); };

  const link = ({ isActive }) =>
    `flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
      isActive ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground hover:bg-muted"
    }`;

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-20 h-16 border-b border-border bg-background/80 backdrop-blur-xl">
        <div className="max-w-5xl mx-auto h-full px-4 sm:px-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-primary flex items-center justify-center">
              <GraduationCap className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="font-heading text-lg font-semibold tracking-tight hidden sm:block">CBT Ujian</span>
          </div>
          <nav className="flex items-center gap-1">
            <NavLink to="/beranda" className={link} data-testid="nav-beranda">
              <Home className="h-4 w-4" /> <span className="hidden sm:inline">Beranda</span>
            </NavLink>
            <NavLink to="/hasil" end className={link} data-testid="nav-hasil-saya">
              <ClipboardList className="h-4 w-4" /> <span className="hidden sm:inline">Hasil Saya</span>
            </NavLink>
            <NavLink to="/peringkat" className={link} data-testid="nav-peringkat">
              <Trophy className="h-4 w-4" /> <span className="hidden sm:inline">Peringkat</span>
            </NavLink>
          </nav>
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="relative" ref={ref}>
              <button onClick={toggle} data-testid="notif-bell" className="relative p-2 rounded-md hover:bg-muted transition-colors">
                <Bell className="h-5 w-5" />
                {unread > 0 && (
                  <span data-testid="notif-badge" className="absolute -top-0.5 -right-0.5 h-4 min-w-4 px-1 rounded-full bg-accent text-accent-foreground text-[10px] font-bold flex items-center justify-center">
                    {unread}
                  </span>
                )}
              </button>
              {open && (
                <div data-testid="notif-panel" className="absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto bg-card border border-border rounded-md shadow-lg z-30">
                  <div className="px-4 py-3 border-b border-border">
                    <p className="font-heading font-semibold text-sm">Notifikasi</p>
                  </div>
                  {notes.length === 0 ? (
                    <p className="px-4 py-8 text-sm text-muted-foreground text-center">Tidak ada notifikasi.</p>
                  ) : (
                    <div className="divide-y divide-border">
                      {notes.map((n) => {
                        const Icon = ICON[n.type] || Megaphone;
                        return (
                          <div key={n.id} className="px-4 py-3 flex gap-3 hover:bg-muted/40" data-testid={`notif-${n.type}`}>
                            <Icon className={`h-4 w-4 mt-0.5 shrink-0 ${TONE[n.type]}`} />
                            <div className="min-w-0">
                              <p className="text-sm font-medium truncate">{n.title}</p>
                              <p className="text-xs text-muted-foreground">{n.message}</p>
                              <p className="text-[11px] text-muted-foreground mt-0.5">{fmtDateTime(n.time)}</p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
            <span className="text-sm font-medium hidden sm:block">{user.name}</span>
            <Button variant="ghost" size="sm" onClick={doLogout} data-testid="logout-button">
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        <Outlet />
      </main>
    </div>
  );
}
