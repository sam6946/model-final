/** Types des ressources exposées par l'API KEMTA (miroir des sérialiseurs). */

export type TrustStat = {
  id: number;
  label: string;
  value: string;
  hint: string;
  icon: string;
};

export type Testimonial = {
  id: number;
  author_name: string;
  author_role: string;
  author_city: string;
  author_country: string;
  quote: string;
  rating: number;
  photo_url: string;
  project_name: string;
};

export type FaqItem = {
  id: number;
  category: string;
  question: string;
  answer: string;
  order: number;
};

export type PublicContent = {
  faq: Record<string, FaqItem[]>;
  testimonials: Testimonial[];
  trust_stats: TrustStat[];
};

export type Location = {
  id: number;
  name: string;
  slug: string;
  region: string;
  country: string;
  kind: string;
  label: string;
  latitude: number | null;
  longitude: number | null;
};

export type LocationsPayload = {
  count: number;
  cities: Location[];
  neighbourhoods?: Location[];
  diaspora?: Location[];
};

export type Specialty = {
  id: number;
  code: string;
  name: string;
  category?: string;
  description?: string;
  icon?: string;
  companies_count?: number;
};

export type SpecialtiesPayload = {
  results: Specialty[];
  grouped?: Record<string, Specialty[]>;
};

export type ServiceCatalogItem = {
  id: number;
  code: string;
  name: string;
  tagline: string;
  description: string;
  icon: string;
  duration_days: number;
  base_price_xaf: string | null;
  price_label?: string;
  requires_site_visit: boolean;
  deliverables: string[];
};

export type Plan = {
  id: number;
  code: 'FREE' | 'PRO' | 'PREMIUM' | string;
  name: string;
  tagline: string;
  description: string;
  price_xaf: number;
  price_label: string;
  currency: string;
  interval: string;
  trial_days: number;
  features: string[];
  limits?: Record<string, number | null>;
  is_recommended?: boolean;
};

export type SpecialtyRef = {
  id?: number;
  code: string;
  name: string;
  category?: string;
  icon?: string;
};

export type CompanyCard = {
  id: number;
  name: string;
  slug: string;
  city: string;
  region: string;
  specialities: SpecialtyRef[];
  years_experience: number;
  projects_count: number;
  employees_count: number;
  logo_url: string | null;
  cover_url: string | null;
  rating: number;
  rating_count: number;
  is_verified: boolean;
  is_featured: boolean;
  realizations_count: number;
  description: string;
  intervention_label: string;
};

export type CompanyRealizationItem = {
  id: number;
  title: string;
  slug: string;
  type: string;
  type_label: string;
  location: string;
  year: number;
  surface_m2: number | null;
  cover_url: string | null;
  budget_display: string;
  services: string[];
};

export type CompanyReview = {
  id: number;
  author: string;
  author_city: string;
  rating: number;
  comment: string;
  work_quality: number | null;
  deadline_respect: number | null;
  communication: number | null;
  created_at: string;
  response: string;
};

export type CompanyDetail = CompanyCard & {
  legal_name: string;
  address: string;
  website: string;
  equipment_summary: string;
  verification_status: string;
  verified_at: string | null;
  documents_verified: number;
  reviews: CompanyReview[];
  completed_projects_count: number;
  intervention_radius_km: number | null;
  contact: { phone: string; email: string; city: string; website?: string; preferred_channel: string };
  realizations: CompanyRealizationItem[];
};

export type RealizationCard = {
  id: number;
  title: string;
  slug: string;
  realization_type: string;
  type_label: string;
  company_name: string;
  company_slug: string;
  company_verified: boolean;
  display_location: string;
  year: number;
  surface_m2: string | null;
  duration_days: number | null;
  cover_url: string | null;
  services: string[];
  budget_display: string;
  is_featured: boolean;
};

export type Opportunity = {
  id: number;
  reference: string;
  title: string;
  slug: string;
  description: string;
  property_type: string;
  property_type_label: string;
  display_location: string;
  country: string;
  budget_min_xaf: string | null;
  budget_max_xaf: string | null;
  budget_label: string;
  budget_visible: boolean;
  start_date: string | null;
  duration_days: number | null;
  application_deadline: string | null;
  minimum_experience_years: number;
  requires_verified_company: boolean;
  status: string;
  status_label: string;
  is_featured: boolean;
  is_open: boolean;
  days_left: number | null;
  specialties: SpecialtyRef[];
  applications_count: number;
  views_count?: number;
  eligibility_reason?: string | null;
  published_at: string | null;
  created_at: string;
  eligible_for_me?: boolean | null;
  already_applied?: boolean;
};

