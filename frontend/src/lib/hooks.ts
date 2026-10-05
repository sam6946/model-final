import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { http, type Paginated } from '@/lib/api';
import { qk } from '@/lib/query';
import { useAuth } from '@/hooks/useAuth';
import type {
  CompanyCard,
  DashboardPayload,
  LocationsPayload,
  Opportunity,
  Plan,
  ProjectCard,
  ProjectDetail,
  ProjectPhase,
  ProjectUpdate,
  Property,
  PublicContent,
  RealizationCard,
  ServiceCatalogItem,
  ServiceRequest,
  SpecialtiesPayload,
  Specialty,
} from '@/lib/types';

/* ------------------------------------------------------------ contenus publics */

export function usePublicContent(): UseQueryResult<PublicContent> {
  return useQuery({
    queryKey: qk.publicContent(),
    queryFn: () => http.get<PublicContent>('/catalog/public-content/'),
    staleTime: 30 * 60_000,
  });
}

export function useLocations(country = 'CM'): UseQueryResult<LocationsPayload> {
  return useQuery({
    queryKey: [...qk.locations(), country],
    queryFn: () => http.get<LocationsPayload>('/catalog/locations/', { params: { country } }),
    staleTime: 60 * 60_000,
  });
}

export function useSpecialties(): UseQueryResult<SpecialtiesPayload> {
  return useQuery({
    queryKey: qk.specialties(),
    queryFn: () => http.get<SpecialtiesPayload>('/catalog/specialties/'),
    staleTime: 60 * 60_000,
  });
}

export function useServiceCatalog(): UseQueryResult<Paginated<ServiceCatalogItem> | ServiceCatalogItem[]> {
  return useQuery({
    queryKey: qk.serviceCatalog(),
    queryFn: () => http.get<Paginated<ServiceCatalogItem> | ServiceCatalogItem[]>('/services/'),
    staleTime: 30 * 60_000,
  });
}

/** Les tarifs viennent toujours du backend : jamais de prix figé dans le front. */
export function usePlans(): UseQueryResult<Plan[]> {
  return useQuery({
    queryKey: qk.plans(),
    queryFn: async () => {
      const data = await http.get<{ results: Plan[] }>('/plans/');
      return data.results ?? [];
    },
    staleTime: 15 * 60_000,
  });
}

/* ------------------------------------------------------------------ écosystème */

export function useCompanies(params: Record<string, unknown> = {}): UseQueryResult<Paginated<CompanyCard>> {
  return useQuery({
    queryKey: qk.companies(params),
    queryFn: () => http.get<Paginated<CompanyCard>>('/companies/', { params }),
    staleTime: 5 * 60_000,
  });
}

export function useRealizations(params: Record<string, unknown> = {}): UseQueryResult<Paginated<RealizationCard>> {
  return useQuery({
    queryKey: qk.realizations(params),
    queryFn: () => http.get<Paginated<RealizationCard>>('/catalog/realizations/', { params }),
    staleTime: 5 * 60_000,
  });
}

export type RealizationFiltersPayload = {
  types: Array<{ value: string; label: string; count: number }>;
  specialties: Specialty[];
};

/** Facettes du catalogue : libellés et volumes calculés côté backend. */
export function useRealizationFilters(): UseQueryResult<RealizationFiltersPayload> {
  return useQuery({
    queryKey: qk.realizationFilters(),
    queryFn: () => http.get<RealizationFiltersPayload>('/catalog/realizations/filters/'),
    staleTime: 30 * 60_000,
  });
}

export function useOpportunities(params: Record<string, unknown> = {}): UseQueryResult<Paginated<Opportunity>> {
  return useQuery({
    queryKey: qk.opportunities(params),
    queryFn: () => http.get<Paginated<Opportunity>>('/opportunities/', { params }),
    staleTime: 2 * 60_000,
  });
}

/* ------------------------------------------------------------------ espace client */

export function useDashboard(space: 'CLIENT' | 'COMPANY' | 'ADMIN' = 'CLIENT') {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: qk.dashboard(space),
    enabled: isAuthenticated,
    queryFn: () => http.get<DashboardPayload>('/dashboard/', { params: { space } }),
    staleTime: 60_000,
  });
}

export function useMyProjects(params: Record<string, unknown> = {}) {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: qk.myProjects(params),
    enabled: isAuthenticated,
    queryFn: () =>
      http.get<Paginated<ProjectCard> & { summary?: Record<string, number | string> }>('/projects/mine/', {
        params,
      }),
    staleTime: 60_000,
  });
}

export function useProject(id: number | string | undefined) {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: qk.project(id ?? ''),
    enabled: isAuthenticated && Boolean(id),
    queryFn: () => http.get<ProjectDetail>(`/projects/${id}/`),
  });
}

export function useProjectPhases(id: number | string | undefined) {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: qk.projectPhases(id ?? ''),
    enabled: isAuthenticated && Boolean(id),
    queryFn: async () => {
      const data = await http.get<Paginated<ProjectPhase> | ProjectPhase[]>(`/projects/${id}/phases/`);
      return Array.isArray(data) ? data : data.results;
    },
  });
}

export function useProjectTimeline(id: number | string | undefined) {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: qk.projectTimeline(id ?? ''),
    enabled: isAuthenticated && Boolean(id),
    queryFn: async () => {
      const data = await http.get<Paginated<ProjectUpdate> | ProjectUpdate[]>(`/projects/${id}/timeline/`);
      return Array.isArray(data) ? data : data.results;
    },
  });
}

export function useMyProperties(): UseQueryResult<Paginated<Property>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: qk.myProperties(),
    enabled: isAuthenticated,
    queryFn: () => http.get<Paginated<Property>>('/properties/'),
    staleTime: 60_000,
  });
}

export function useMyRequests(): UseQueryResult<Paginated<ServiceRequest>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: qk.myRequests(),
    enabled: isAuthenticated,
    queryFn: () => http.get<Paginated<ServiceRequest>>('/requests/mine/'),
    staleTime: 60_000,
  });
}
