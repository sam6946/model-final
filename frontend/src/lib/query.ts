import { QueryClient } from '@tanstack/react-query';

/**
 * Cache applicatif.
 *
 * Les données publiques (contenus éditoriaux, catalogue, entreprises) restent
 * fraîches longtemps ; les données de suivi (projets, preuves, dashboards) sont
 * rafraîchies à la demande de l'utilisateur. On évite les rafraîchissements
 * automatiques au retour de fenêtre pour ne pas surcharger les forfaits mobiles.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      gcTime: 15 * 60_000,
      retry: (failureCount, error) => {
        const status = (error as { status?: number })?.status ?? 0;
        if (status === 401 || status === 403 || status === 404 || status === 422) return false;
        return failureCount < 2;
      },
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 6000),
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
    },
    mutations: { retry: 0 },
  },
});

/** Clés de cache centralisées : une seule source de vérité par ressource. */
export const qk = {
  me: () => ['auth', 'me'] as const,
  publicContent: () => ['catalog', 'public-content'] as const,
  locations: () => ['catalog', 'locations'] as const,
  specialties: () => ['catalog', 'specialties'] as const,
  serviceCatalog: () => ['catalog', 'services'] as const,
  plans: () => ['plans'] as const,
  companies: (params: Record<string, unknown>) => ['companies', params] as const,
  company: (slug: string) => ['companies', slug] as const,
  realizations: (params: Record<string, unknown>) => ['realizations', params] as const,
  realizationFilters: () => ['realizations', 'filters'] as const,
  opportunities: (params: Record<string, unknown>) => ['opportunities', params] as const,
  opportunity: (slug: string) => ['opportunities', slug] as const,
  dashboard: (space: string) => ['dashboard', space] as const,
  myProjects: (params: Record<string, unknown>) => ['projects', 'mine', params] as const,
  project: (id: number | string) => ['projects', String(id)] as const,
  projectPhases: (id: number | string) => ['projects', String(id), 'phases'] as const,
  projectTimeline: (id: number | string) => ['projects', String(id), 'timeline'] as const,
  projectBudget: (id: number | string) => ['projects', String(id), 'budget'] as const,
  myProperties: () => ['properties', 'mine'] as const,
  myRequests: () => ['requests', 'mine'] as const,
  myCompany: () => ['company', 'mine'] as const,
  companyDocuments: () => ['company', 'documents'] as const,
  companyRealizations: () => ['company', 'realizations'] as const,
  applications: () => ['applications', 'mine'] as const,
  notifications: () => ['notifications'] as const,
  subscription: () => ['subscriptions', 'mine'] as const,
  invoices: () => ['invoices'] as const,
  adminCompanies: () => ['admin', 'companies'] as const,
  adminApplications: () => ['admin', 'applications'] as const,
  myApplication: (id: number | string) => ['applications', 'mine', String(id)] as const,
};
