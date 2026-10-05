import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios';

/**
 * Client HTTP unique de l'application.
 *
 * Principes :
 * - toutes les requêtes passent par `/api/v1` (même origine en dev comme en prod,
 *   le proxy Vite puis Nginx s'occupent du reste : aucun CORS côté navigateur) ;
 * - le jeton d'accès vit en mémoire et dans le stockage local, le jeton de
 *   rafraîchissement est renouvelé une seule fois même si dix requêtes échouent
 *   en parallèle (promesse partagée) ;
 * - chaque erreur est normalisée en français, prête à être affichée à l'écran.
 */

const ACCESS_KEY = 'kemta.access';
const REFRESH_KEY = 'kemta.refresh';

export type ApiErrorShape = {
  code: string;
  message: string;
  fields: Record<string, string[]>;
  traceId?: string;
  status: number;
};

export class ApiError extends Error implements ApiErrorShape {
  code: string;
  fields: Record<string, string[]>;
  traceId?: string;
  status: number;

  constructor(shape: ApiErrorShape) {
    super(shape.message);
    this.name = 'ApiError';
    this.code = shape.code;
    this.fields = shape.fields;
    this.traceId = shape.traceId;
    this.status = shape.status;
  }

  /** Message à afficher pour un champ de formulaire donné. */
  fieldError(field: string): string | undefined {
    return this.fields[field]?.[0];
  }
}

export const tokens = {
  access: () => localStorage.getItem(ACCESS_KEY),
  refresh: () => localStorage.getItem(REFRESH_KEY),
  set(access: string, refresh?: string) {
    localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
  hasSession: () => Boolean(localStorage.getItem(ACCESS_KEY) || localStorage.getItem(REFRESH_KEY)),
};

export const api: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 20000,
  headers: { Accept: 'application/json' },
});

api.interceptors.request.use((config) => {
  const access = tokens.access();
  if (access) config.headers.Authorization = `Bearer ${access}`;
  return config;
});

let refreshInFlight: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = tokens.refresh();
  if (!refresh) return null;
  try {
    const { data } = await axios.post('/api/v1/auth/token/refresh/', { refresh }, { timeout: 15000 });
    const access = data?.access as string | undefined;
    if (!access) return null;
    tokens.set(access, data?.refresh);
    return access;
  } catch {
    tokens.clear();
    return null;
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const status = error.response?.status ?? 0;
    const original = error.config as AxiosRequestConfig & { _retried?: boolean };

    if (status === 401 && original && !original._retried && !original.url?.includes('/auth/')) {
      original._retried = true;
      refreshInFlight = refreshInFlight ?? refreshAccessToken();
      const access = await refreshInFlight;
      refreshInFlight = null;
      if (access) {
        original.headers = { ...(original.headers ?? {}), Authorization: `Bearer ${access}` };
        return api.request(original);
      }
      window.dispatchEvent(new CustomEvent('kemta:session-expired'));
    }

    throw normalizeError(error);
  },
);

/** Transforme n'importe quelle panne en message français exploitable. */
export function normalizeError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;

  if (axios.isAxiosError(error)) {
    const payload = error.response?.data as
      | { error?: { code?: string; message?: string; fields?: Record<string, string[]>; trace_id?: string } }
      | undefined;
    const status = error.response?.status ?? 0;
    const body = payload?.error;

    if (!error.response) {
      return new ApiError({
        code: 'network_error',
        message:
          "Impossible de joindre KEMTA. Vérifiez votre connexion internet puis réessayez : vos informations saisies sont conservées.",
        fields: {},
        status: 0,
      });
    }
    return new ApiError({
      code: body?.code ?? 'error',
      message: body?.message ?? 'Une erreur est survenue. Réessayez dans un instant.',
      fields: body?.fields ?? {},
      traceId: body?.trace_id,
      status,
    });
  }

  return new ApiError({
    code: 'unknown',
    message: 'Une erreur inattendue est survenue. Réessayez dans un instant.',
    fields: {},
    status: 0,
  });
}

/* --------------------------------------------------------------- raccourcis */
export const http = {
  get: async <T>(url: string, config?: AxiosRequestConfig) => (await api.get<T>(url, config)).data,
  post: async <T>(url: string, body?: unknown, config?: AxiosRequestConfig) =>
    (await api.post<T>(url, body, config)).data,
  patch: async <T>(url: string, body?: unknown, config?: AxiosRequestConfig) =>
    (await api.patch<T>(url, body, config)).data,
  put: async <T>(url: string, body?: unknown, config?: AxiosRequestConfig) =>
    (await api.put<T>(url, body, config)).data,
  delete: async <T>(url: string, config?: AxiosRequestConfig) => (await api.delete<T>(url, config)).data,
};

export type Paginated<T> = {
  count: number;
  pages: number;
  page: number;
  page_size: number;
  next: string | null;
  previous: string | null;
  results: T[];
};
