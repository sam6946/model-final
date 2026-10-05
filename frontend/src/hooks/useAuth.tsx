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

type AuthContextValue = {
  user: SessionUser | null;
  permissions: string[];
  spaces: SpaceLink[];
  phoneVerified: boolean;
  loading: boolean;
  isAuthenticated: boolean;
  hasPermission: (code: string) => boolean;
  signIn: (payload: { access: string; refresh: string }) => void;
  signOut: (options?: { silent?: boolean }) => Promise<void>;
  refreshProfile: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [hasSession, setHasSession] = useState(() => tokens.hasSession());

  const { data, isLoading, refetch } = useQuery<MePayload, ApiError>({
    queryKey: qk.me(),
    enabled: hasSession,
    queryFn: () => http.get<MePayload>('/auth/me/'),
    staleTime: 5 * 60_000,
    retry: false,
  });

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
  }, []);

  useEffect(() => {
    const onExpired = () => {
      void signOut({ silent: true });
    };
    window.addEventListener('kemta:session-expired', onExpired);
    return () => window.removeEventListener('kemta:session-expired', onExpired);
  }, [signOut]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user: data?.user ?? null,
      permissions: data?.permissions ?? [],
      spaces: data?.spaces ?? [],
      phoneVerified: data?.phone_verified ?? false,
      loading: hasSession && isLoading,
      isAuthenticated: Boolean(data?.user),
      hasPermission: (code: string) => (data?.permissions ?? []).includes(code),
      signIn,
      signOut,
      refreshProfile: async () => {
        await refetch();
      },
    }),
    [data, hasSession, isLoading, refetch, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth doit être utilisé dans <AuthProvider>.');
  return context;
}