export type NotificationItem = {
  id: number;
  notification_type?: string;
  type?: string;
  type_label?: string;
  level?: string;
  title: string;
  body: string;
  url?: string;
  action_url?: string;
  action_label?: string;
  is_read: boolean;
  age_label?: string;
  created_at: string;
};

export type SpaceLink = {
  key: string;
  label: string;
  url?: string;
  available: boolean;
  company_name?: string;
};

export type ActivityItem = {
  id: number;
  verb?: string;
  verb_label?: string;
  message: string;
  actor_name?: string;
  actor_initials?: string;
  project_reference?: string;
  is_important?: boolean;
  created_at: string;
};

export type NextActionItem = {
  key: string;
  label: string;
  url: string;
  kind?: string;
  priority?: number;
  done?: boolean;
};

export type ProjectCard = {
  id: number;
  reference: string;
  name: string;
  slug: string;
  kind: string;
  kind_label: string;
  status: string;
  status_label: string;
  health: string;
  health_label: string;
  display_location: string;
  cover_url: string;
  manager_name: string;
  company_name: string;
  progress_percent: number;
  budget_used_percent: number;
  budget_label: string;
  planned_start: string | null;
  planned_end: string | null;
  is_late: boolean;
  updated_at: string;
  created_at: string;
};

export type ProjectManager = { id: number; name: string; phone: string; initials: string };

export type ProjectMetrics = {
  physical_progress: number;
  budget_total_xaf: number;
  budget_spent_xaf: number;
  budget_used_percent: number;
  budget_remaining_xaf: number;
  is_over_budget: boolean;
  is_late: boolean;
  health: string;
  health_label: string;
  days_to_deadline: number | null;
  phases_count: number;
  phases_done: number;
  phases_blocked: number;
  tasks_open: number;
  tasks_overdue: number;
  evidences_count: number;
  evidences_pending: number;
};

export type ProjectDetail = {
  id: number;
  reference: string;
  name: string;
  slug: string;
  kind: string;
  kind_label: string;
  status: string;
  status_label: string;
  health: string;
  health_label: string;
  health_notes: string;
  description: string;
  cover_url: string;
  customer_name: string;
  request_reference: string;
  manager: ProjectManager | null;
  company: { id: number; name: string; slug: string; verified: boolean } | null;
  location_text: string;
  display_location: string;
  address: string;
  country: string;
  latitude: number | null;
  longitude: number | null;
  physical_progress: string | number;
  budget_total_xaf: string;
  budget_spent_xaf: string;
  budget_total_label: string;
  budget_spent_label: string;
  budget_remaining_label: string;
  budget_used_percent: number;
  is_over_budget: boolean;
  is_late: boolean;
  currency: string;
  contract_signed: boolean;
  planned_start: string | null;
  planned_end: string | null;
  actual_start: string | null;
  actual_end: string | null;
  next_visit_at: string | null;
  customer_can_comment: boolean;
  metrics: ProjectMetrics;
  phases: ProjectPhase[];
  created_at: string;
  updated_at: string;
};

export type ProjectPhase = {
  id: number;
  name: string;
  description: string;
  order: number;
  weight_percent: string | number;
  status: string;
  status_label: string;
  progress_percent: string | number;
  planned_start: string | null;
  planned_end: string | null;
  actual_start: string | null;
  actual_end: string | null;
  budget_planned_xaf: string | null;
  budget_spent_xaf: string | null;
  budget_planned_label: string;
  budget_spent_label: string;
  budget_variance_xaf: number;
  responsible: { id: number; name: string; initials?: string } | null;
  blocked_reason: string;
  is_overdue: boolean;
  notes: string;
  tasks_count: number;
  evidences_count: number;
};

export type ProjectUpdate = {
  id: number;
  update_type: string;
  type_label: string;
  message: string;
  author?: number | null;
  author_name?: string | null;
  author_initials?: string;
  visibility: string;
  created_at: string;
  payload?: Record<string, unknown>;
};

