import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { Moon, Sun, Globe, LogOut, User as UserIcon } from "lucide-react";
import { useTheme } from "../contexts/ThemeContext";
import { useLang } from "../contexts/LanguageContext";
import { useAuth } from "../contexts/AuthContext";
import { Button } from "./ui/button";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Navbar() {
  const { theme, toggle } = useTheme();
  const { lang, setLang, t } = useLang();
  const { user, login, logout } = useAuth();
  const [isHost, setIsHost] = useState(false);

  useEffect(() => {
    if (!user) { setIsHost(false); return; }
    axios.get(`${API}/host/me`, { withCredentials: true })
      .then((r) => setIsHost(!!r.data?.is_host))
      .catch(() => setIsHost(false));
  }, [user]);

  return (
    <header className="sticky top-0 z-40 backdrop-blur-xl bg-background/70 border-b border-border/60">
      <div className="max-w-7xl mx-auto px-6 lg:px-10 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 group" data-testid="brand-link">
          <span className="w-2 h-2 rounded-full bg-primary group-hover:scale-125 transition-transform" />
          <span className="font-serif text-2xl tracking-tight">ZenStay</span>
        </Link>

        <nav className="hidden md:flex items-center gap-7 text-sm text-muted-foreground">
          <Link to="/listings" className="hover:text-foreground transition-colors" data-testid="nav-listings">
            {t.nav.listings}
          </Link>
          <Link to="/host" className="hover:text-foreground transition-colors" data-testid="nav-host">
            {t.nav.become_host}
          </Link>
          {user?.role === "admin" && (
            <Link to="/admin" className="hover:text-foreground transition-colors" data-testid="nav-admin">
              {t.nav.admin}
            </Link>
          )}
          {isHost && (
            <Link to="/host-portal" className="hover:text-foreground transition-colors" data-testid="nav-host-portal">
              {t.host_portal.title}
            </Link>
          )}
          {user && (
            <Link to="/dashboard" className="hover:text-foreground transition-colors" data-testid="nav-my-bookings">
              {t.nav.my_bookings}
            </Link>
          )}
        </nav>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setLang(lang === "fr" ? "en" : "fr")}
            className="px-3 h-9 rounded-full border border-border text-xs uppercase tracking-widest hover:bg-muted transition flex items-center gap-1.5"
            data-testid="lang-toggle"
            aria-label="Toggle language"
          >
            <Globe className="w-3.5 h-3.5" /> {lang.toUpperCase()}
          </button>
          <button
            onClick={toggle}
            className="w-9 h-9 rounded-full border border-border hover:bg-muted transition flex items-center justify-center"
            data-testid="theme-toggle"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
          {user ? (
            <div className="flex items-center gap-2 ml-1">
              <div className="hidden sm:flex items-center gap-2 px-3 h-9 rounded-full bg-muted text-sm">
                <UserIcon className="w-3.5 h-3.5" />
                <span className="max-w-[120px] truncate" data-testid="user-email">{user.name || user.email}</span>
              </div>
              <Button variant="ghost" size="sm" onClick={logout} data-testid="logout-btn" className="rounded-full">
                <LogOut className="w-4 h-4" />
              </Button>
            </div>
          ) : (
            <Button onClick={login} className="rounded-full" data-testid="login-btn">
              {t.nav.login}
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}
