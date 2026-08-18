import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { GraduationCap, Home, ClipboardList, LogOut } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { Button } from "./ui/button";

export default function StudentLayout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();

  const doLogout = async () => {
    await logout();
    nav("/login", { replace: true });
  };

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
            <span className="font-heading text-lg font-semibold tracking-tight hidden sm:block">
              CBT Ujian
            </span>
          </div>
          <nav className="flex items-center gap-1">
            <NavLink to="/beranda" className={link} data-testid="nav-beranda">
              <Home className="h-4 w-4" /> <span className="hidden sm:inline">Beranda</span>
            </NavLink>
            <NavLink to="/hasil" end className={link} data-testid="nav-hasil-saya">
              <ClipboardList className="h-4 w-4" /> <span className="hidden sm:inline">Hasil Saya</span>
            </NavLink>
          </nav>
          <div className="flex items-center gap-3">
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
