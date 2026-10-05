import { Loader2 } from 'lucide-react';

import { BrandMark } from './layout/Brand';

/** Écran affiché pendant le chargement d'un morceau de page (réseau lent). */
export function RouteFallback() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 bg-white">
      <BrandMark className="size-10 animate-pulse" />
      <p className="inline-flex items-center gap-2 text-[0.875rem] text-k-muted" role="status">
        <Loader2 className="size-4 animate-spin" aria-hidden />
        Chargement de la page…
      </p>
    </div>
  );
}
