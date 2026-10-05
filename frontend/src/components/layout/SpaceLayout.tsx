import { useState } from 'react';
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import clsx from 'clsx';
import {
  Bell,
  Building2,
  FileText,
  Home,
  LayoutDashboard,
  LogOut,
  Menu,
  Settings,
  ShieldCheck,
  X,
} from 'lucide-react';

import { BrandWordmark } from './Brand';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { useAuth } from '@/hooks/useAuth';
import { useDashboard } from '@/lib/hooks';
import { useOnlineStatus } from '@/hooks/useReveal';
import { formatPhone, initials } from '@/lib/format';

type NavItem = {
  to: string;
  label: string;
  icon: typeof Home;
  end?: boolean;
  permission?: string;
  space?: 'company' | 'admin';
};

const NAV: NavItem[] = [
  { to: '/espace', label: 'Vue d\u2019ensemble', icon: LayoutDashboard, end: true },
  { to: '/espace/proprietes', label: 'Mes propriétés', icon: Home },
  { to: '/espace/demandes', label: 'Mes demandes', icon: FileText },
  { to: '/espace/entreprise', label: 'Espace entreprise', icon: Building2, space: 'company' },
  { to: '/espace/admin', label: 'Back-office KEMTA', icon: ShieldCheck, space: 'admin' },
];

export function SpaceLayout() {
  const { user, signOut, spaces } = useAuth();
  const { data, isLoading } = useDashboard('CLIENT');
  const [menuOpen, setMenuOpen] = useState(false);
  const navigate = useNavigate();
  const online = useOnlineStatus();

  const unread = data?.statistics?.notifications?.unread ?? 0;
  const hasSpace = (key: 'company' | 'admin') =>
    (spaces ?? []).some((space) => space.key === key && space.available);

  const items = NAV.filter((item) => {
    if (!item.space) return true;
    return hasSpace(item.space);
  });

  const logout = async () => {
    await signOut();
    navigate('/', { replace: true });
  };

  const navLink = (item: NavItem, mobile = false) => {
    const Icon = item.icon;
    return (
      <NavLink
        key={item.to}
        to={item.to}
        end={item.end}
        onClick={() => setMenuOpen(false)}
        className={({ isActive }) =>
          clsx(
            'flex items-center gap-3 rounded-k px-3 py-2.5 text-[0.875rem] font-medium transition-colors',
            isActive
              ? mobile
                ? 'bg-k-blue-soft text-k-blue'
                : 'bg-white/10 text-white'
              : mobile
                ? 'text-k-ink hover:bg-k-mist'
                : 'text-white/75 hover:bg-white/10 hover:text-white',
          )
        }
      >
        <Icon className="size-4 shrink-0" aria-hidden />
        <span className="flex-1">{item.label}</span>
        {item.to === '/espace' && unread > 0 && !isLoading ? (
          <span className="inline-flex min-w-5 items-center justify-center rounded-full bg-k-green px-1.5 text-[0.625rem] font-semibold text-white">
            {unread}
          </span>
        ) : null}
      </NavLink>
    );
  };

  return (
    <div className="flex min-h-screen flex-col bg-k-mist lg:flex-row">
      {/* Barre supérieure mobile */}
      <header className="sticky top-0 z-40 flex items-center justify-between border-b border-k-line bg-white px-4 py-3 lg:hidden">
        <Link to="/" aria-label="KEMTA — accueil">
          <BrandWordmark />
        </Link>
        <div className="flex items-center gap-2">
          <Link
            to="/espace"
            className="relative inline-flex size-9 items-center justify-center rounded-k border border-k-line text-k-muted"
            aria-label={unread > 0 ? `Notifications : ${unread} non lues` : 'Notifications'}
          >
            <Bell className="size-4" aria-hidden />
            {unread > 0 ? <span className="absolute -right-0.5 -top-0.5 size-2.5 rounded-full bg-k-green" /> : null}
          </Link>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setMenuOpen((value) => !value)}
            aria-expanded={menuOpen}
            aria-label={menuOpen ? 'Fermer le menu' : 'Ouvrir le menu'}
            icon={menuOpen ? <X className="size-4" aria-hidden /> : <Menu className="size-4" aria-hidden />}
          />
        </div>
      </header>

      {menuOpen ? (
        <nav aria-label="Navigation de l'espace" className="border-b border-k-line bg-white px-3 py-3 lg:hidden">
          <div className="space-y-1">{items.map((item) => navLink(item, true))}</div>
          <div className="mt-3 flex items-center justify-between border-t border-k-line px-3 pt-3">
            <div>
              <p className="text-[0.875rem] font-medium text-k-ink">{user?.full_name}</p>
              <p className="text-[0.75rem] text-k-muted">{formatPhone(user?.phone)}</p>
            </div>
            <Button variant="ghost" size="sm" onClick={logout} icon={<LogOut className="size-4" aria-hidden />}>
              Quitter
            </Button>
          </div>
        </nav>
      ) : null}

      {/* Colonne latérale desktop */}
      <aside className="hidden w-72 shrink-0 flex-col bg-k-blue p-4 lg:flex">
        <Link to="/" className="px-2 py-3" aria-label="KEMTA — accueil">
          <BrandWordmark />
        </Link>

        <nav aria-label="Navigation de l'espace" className="mt-6 flex-1 space-y-1.5">
          {items.map((item) => navLink(item))}
        </nav>

        <div className="mt-6 rounded-k-lg bg-white/10 p-4">
          <div className="flex items-center gap-3">
            <span
              className="flex size-10 shrink-0 items-center justify-center rounded-full bg-white/15 font-display text-[0.8125rem] font-semibold text-white"
              aria-hidden
            >
              {initials(user?.full_name)}
            </span>
            <div className="min-w-0">
              <p className="truncate text-[0.875rem] font-medium text-white">{user?.full_name}</p>
              <p className="truncate text-[0.75rem] text-white/70">{formatPhone(user?.phone)}</p>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap gap-1.5">
            {user?.role ? <Badge tone="outline">{user.role}</Badge> : null}
            {!online ? <Badge tone="amber">Hors ligne</Badge> : null}
          </div>

          <div className="mt-4 space-y-1.5 border-t border-white/15 pt-3">
            <Link
              to="/contact"
              className="flex items-center gap-2 text-[0.8125rem] text-white/80 transition-colors hover:text-white"
            >
              <Settings className="size-3.5" aria-hidden />
              Aide & contact
            </Link>
            <button
              type="button"
              onClick={logout}
              className="flex items-center gap-2 text-[0.8125rem] text-white/80 transition-colors hover:text-white"
            >
              <LogOut className="size-3.5" aria-hidden />
              Se déconnecter
            </button>
          </div>
        </div>
      </aside>

      <main className="min-w-0 flex-1">
        <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
