import { useEffect, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import clsx from 'clsx';
import { LayoutDashboard, Menu, Phone, X } from 'lucide-react';

import { BrandWordmark } from './Brand';
import { Button, ButtonLink } from '@/components/ui/Button';
import { useAuth } from '@/hooks/useAuth';

const PUBLIC_LINKS = [
  { to: '/services/suivi-chantier', label: 'Suivi de chantier' },
  { to: '/services/entretien-propriete', label: 'Entretien' },
  { to: '/entreprises-btp', label: 'Entreprises BTP' },
  { to: '/realisations', label: 'Réalisations' },
  { to: '/opportunites', label: 'Opportunités' },
  { to: '/comment-ca-marche', label: 'Comment ça marche' },
];

export function Navbar() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { isAuthenticated, user } = useAuth();
  const location = useLocation();

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header
      className={clsx(
        'sticky top-0 z-50 border-b bg-white/95 backdrop-blur-sm transition-shadow duration-300',
        scrolled ? 'border-k-line shadow-k-sm' : 'border-transparent',
      )}
    >
      <a
        href="#contenu"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:z-50 focus:rounded-k focus:bg-k-blue focus:px-4 focus:py-2 focus:text-sm focus:text-white"
      >
        Aller au contenu principal
      </a>

      <div className="k-container flex h-16 items-center justify-between gap-6 lg:h-18">
        <Link to="/" aria-label="KEMTA — accueil" className="shrink-0">
          <BrandWordmark />
        </Link>

        <nav aria-label="Navigation principale" className="hidden items-center gap-7 lg:flex">
          {PUBLIC_LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                clsx(
                  'k-underline text-[0.875rem] font-medium transition-colors',
                  isActive ? 'text-k-blue' : 'text-k-ink/80 hover:text-k-blue',
                )
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="hidden items-center gap-3 lg:flex">
          <a
            href="tel:+237600000000"
            className="inline-flex items-center gap-1.5 text-[0.8125rem] font-medium text-k-muted transition-colors hover:text-k-blue"
          >
            <Phone className="size-3.5" aria-hidden />
            +237 600 000 000
          </a>
          {isAuthenticated ? (
            <ButtonLink
              to="/espace"
              variant="secondary"
              size="sm"
              icon={<LayoutDashboard className="size-3.5" aria-hidden />}
            >
              {user?.first_name ? `Bonjour ${user.first_name}` : 'Mon espace'}
            </ButtonLink>
          ) : (
            <ButtonLink to="/connexion" variant="secondary" size="sm">
              Espace client
            </ButtonLink>
          )}
          <ButtonLink to="/demande" size="sm">
            Démarrer une demande
          </ButtonLink>
        </div>

        <Button
          variant="ghost"
          size="sm"
          className="lg:hidden"
          aria-expanded={open}
          aria-controls="menu-mobile"
          aria-label={open ? 'Fermer le menu' : 'Ouvrir le menu'}
          onClick={() => setOpen((value) => !value)}
          icon={open ? <X className="size-5" aria-hidden /> : <Menu className="size-5" aria-hidden />}
        />
      </div>

      {open ? (
        <div id="menu-mobile" className="border-t border-k-line bg-white lg:hidden">
          <nav aria-label="Navigation mobile" className="k-container flex flex-col py-3">
            {PUBLIC_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  clsx(
                    'border-b border-k-line/70 py-3.5 text-[0.9375rem] font-medium',
                    isActive ? 'text-k-green-dark' : 'text-k-ink',
                  )
                }
              >
                {link.label}
              </NavLink>
            ))}
            <div className="flex flex-col gap-2.5 pt-4">
              <ButtonLink to="/demande" block>
                Démarrer une demande
              </ButtonLink>
              <ButtonLink to={isAuthenticated ? '/espace' : '/connexion'} variant="secondary" block>
                {isAuthenticated ? 'Mon espace' : 'Espace client'}
              </ButtonLink>
              <a
                href="tel:+237600000000"
                className="pt-1 text-center text-[0.8125rem] text-k-muted"
              >
                Appeler KEMTA : +237 600 000 000
              </a>
            </div>
          </nav>
        </div>
      ) : null}
    </header>
  );
}