export type Evidence = {
  id: number;
  project_id?: number;
  project_name?: string;
  kind: string;
  title: string;
  caption: string;
  thumbnail_url?: string | null;
  preview_url?: string | null;
  asset_url?: string | null;
  status: string;
  captured_at: string | null;
  captured_by_name?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  is_visible_to_customer?: boolean;
};

export type Property = {
  id: number;
  reference: string;
  name: string;
  property_type: string;
  type_label: string;
  occupancy_status: string;
  occupancy_label: string;
  display_location: string;
  city: string;
  cover_url: string;
  area_m2: string | null;
  rooms_count: number | null;
  last_visited_at: string | null;
  next_visit_at: string | null;
  needs_attention: boolean;
  days_since_last_visit: number | null;
  condition_score: number | null;
  active_contract_label: string;
  is_active: boolean;
  created_at: string;
};

export type PropertyDetail = Property & {
  location_text: string;
  address: string;
  country: string;
  land_area_m2: string | null;
  bedrooms_count: number | null;
  bathrooms_count: number | null;
  levels_count: number | null;
  year_built: number | null;
  tenant_name: string;
  tenant_phone: string;
  has_guardian: boolean;
  is_fenced: boolean;
  has_water: boolean;
  has_electricity: boolean;
  has_security_system: boolean;
  documentation_status: string;
  title_deed_number: string;
  estimated_value_xaf: string | null;
  monthly_rent_xaf: string | null;
  description: string;
  last_inspection_at: string | null;
  manager_name: string;
  open_issues_count: number;
  contracts_count: number;
  photos: Array<{ id: number; kind: string; url: string; thumbnail_url: string; caption: string; taken_at: string | null }>;
};

export type ServiceRequest = {
  id: number;
  reference: string;
  kind: string;
  kind_label: string;
  status: string;
  status_label: string;
  priority: string;
  full_name: string;
  phone: string;
  city: string;
  display_location: string;
  budget_label: string;
  desired_start_date: string | null;
  next_step_label: string;
  estimated_value_xaf: string | null;
  created_at: string;
};

export type ServiceRequestEvent = {
  id: number;
  from_status: string;
  to_status: string;
  to_status_label: string;
  comment: string;
  actor_name: string;
  is_customer_visible: boolean;
  created_at: string;
};

export type ServiceRequestDetail = ServiceRequest & {
  first_name: string;
  last_name: string;
  phone_display: string;
  email: string;
  country: string;
  project_type: string;
  location_text: string;
  budget_min_xaf: string | null;
  budget_max_xaf: string | null;
  description: string;
  objective: string;
  maintenance_frequency: string;
  property_type: string;
  assigned_to_name: string;
  converted_project_reference: string;
  attachments: Array<{ id: number; category: string; url?: string; caption: string; created_at: string }>;
  events: ServiceRequestEvent[];
  updated_at: string;
};

export type OwnedRealization = {
  id: number;
  title: string;
  slug: string;
  realization_type: string;
  type_label: string;
  display_location: string;
  year: number;
  surface_m2: string | null;
  duration_days: number | null;
  cover_url: string | null;
  services: string[];
  budget_display: string;
  budget_xaf: string | null;
  budget_visible: boolean;
  is_featured: boolean;
  views_count: number;
  status: string;
  description: string;
  client_testimonial: string;
  client_name: string;
  media: Array<{ id: number; kind: string; kind_label: string; url: string; thumbnail_url: string; caption: string }>;
  created_at: string;
};

export type CompanyDocument = {
  id: number;
  kind: string;
  kind_label: string;
  title: string;
  reference_number: string;
  issued_at: string | null;
  expires_at: string | null;
  status: string;
  status_label: string;
  review_notes: string;
  reviewed_at: string | null;
  is_expired: boolean;
  created_at: string;
};

export type MyCompanyPayload = {
  company:
    | (CompanyDetail & {
        stats_detail: {
          realizations: { total: number; published: number; pending: number; views: number };
          applications: { total: number; pending: number; shortlisted: number };
        };
        members: Array<{ id: number; user: number; user_name: string; user_phone: string; role: string; role_label: string; job_title: string; is_active: boolean; joined_at: string }>;
        documents: CompanyDocument[];
        role: string;
      })
    | null;
  onboarding_required: boolean;
};

