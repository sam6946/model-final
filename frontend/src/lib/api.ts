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

/**
 * Accès au stockage local, tolérant aux environnements restreints.
 *
 * Dans une iframe de prévisualisation, un onglet privé ou un navigateur qui
 * bloque le stockage, `localStorage` peut lever une exception. Une connexion
 * réussie ne doit jamais être perdue pour autant : on conserve alors la session
 * en mémoire, le temps de l'onglet.
 */
const memoryStore = new Map<string, string>();

function readKey(key: string): string | null {
  if (memoryStore.has(key)) return memoryStore.get(key) ?? null;
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeKey(key: string, value: string): void {
  memoryStore.set(key, value);
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* stockage indisponible : la session reste en mémoire */
  }
}

function removeKey(key: string): void {
  memoryStore.delete(key);
  try {
    window.localStorage.removeItem(key);
  } catch {
    /* rien à faire */
  }
}

export const tokens = {
  access: () => readKey(ACCESS_KEY),
  refresh: () => readKey(REFRESH_KEY),
  set(access: string, refresh?: string) {
    writeKey(ACCESS_KEY, access);
    if (refresh) writeKey(REFRESH_KEY, refresh);
  },
  clear() {
    removeKey(ACCESS_KEY);
    removeKey(REFRESH_KEY);
  },
  /**
   * Ferme la session uniquement si le jeton de rafraîchissement fourni est
   * toujours celui en cours.
   *
   * Un échec peut arriver tardivement (onglet laissé ouvert, réseau lent) :
   * à ce moment-là l'utilisateur s'est peut-être reconnecté et détruire sa
   * nouvelle session le renverrait sur un écran de connexion sans explication.
   */
  clearStale(expected: string | null): boolean {
    if ((readKey(REFRESH_KEY) ?? null) !== expected) return false;
    removeKey(ACCESS_KEY);
    removeKey(REFRESH_KEY);
    return true;
  },
  hasSession: () => Boolean(readKey(ACCESS_KEY) || readKey(REFRESH_KEY)),
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

let refreshInFlight: Promise<RefreshOutcome> | null = null;

type RefreshOutcome = { access: string } | { failure: 'rejected' | 'unreachable' };

async function refreshAccessToken(refresh: string): Promise<RefreshOutcome> {
  try {
    const { data } = await axios.post('/api/v1/auth/token/refresh/', { refresh }, { timeout: 15000 });
    const access = data?.access as string | undefined;
    if (!access) return { failure: 'rejected' };
    tokens.set(access, data?.refresh);
    return { access };
  } catch (error) {
    // Un refus franc (4xx) signifie que la session est morte ; une panne
    // réseau ne prouve rien et ne doit donc pas faire perdre la session.
    const status = axios.isAxiosError(error) ? error.response?.status ?? 0 : 0;
    return { failure: status >= 400 && status < 500 ? 'rejected' : 'unreachable' };
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const status = error.response?.status ?? 0;
    const original = error.config as AxiosRequestConfig & { _retried?: boolean };

    // Ces points d'entrée ne doivent jamais être rejoués après un rafraîchissement :
    // ce sont eux qui délivrent les jetons (un rejeu masquerait l'erreur réelle).
    const noRetry = [
      '/auth/login',
      '/auth/register',
      '/auth/otp',
      '/otp/',
      '/auth/token/refresh',
      '/auth/password',
      '/auth/phone',
    ];
    const rejouable = Boolean(original?.url) && !noRetry.some((fragment) => original.url!.includes(fragment));

    if (status === 401 && original && !original._retried && rejouable) {
      original._retried = true;
      const refreshToken = tokens.refresh();

      if (!refreshToken) {
        if (tokens.clearStale(null)) window.dispatchEvent(new CustomEvent('kemta:session-expired'));
        throw normalizeError(error);
      }

      refreshInFlight = refreshInFlight ?? refreshAccessToken(refreshToken);
      const outcome = await refreshInFlight;
      refreshInFlight = null;

      if ('access' in outcome) {
        original.headers = { ...(original.headers ?? {}), Authorization: `Bearer ${outcome.access}` };
        return api.request(original);
      }

      if (outcome.failure === 'unreachable') {
        // Le rafraîchissement n'a pas pu être vérifié : on n'efface rien et on
        // le dit clairement, plutôt que de faire croire à une déconnexion.
        throw new ApiError({
          code: 'network_error',
          message:
            "Impossible de joindre KEMTA pour vérifier votre session. Vérifiez votre connexion internet puis réessayez : vous n'avez pas été déconnecté.",
          fields: {},
          status: 0,
        });
      }

      if (tokens.clearStale(refreshToken)) window.dispatchEvent(new CustomEvent('kemta:session-expired'));
    }

    throw normalizeError(error);
  },
);

/**
 * Messages techniques → français.
 *
 * L'API répond toujours en français (middleware côté serveur), mais un message
 * brut peut arriver d'ailleurs : erreur de proxy, page d'administration Django,
 * réponse d'un service tiers. Aucun texte anglais ne doit atteindre l'écran.
 */
const FRENCH_ERROR_CODES: Record<number, { code: string; message: string }> = {
  401: {
    code: 'not_authenticated',
    message: "Votre session a expiré ou vous n'êtes pas connecté. Reconnectez-vous pour continuer.",
  },
  403: {
    code: 'forbidden',
    message: "Vous n'avez pas l'autorisation d'accéder à cette ressource.",
  },
  404: {
    code: 'not_found',
    message: "Cette ressource n'existe pas ou a été supprimée.",
  },
  405: {
    code: 'method_not_allowed',
    message: "Cette action n'est pas disponible sur cette adresse.",
  },
  415: {
    code: 'unsupported_media_type',
    message: "Le format des données envoyées n'est pas pris en charge.",
  },
  429: {
    code: 'rate_limited',
    message: 'Trop de tentatives en peu de temps. Merci de patienter quelques minutes avant de réessayer.',
  },
};

const TECHNICAL_MESSAGE = new RegExp(
  [
    'authentication credentials were not provided',
    'given token not valid',
    'token is invalid or expired',
    'you do not have permission',
    'not found\\.?$',
    'method .* not allowed',
    'request was throttled',
    'json parse error',
    'unsupported media type',
  ].join('|'),
  'i',
);

/** Vrai si le texte est un message technique, donc jamais affichable. */
function isTechnicalMessage(text: string | undefined): boolean {
  if (!text) return true;
  return TECHNICAL_MESSAGE.test(text.trim());
}

function frenchMessage(detail: string | undefined, status: number, code: string | undefined): string {
  const fallback = FRENCH_ERROR_CODES[status];
  if (isTechnicalMessage(detail)) {
    if (fallback) return fallback.message;
    if (code && FRENCH_ERROR_CODES_BY_CODE[code]) return FRENCH_ERROR_CODES_BY_CODE[code];
    return detail && !fallback ? detail : 'Une erreur est survenue. Réessayez dans un instant.';
  }
  return detail as string;
}

const FRENCH_ERROR_CODES_BY_CODE: Record<string, string> = {
  not_authenticated: FRENCH_ERROR_CODES[401].message,
  authentication_failed: FRENCH_ERROR_CODES[401].message,
  token_not_valid: FRENCH_ERROR_CODES[401].message,
  permission_denied: FRENCH_ERROR_CODES[403].message,
  forbidden: FRENCH_ERROR_CODES[403].message,
  not_found: FRENCH_ERROR_CODES[404].message,
  method_not_allowed: FRENCH_ERROR_CODES[405].message,
  rate_limited: FRENCH_ERROR_CODES[429].message,
  throttled: FRENCH_ERROR_CODES[429].message,
};

/** Transforme n'importe quelle panne en message français exploitable. */
export function normalizeError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;

  if (axios.isAxiosError(error)) {
    const payload = error.response?.data as
      | {
          error?: { code?: string; message?: string; fields?: Record<string, string[]>; trace_id?: string };
          detail?: unknown;
          code?: unknown;
        }
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
    if (status >= 500) {
      // Panne serveur (ou service arrêté derrière le proxy) : message explicite
      // plutôt qu'un « une erreur est survenue » qui laisse croire à une faute
      // de saisie.
      return new ApiError({
        code: body?.code ?? 'server_error',
        message:
          body?.message ??
          "KEMTA est momentanément indisponible (incident technique). Vos informations sont conservées : réessayez dans un instant.",
        fields: body?.fields ?? {},
        traceId: body?.trace_id,
        status,
      });
    }

    // Filet de sécurité : certains cas (proxy, page d'administration, réponse
    // brute de Django REST Framework) n'ont pas l'enveloppe KEMTA. On ne laisse
    // jamais passer un message technique anglais dans une interface française.
    const rawCode = body?.code ?? (typeof payload?.code === 'string' ? payload.code : undefined);
    const rawDetail =
      body?.message ??
      (typeof payload?.detail === 'string' ? payload.detail : Array.isArray(payload?.detail) ? String(payload.detail[0]) : undefined);

    return new ApiError({
      code: rawCode ?? FRENCH_ERROR_CODES[status]?.code ?? 'error',
      message: frenchMessage(rawDetail, status, rawCode),
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
