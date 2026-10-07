import type { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Lock, RefreshCw, ShieldAlert, WifiOff } from 'lucide-react';

import { useAuth } from '@/hooks/useAuth';
import { RouteFallback } from './RouteFallback';
import { Button, ButtonLink } from '@/components/ui/Button';

/**
 * Garde d'accès côté interface.
 *
 * Elle n'est jamais la seule protection : chaque endpoint vérifie lui-même les
 * droits (RBAC + propriété de la ressource). Ce composant sert uniquement à
 * éviter d'afficher un écran vide ou une erreur brute à l'utilisateur.
 *
 * Trois situations distinctes sont présentées différemment, car elles
 * n'appellent pas la même action :
 *   · aucune session      → « Connexion requise » ;
 *   · session expirée     → « Session expirée », on se reconnecte ;
 *   · KEMTA injoignable   → « Service momentanément indisponible », on réessaie.
 * Sans cette distinction, une panne de réseau ressemble à une déconnexion et
 * l'utilisateur tourne en boucle entre la connexion et l'écran d'accès.
 */
export function ProtectedRoute({
  children,
  permission,
}: {
  children: ReactNode;
  permission?: string;
}) {
  const { isAuthenticated, loading, hasPermission, sessionState, refreshProfile } = useAuth();
  const location = useLocation();

  if (loading || sessionState === 'loading') return <RouteFallback />;

  if (!isAuthenticated && sessionState === 'unreachable') {
    return (
      <div className="k-container flex min-h-[70vh] flex-col items-center justify-center gap-4 py-16 text-center">
        <span className="flex size-12 items-center justify-center rounded-full bg-k-amber-pale text-k-amber" aria-hidden>
          <WifiOff className="size-5" />
        </span>
        <h1 className="text-2xl">Service momentanément injoignable</h1>
        <p className="k-lead mx-auto max-w-lg">
          Votre connexion internet est peut-être en cause, ou KEMTA effectue une maintenance. Votre session n&apos;a
          pas été perdue : réessayez dans quelques instants.
        </p>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button
            icon={<RefreshCw className="size-4" aria-hidden />}
            onClick={() => {
              void refreshProfile().catch(() => undefined);
            }}
          >
            Réessayer
          </Button>
          <ButtonLink to="/contact" variant="secondary">
            Contacter KEMTA
          </ButtonLink>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    const expired = sessionState === 'expired';
    return (
      <div className="k-container flex min-h-[70vh] flex-col items-center justify-center gap-4 py-16 text-center">
        <span className="flex size-12 items-center justify-center rounded-full bg-k-blue-soft text-k-blue" aria-hidden>
          <Lock className="size-5" />
        </span>
        <h1 className="text-2xl">{expired ? 'Session expirée' : 'Connexion requise'}</h1>
        <p className="k-lead mx-auto max-w-lg">
          {expired
            ? 'Votre session a pris fin pour des raisons de sécurité. Reconnectez-vous avec votre numéro de téléphone : vos projets et vos preuves sont intacts.'
            : 'Votre espace KEMTA est protégé. Connectez-vous avec votre numéro de téléphone pour suivre vos projets, vos propriétés et vos demandes.'}
        </p>
        <div className="flex flex-col gap-3 sm:flex-row">
          <ButtonLink to="/connexion" state={{ from: location.pathname }}>
            Se connecter
          </ButtonLink>
          <ButtonLink to="/inscription" variant="secondary">
            Créer un compte
          </ButtonLink>
        </div>
        <p className="text-[0.8125rem] text-k-muted">
          Pas encore de compte ? L&apos;inscription prend deux minutes et se fait par SMS.
        </p>
      </div>
    );
  }

  if (permission && !hasPermission(permission)) {
    return (
      <div className="k-container flex min-h-[70vh] flex-col items-center justify-center gap-4 py-16 text-center">
        <span className="flex size-12 items-center justify-center rounded-full bg-k-red-pale text-k-red" aria-hidden>
          <ShieldAlert className="size-5" />
        </span>
        <h1 className="text-2xl">Accès non autorisé</h1>
        <p className="k-lead mx-auto max-w-lg">
          Cette section est réservée à l&apos;équipe KEMTA. Si vous pensez qu&apos;il s&apos;agit d&apos;une erreur,
          contactez votre chargé de suivi.
        </p>
        <Link to="/espace" className="text-[0.875rem] font-medium text-k-blue hover:text-k-green-dark">
          Revenir à mon espace
        </Link>
      </div>
    );
  }

  return <>{children}</>;
}
