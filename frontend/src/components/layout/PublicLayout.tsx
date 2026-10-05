import { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';

import { Footer } from './Footer';
import { Navbar } from './Navbar';
import { OfflineBanner } from '@/components/ui/Feedback';
import { useOnlineStatus } from '@/hooks/useReveal';

/** Remet la page en haut lors d'un changement de route (comportement attendu sur mobile). */
function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior });
  }, [pathname]);
  return null;
}

export function PublicLayout() {
  const online = useOnlineStatus();

  return (
    <div className="flex min-h-screen flex-col">
      <ScrollToTop />
      {!online ? <OfflineBanner /> : null}
      <Navbar />
      <main id="contenu" className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