export type AdminCompany = {
  id: number;
  name: string;
  slug: string;
  legal_name: string;
  city: string;
  region: string;
  phone: string;
  email: string;
  verification_status: string;
  status_label: string;
  verification_notes: string;
  verified_at: string | null;
  is_published: boolean;
  is_featured: boolean;
  owner_name: string;
  owner_phone: string;
  years_experience: number;
  employees_count: number;
  projects_count: number;
  rating_average: string | number;
  rating_count: number;
  documents_count: number;
  realizations_count: number;
  created_at: string;
};

export type AdminApplication = {
  id: number;
  reference: string;
  status: string;
  status_label: string;
  opportunity: number;
  opportunity_title: string;
  opportunity_slug: string;
  opportunity_reference: string;
  location: string;
  company: number;
  company_name: string;
  company_slug: string;
  company_verified: boolean;
  company_rating: number;
  estimated_budget_xaf: string | null;
  budget_label: string;
  proposed_duration_days: number | null;
  score: string | null;
  is_decided: boolean;
  status_is_positive: boolean;
  created_at: string;
  updated_at: string;
};

export type DashboardStatistics = {
  projects?: {
    total: number;
    active: number;
    completed: number;
    at_risk: number;
    budget_total_xaf: number;
    budget_total_label: string;
    budget_spent_xaf: number;
    budget_spent_label: string;
    budget_used_percent: number;
  };
  properties?: { total: number; vacant: number; rented: number; portfolio_value_xaf: number; portfolio_value_label: string };
  requests?: { total: number; open: number; converted: number };
  maintenance?: { contracts_total: number; contracts_active: number; next_visits: number };
  evidences?: { published: number };
  billing?: { unpaid_invoices: number; outstanding_label: string };
  notifications?: { unread: number };
  companies?: { total: number; verified: number; pending: number } | Record<string, number>;
  applications?: { total: number; pending: number } | Record<string, number>;
  opportunities?: { open: number } | Record<string, number>;
  payments?: { total_collected_xaf?: number; collected_label?: string } | Record<string, number | string>;
  invoices?: Record<string, number>;
  subscriptions?: Record<string, number>;
};

export type DashboardPayload = {
  user: {
    id: number;
    full_name: string;
    first_name: string;
    initials?: string;
    phone?: string;
    phone_verified?: boolean;
    email?: string;
    role: string;
    role_label?: string;
    city?: string;
    country?: string;
    avatar_url?: string;
    is_diaspora?: boolean;
  };
  permissions: string[];
  spaces?: SpaceLink[];
  statistics?: DashboardStatistics;
  projects?: ProjectCard[];
  projects_at_risk?: Array<{
    id: number;
    reference: string;
    name: string;
    customer_name: string;
    manager_name: string;
    progress_percent: number;
    budget_used_percent: number;
    planned_end: string | null;
    is_late: boolean;
  }>;
  pending_companies?: Array<{
    id: number;
    name: string;
    city: string;
    owner_name: string;
    owner_phone: string;
    created_at: string;
  }>;
  properties?: Property[];
  requests?: ServiceRequest[];
  organizations?: Array<{ id: number; name: string; slug: string; role: string; is_verified: boolean }>;
  next_visits?: Array<{ id: number; title: string; scheduled_for: string; property_name?: string; property_id?: number }>;
  latest_evidences?: Evidence[];
  notifications?: NotificationItem[];
  recent_activity?: ActivityItem[];
  next_actions?: NextActionItem[];
  company?: CompanyCard & { verification_status?: string };
  onboarding_required?: boolean;
  space?: string;
  generated_at: string;
};

export type RealizationDetail = RealizationCard & {
  description: string;
  levels_count: number | null;
  rooms_count: number | null;
  client_testimonial: string;
  client_name: string;
  budget_xaf: string | null;
  budget_visible: boolean;
  company: {
    id: number;
    name: string;
    slug: string;
    city: string;
    verified: boolean;
    rating: number;
    rating_count: number;
    logo_url: string | null;
    years_experience: number;
    phone: string;
    projects_count: number;
  };
  location_detail: Location | null;
  media: Array<{ id: number; kind: string; kind_label: string; url: string; thumbnail_url: string; caption: string }>;
  before_after: { before: Array<{ id: number; url: string; thumbnail_url: string }>; after: Array<{ id: number; url: string; thumbnail_url: string }> };
  status: string;
  views_count: number;
  duration_days: number | null;
};

export type UserOrganization = CompanyCard & {
  role: string;
  verification_status: string;
  profile_completeness?: number;
  missing_items?: Array<{ key: string; label: string; url: string }>;
};
