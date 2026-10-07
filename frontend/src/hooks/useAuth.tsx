import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';

import { ApiError, http, tokens } from '@/lib/api';
import { qk } from '@/lib/query';

export type SessionUser = {
  id: number;
  phone: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email: string;
  role: 'CUSTOMER' | 'COMPANY' | 'FIELD' | 'MANAGER' | 'ADMIN';
  city: string;
  country: string;
  avatar_url?: string | null;
  initials?: string;
};

export type SpaceLink = {
  key: 'customer' | 'company' | 'admin' | string;
  label: string;
  url?: string;
  available: boolean;
  company_name?: string;
};

export type MePayload = {
  user: SessionUser;
  permissions: string[];
  phone_verified: boolean;
  spaces: SpaceLink[];
};

/**
 * Etat réel de la session, pour ne jamais afficher « Connexion requise » à
 * quelqu'un dont la session existe mais dont le profil n'a pas pu être chargé.
 */
export type SessionState =
  | 'anonymous'      // aucun jeton : il faut se connecter
  | 'loading'        // jeton présent, profil en cours de chargement
  | 'authenticated'
  | 'expired'        // jeton refusé par le serveur
  | 'unreachable';   // KEMTA injoignable (réseau ou service arrêté)

type AuthContextValue = {
  user: SessionUser | null;
  permissions: string[];
  spaces: SpaceLink[];
  phoneVerified: boolean;
  loading: boolean;
  isAuthenticated: boolean;
  sessionState: SessionState;
  hasPermission: (code: string) => boolean;
  signIn: (payload: { access: string; refresh: string }) => void;
  signOut: (options?: { silent?: boolean }) => Promise<void>;
  refreshProfile: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [hasSession, setHasSession] = useState(() => tokens.hasSession());
  // Vrai lorsqu'une session existante vient d'être close par le serveur :
  // l'écran peut alors expliquer la reconnexion au lieu d'un « connexion
  // requise » identique à celui d'un simple visiteur.
  const [justExpired, setJustExpired] = useState(false);

  const { data, error, isLoading, refetch } = useQuery<MePayload, ApiError>({
    queryKey: qk.me(),
    enabled: hasSession,
    queryFn: () => http.get<MePayload>('/auth/me/'),
    staleTime: 5 * 60_000,
    retry: false,
  });

  // Un jeton refusé (expiré, révoqué, signé par un autre environnement) ne doit
  // pas laisser l'application dans un état intermédiaire : on repart proprement
  // déconnecté, ce qui évite de rester bloqué sur un écran d'accès protégé.
  const sessionRefused = Boolean(error) && error?.status === 401;

  useEffect(() => {
    if (sessionRefused && hasSession) {
      tokens.clear();
      setHasSession(false);
      setJustExpired(true);
    }
  }, [sessionRefused, hasSession]);

  const signOut = useCallback(
    async (options?: { silent?: boolean }) => {
      const refresh = tokens.refresh();
      if (refresh && !options?.silent) {
        try {
          await http.post('/auth/logout/', { refresh });
        } catch {
          // Une session déjà révoquée côté serveur ne doit pas bloquer la sortie.
        }
      }
      tokens.clear();
      setHasSession(false);
      queryClient.clear();
    },
    [queryClient],
  );

  const signIn = useCallback((payload: { access: string; refresh: string }) => {
    tokens.set(payload.access, payload.refresh);
    setHasSession(true);
    setJustExpired(false);
  }, []);

  useEffect(() => {
    const onExpired = () => {
      setJustExpired(true);
      void signOut({ silent: true });
    };
    window.addEventListener('kemta:session-expired', onExpired);
    return () => window.removeEventListener('kemta:session-expired', onExpired);
  }, [signOut]);

  const sessionState: SessionState = (() => {
    if (data?.user) return 'authenticated';
    if (hasSession && isLoading) return 'loading';
    // Un jeton présent mais un service injoignable : la session n'est pas en
    // cause, inutile de renvoyer la personne vers la page de connexion.
    if (hasSession && error?.code === 'network_error') return 'unreachable';
    if (hasSession) return 'expired';
    return justExpired ? 'expired' : 'anonymous';
  })();

  const value = useMemo<AuthContextValue>(
    () => ({
      user: data?.user ?? null,
      permissions: data?.permissions ?? [],
      spaces: data?.spaces ?? [],
      phoneVerified: data?.phone_verified ?? false,
      loading: hasSession && isLoading,
      isAuthenticated: Boolean(data?.user),
      sessionState,
      hasPermission: (code: string) => (data?.permissions ?? []).includes(code),
      signIn,
      signOut,
      refreshProfile: async () => {
        // `throwOnError` : une panne de chargement du profil doit remonter à
        // l'écran de connexion, jamais se traduire par une redirection muette.
        await refetch({ throwOnError: true });
      },
    }),
    [data, error, hasSession, isLoading, sessionState, refetch, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth doit être utilisé dans <AuthProvider>.');
  return context;
}
