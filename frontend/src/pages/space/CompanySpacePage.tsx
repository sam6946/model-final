import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  BadgeCheck,
  Building2,
  Eye,
  FilePlus2,
  FileText,
  Send,
  Upload,
  Wallet,
} from 'lucide-react';

import { ApiError, http, type Paginated } from '@/lib/api';
import { Seo } from '@/components/Seo';
import { Alert, CardSkeleton, EmptyState, ErrorState } from '@/components/ui/Feedback';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { Button, ButtonLink } from '@/components/ui/Button';
import { Field, Input, Select, Textarea } from '@/components/ui/Field';
import { formatDate, formatXaf, statusLabel } from '@/lib/format';
import { qk } from '@/lib/query';
import type { AdminApplication, MyCompanyPayload, OwnedRealization, Plan } from '@/lib/types';

type SubscriptionPayload = {
  company?: { id: number; name: string } | null;
  subscription: {
    id: number;
    plan: Plan;
    status: string;
    status_label: string;
    current_period_end: string;
    applications_used: number;
    days_remaining: number;
    renews_soon: boolean;
    is_trial: boolean;
  } | null;
  limits?: Record<string, number | null>;
  message?: string;
};

const DOCUMENT_KINDS = [
  { value: 'REGISTRE_COMMERCE', label: 'Registre de commerce (RCCM)' },
  { value: 'ATTESTATION_FISCALE', label: 'Attestation fiscale' },
  { value: 'CNPS', label: 'Attestation CNPS' },
  { value: 'ASSURANCE', label: 'Attestation d\u2019assurance' },
  { value: 'REFERENCE', label: 'Référence de chantier' },
  { value: 'OTHER', label: 'Autre pièce' },
];

const REALIZATION_TYPES = [
  'VILLA',
  'MAISON',
  'IMMEUBLE',
  'APPARTEMENT',
  'LOCAL_COMMERCIAL',
  'ECOLE',
  'SANTE',
  'ROUTE',
  'RENOVATION',
];

const TABS = [
  { id: 'dossier', label: 'Dossier & pièces' },
  { id: 'realisations', label: 'Réalisations' },
  { id: 'candidatures', label: 'Candidatures' },
  { id: 'abonnement', label: 'Abonnement' },
] as const;

type TabId = (typeof TABS)[number]['id'];

const EMPTY_REALIZATION = {
  title: '',
  realization_type: 'VILLA',
  description: '',
  location_text: '',
  year: String(new Date().getFullYear()),
  surface_m2: '',
  budget_xaf: '',
};

export default function CompanySpacePage() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<TabId>('dossier');
  const [notice, setNotice] = useState<{ tone: 'success' | 'error'; message: string } | null>(null);

  const [uploadKind, setUploadKind] = useState('REGISTRE_COMMERCE');
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploading, setUploading] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const [realization, setRealization] = useState(EMPTY_REALIZATION);
  const [realizationError, setRealizationError] = useState<string | null>(null);

  const overview = useQuery<MyCompanyPayload>({
    queryKey: qk.myCompany(),
    queryFn: () => http.get<MyCompanyPayload>('/company/mine/'),
    retry: false,
  });

  const realizations = useQuery<Paginated<OwnedRealization>>({
    queryKey: qk.companyRealizations(),
    enabled: tab === 'realisations',
    queryFn: () => http.get<Paginated<OwnedRealization>>('/company/realizations/'),
  });

  const applications = useQuery<Paginated<AdminApplication>>({
    queryKey: qk.applications(),
    enabled: tab === 'candidatures',
    queryFn: () => http.get<Paginated<AdminApplication>>('/applications/mine/'),
  });

  const subscription = useQuery<SubscriptionPayload>({
    queryKey: qk.subscription(),
    enabled: tab === 'abonnement',
    queryFn: () => http.get<SubscriptionPayload>('/subscriptions/mine/'),
  });

  const plans = useQuery<Paginated<Plan>>({
    queryKey: qk.plans(),
    enabled: tab === 'abonnement',
    queryFn: () => http.get<Paginated<Plan>>('/plans/'),
  });

  const subscribe = useMutation({
    mutationFn: ({ planCode, provider }: { planCode: string; provider: string }) =>
      http.post('/subscriptions/mine/', { plan_code: planCode, provider }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: qk.subscription() });
      void queryClient.invalidateQueries({ queryKey: qk.myCompany() });
    },
    onError: (error) => {
      setNotice({
        tone: 'error',
        message: error instanceof ApiError ? error.message : 'Le changement d\u2019offre a échoué.',
      });
    },
  });

  const createRealization = useMutation({
    mutationFn: (payload: Record<string, unknown>) => http.post('/company/realizations/', payload),
    onSuccess: () => {
      setRealization(EMPTY_REALIZATION);
      setNotice({
        tone: 'success',
        message:
          'Réalisation enregistrée. Si votre dossier est vérifié, elle est publiée immédiatement ; sinon elle passe en validation KEMTA.',
      });
      void queryClient.invalidateQueries({ queryKey: qk.companyRealizations() });
    },
  });

  const uploadDocument = async () => {
    setNotice(null);
    const file = fileInput.current?.files?.[0];
    if (!file) {
      setNotice({ tone: 'error', message: 'Sélectionnez d\u2019abord le fichier de la pièce (photo nette ou PDF).' });
      return;
    }
    if (!uploadTitle.trim()) {
      setNotice({ tone: 'error', message: 'Donnez un intitulé à la pièce (ex. « RCCM 2026 »).' });
      return;
    }

    setUploading(true);
    try {
      const body = new FormData();
      body.append('file', file);
      body.append('upload_kind', 'DOCUMENT');
      const asset = await http.post<{ id: number }>('/uploads/direct/', body, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      await http.post('/company/documents/', { kind: uploadKind, title: uploadTitle.trim(), asset: asset.id });
      await queryClient.invalidateQueries({ queryKey: qk.myCompany() });
      setUploadTitle('');
      if (fileInput.current) fileInput.current.value = '';
      setNotice({ tone: 'success', message: 'Pièce envoyée : l\u2019équipe KEMTA la vérifie et vous notifie sa décision.' });
    } catch (error) {
      setNotice({
        tone: 'error',
        message: error instanceof ApiError ? error.message : "L'envoi de la pièce a échoué. Réessayez dans un instant.",
      });
    } finally {
      setUploading(false);
    }
  };

  /* ------------------------------------------------------------- pas de profil */
  if (overview.isSuccess && (!overview.data.company || overview.data.onboarding_required)) {
    return (
      <>
        <Seo
          title="Espace entreprise BTP"
          description="Créez votre profil entreprise KEMTA, déposez vos pièces et candidatez aux marchés de construction."
          path="/espace/entreprise"
          noIndex
        />
        <EmptyState
          icon={<Building2 className="size-5" aria-hidden />}
          title="Vous n'avez pas encore de profil entreprise"
          description="Créez votre profil pour déposer vos pièces administratives, publier vos réalisations et candidater aux marchés publiés sur KEMTA."
          action={<ButtonLink to="/espace-entreprise">Créer mon profil entreprise</ButtonLink>}
        />
      </>
    );
  }

  if (overview.isError) {
    return (
      <>
        <Seo
          title="Espace entreprise"
          description="Gérez votre profil entreprise, vos pièces et vos candidatures KEMTA."
          path="/espace/entreprise"
          noIndex
        />
        <ErrorState
          message={
            overview.error instanceof ApiError
              ? overview.error.message
              : "L'espace entreprise n'a pas pu être chargé."
          }
          onRetry={() => void overview.refetch()}
        />
      </>
    );
  }

  if (overview.isLoading || !overview.data?.company) {
    return (
      <div className="space-y-6">
        <CardSkeleton lines={3} />
        <CardSkeleton lines={6} />
      </div>
    );
  }

  const company = overview.data.company;
  const stats = company.stats_detail;
  const documents = company.documents ?? [];
  const members = company.members ?? [];
  const pendingDocuments = documents.filter((document) => document.status === 'PENDING');
  const isVerified = Boolean(company.is_verified);

  return (
    <>
      <Seo
        title={`${company.name} — espace entreprise`}
        description="Suivez la vérification de votre dossier, publiez vos réalisations, candidatez aux marchés et gérez votre abonnement KEMTA."
        path="/espace/entreprise"
        noIndex
      />

      <div className="flex flex-col gap-6">
        <header className="rounded-k-lg border border-k-line bg-white p-5 sm:p-6">
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div className="flex items-start gap-4">
              {company.logo_url ? (
                <img
                  src={company.logo_url}
                  alt=""
                  className="size-14 shrink-0 rounded-k border border-k-line object-contain p-1"
                />
              ) : (
                <span
                  className="flex size-14 shrink-0 items-center justify-center rounded-k bg-k-blue-soft text-k-blue"
                  aria-hidden
                >
                  <Building2 className="size-6" />
                </span>
              )}
              <div className="min-w-0">
                <h1 className="text-[1.5rem]">{company.name}</h1>
                <p className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-[0.8125rem] text-k-muted">
                  <span>{company.city}</span>
                  {company.intervention_label ? <span>{company.intervention_label}</span> : null}
                  <Link
                    to={`/entreprises/${company.slug}`}
                    className="font-medium text-k-blue hover:text-k-green-dark"
                  >
                    Voir mon profil public
                  </Link>
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {isVerified ? (
                    <Badge tone="green">
                      <BadgeCheck className="size-3.5" aria-hidden />
                      Entreprise vérifiée
                    </Badge>
                  ) : (
                    <Badge tone="amber">{company.verification_status === 'REJECTED' ? 'Dossier à compléter' : 'Dossier en cours de vérification'}</Badge>
                  )}
                  {company.role ? <Badge tone="outline">Votre rôle : {statusLabel(company.role)}</Badge> : null}
                  <Badge tone="neutral">{company.documents_verified} pièce(s) validée(s)</Badge>
                </div>
              </div>
            </div>

            <dl className="grid grid-cols-3 gap-5 text-center">
              <div>
                <dt className="text-[0.6875rem] uppercase tracking-wide text-k-muted">Réalisations</dt>
                <dd className="mt-0.5 font-display text-[1.25rem] font-bold text-k-ink">
                  {stats.realizations.published}
                  <span className="text-[0.75rem] font-medium text-k-muted">/{stats.realizations.total}</span>
                </dd>
                <p className="text-[0.6875rem] text-k-muted">publiées</p>
              </div>
              <div>
                <dt className="text-[0.6875rem] uppercase tracking-wide text-k-muted">Vues catalogue</dt>
                <dd className="mt-0.5 font-display text-[1.25rem] font-bold text-k-ink">{stats.realizations.views}</dd>
                <p className="text-[0.6875rem] text-k-muted">sur vos fiches</p>
              </div>
              <div>
                <dt className="text-[0.6875rem] uppercase tracking-wide text-k-muted">Candidatures</dt>
                <dd className="mt-0.5 font-display text-[1.25rem] font-bold text-k-ink">
                  {stats.applications.total}
                </dd>
                <p className="text-[0.6875rem] text-k-muted">{stats.applications.shortlisted} présélectionnée(s)</p>
              </div>
            </dl>
          </div>

          {!isVerified ? (
            <Alert tone="warning" className="mt-5" title="Ce qu'il reste à faire pour obtenir le badge vérifié">
              <ul className="mt-2 space-y-1.5">
                <li className="flex items-start gap-2">
                  <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-k-amber" aria-hidden />
                  Déposer au minimum le registre de commerce et l&apos;attestation fiscale (seuil atteint :{' '}
                  {documents.length}/2 pièces).
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-k-amber" aria-hidden />
                  Compléter la présentation, le logo et la photo de couverture depuis votre profil public.
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-k-amber" aria-hidden />
                  Publier au moins une réalisation avec photos pour rassurer les clients.
                </li>
              </ul>
            </Alert>
          ) : null}
        </header>

        {notice ? (
          <Alert tone={notice.tone === 'success' ? 'success' : 'error'}>{notice.message}</Alert>
        ) : null}

        <nav className="flex flex-wrap gap-2" aria-label="Sections de l'espace entreprise">
          {TABS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setTab(item.id)}
              aria-current={tab === item.id}
              className={`rounded-k border px-4 py-2 text-[0.875rem] font-medium transition-colors ${
                tab === item.id
                  ? 'border-k-blue bg-k-blue text-white'
                  : 'border-k-line bg-white text-k-ink hover:border-k-blue-line'
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>

        {tab === 'dossier' ? (
          <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
            <section className="rounded-k-lg border border-k-line bg-white p-5">
              <h2 className="flex items-center gap-2 text-[1.125rem]">
                <FileText className="size-4 text-k-blue" aria-hidden />
                Mes pièces administratives
              </h2>

              {documents.length === 0 ? (
                <div className="mt-4">
                  <EmptyState
                    icon={<FilePlus2 className="size-5" aria-hidden />}
                    title="Aucune pièce déposée"
                    description="Déposez au minimum votre registre de commerce et votre attestation fiscale pour permettre la vérification de votre entreprise."
                  />
                </div>
              ) : (
                <ul className="mt-5 divide-y divide-k-line">
                  {documents.map((document) => (
                    <li key={document.id} className="flex flex-wrap items-start justify-between gap-3 py-4">
                      <div className="min-w-0">
                        <p className="text-[0.9375rem] font-medium text-k-ink">{document.title}</p>
                        <p className="mt-0.5 text-[0.75rem] text-k-muted">
                          {document.kind_label} · déposée le {formatDate(document.created_at)}
                          {document.reference_number ? ` · réf. ${document.reference_number}` : ''}
                        </p>
                        {document.review_notes ? (
                          <p className="mt-1.5 text-[0.8125rem] text-k-muted">
                            Observation KEMTA : {document.review_notes}
                          </p>
                        ) : null}
                      </div>
                      <StatusBadge code={document.status} label={document.status_label} />
                    </li>
                  ))}
                </ul>
              )}

              {pendingDocuments.length ? (
                <p className="mt-4 text-[0.8125rem] text-k-muted">
                  {pendingDocuments.length} pièce{pendingDocuments.length > 1 ? 's' : ''} en cours d&apos;examen —
                  vous recevez une notification à la décision.
                </p>
              ) : null}
            </section>

            <div className="space-y-6">
              <section className="rounded-k-lg border border-k-line bg-white p-5">
                <h2 className="flex items-center gap-2 text-[1.0625rem]">
                  <Upload className="size-4 text-k-green" aria-hidden />
                  Déposer une pièce
                </h2>

                <div className="mt-4 space-y-4">
                  <Field label="Type de pièce" htmlFor="doc-kind" required>
                    <Select id="doc-kind" value={uploadKind} onChange={(event) => setUploadKind(event.target.value)}>
                      {DOCUMENT_KINDS.map((kind) => (
                        <option key={kind.value} value={kind.value}>
                          {kind.label}
                        </option>
                      ))}
                    </Select>
                  </Field>

                  <Field label="Intitulé" htmlFor="doc-title" required hint="Tel qu'il apparaîtra dans votre dossier">
                    <Input
                      id="doc-title"
                      value={uploadTitle}
                      onChange={(event) => setUploadTitle(event.target.value)}
                      placeholder="RCCM 2026"
                    />
                  </Field>

                  <Field label="Fichier" htmlFor="doc-file" required hint="Photo nette ou PDF lisible, 10 Mo maximum.">
                    <input
                      ref={fileInput}
                      id="doc-file"
                      type="file"
                      accept="image/*,application/pdf"
                      className="w-full rounded-k border border-k-line bg-white px-3 py-2.5 text-[0.875rem] file:mr-3 file:rounded-k-sm file:border-0 file:bg-k-blue-soft file:px-3 file:py-1.5 file:text-[0.8125rem] file:font-medium file:text-k-blue"
                    />
                  </Field>

                  <Button onClick={uploadDocument} loading={uploading} block icon={<Upload className="size-4" aria-hidden />}>
                    Envoyer la pièce
                  </Button>
                </div>
              </section>

              {members.length ? (
                <section className="rounded-k-lg border border-k-line bg-white p-5">
                  <h2 className="text-[1.0625rem]">Équipe ({members.length})</h2>
                  <ul className="mt-4 space-y-3">
                    {members.map((member) => (
                      <li key={member.id} className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-[0.875rem] font-medium text-k-ink">{member.user_name}</p>
                          <p className="text-[0.75rem] text-k-muted">
                            {member.job_title || member.role_label} · {member.user_phone}
                          </p>
                        </div>
                        {!member.is_active ? (
                          <Badge tone="outline" size="sm">
                            Inactif
                          </Badge>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}
            </div>
          </div>
        ) : null}

        {tab === 'realisations' ? (
          <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
            <section className="rounded-k-lg border border-k-line bg-white p-5">
              <h2 className="text-[1.125rem]">Mes réalisations</h2>

              {realizations.isLoading ? (
                <div className="mt-4 space-y-3">
                  {Array.from({ length: 3 }).map((_, index) => (
                    <CardSkeleton key={index} lines={2} />
                  ))}
                </div>
              ) : (realizations.data?.results ?? []).length === 0 ? (
                <div className="mt-4">
                  <EmptyState
                    icon={<Building2 className="size-5" aria-hidden />}
                    title="Aucune réalisation publiée"
                    description="Publiez vos chantiers livrés : photos, surface, durée et budget. Chaque réalisation renforce la confiance des clients."
                  />
                </div>
              ) : (
                <ul className="mt-5 divide-y divide-k-line">
                  {(realizations.data?.results ?? []).map((item) => (
                    <li key={item.id} className="flex flex-wrap items-start justify-between gap-3 py-4">
                      <div className="flex min-w-0 gap-3">
                        {item.cover_url ? (
                          <img src={item.cover_url} alt="" loading="lazy" className="size-14 shrink-0 rounded-k object-cover" />
                        ) : (
                          <span
                            className="flex size-14 shrink-0 items-center justify-center rounded-k bg-k-mist text-k-muted"
                            aria-hidden
                          >
                            <Building2 className="size-5" />
                          </span>
                        )}
                        <div className="min-w-0">
                          <Link
                            to={`/realisations/${item.slug}`}
                            className="text-[0.9375rem] font-medium text-k-ink hover:text-k-blue"
                          >
                            {item.title}
                          </Link>
                          <p className="mt-0.5 text-[0.75rem] text-k-muted">
                            {item.type_label} · {item.year} · {item.display_location || 'Localisation non précisée'}
                          </p>
                          <p className="mt-0.5 flex items-center gap-1.5 text-[0.75rem] text-k-muted">
                            <Eye className="size-3" aria-hidden />
                            {item.views_count} vue(s)
                            {item.surface_m2 ? ` · ${Number(item.surface_m2)} m²` : ''}
                            {item.budget_display ? ` · ${item.budget_display}` : ''}
                          </p>
                        </div>
                      </div>
                      <div className="flex shrink-0 flex-col items-end gap-2">
                        <StatusBadge code={item.status} label={statusLabel(item.status)} />
                        {item.is_featured ? (
                          <Badge tone="green" size="sm">
                            Mise en avant
                          </Badge>
                        ) : null}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="rounded-k-lg border border-k-line bg-white p-5">
              <h2 className="flex items-center gap-2 text-[1.0625rem]">
                <FilePlus2 className="size-4 text-k-green" aria-hidden />
                Publier une réalisation
              </h2>
              <p className="mt-1.5 text-[0.8125rem] text-k-muted">
                Les photos s&apos;ajoutent ensuite depuis la fiche de la réalisation (avant / après).
              </p>

              {realizationError ? (
                <Alert tone="error" className="mt-4">
                  {realizationError}
                </Alert>
              ) : null}

              <form
                className="mt-4 space-y-4"
                onSubmit={async (event) => {
                  event.preventDefault();
                  setRealizationError(null);
                  if (realization.title.trim().length < 5) {
                    setRealizationError('Donnez un titre explicite (ex. « Villa R+1 de 320 m² — Bonapriso »).');
                    return;
                  }
                  if (realization.description.trim().length < 60) {
                    setRealizationError(
                      'Décrivez les travaux en 60 caractères minimum : c\u2019est ce qui convaincra les clients.',
                    );
                    return;
                  }
                  try {
                    await createRealization.mutateAsync({
                      title: realization.title.trim(),
                      realization_type: realization.realization_type,
                      description: realization.description.trim(),
                      location_text: realization.location_text.trim(),
                      country: 'CM',
                      year: realization.year ? Number(realization.year) : null,
                      surface_m2: realization.surface_m2 ? Number(realization.surface_m2) : null,
                      budget_xaf: realization.budget_xaf || null,
                      budget_visible: false,
                    });
                  } catch (error) {
                    setRealizationError(
                      error instanceof ApiError
                        ? error.message
                        : 'La publication a échoué. Vérifiez les informations puis réessayez.',
                    );
                  }
                }}
              >
                <Field label="Titre" htmlFor="r-title" required>
                  <Input
                    id="r-title"
                    value={realization.title}
                    onChange={(event) => setRealization({ ...realization, title: event.target.value })}
                    placeholder="Villa R+1 de 320 m² — Bonapriso"
                  />
                </Field>

                <Field label="Type d'ouvrage" htmlFor="r-type" required>
                  <Select
                    id="r-type"
                    value={realization.realization_type}
                    onChange={(event) => setRealization({ ...realization, realization_type: event.target.value })}
                  >
                    {REALIZATION_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {statusLabel(type)}
                      </option>
                    ))}
                  </Select>
                </Field>

                <Field label="Localisation" htmlFor="r-location" hint="Ville et quartier">
                  <Input
                    id="r-location"
                    value={realization.location_text}
                    onChange={(event) => setRealization({ ...realization, location_text: event.target.value })}
                    placeholder="Bonapriso, Douala"
                  />
                </Field>

                <div className="grid grid-cols-3 gap-3">
                  <Field label="Année" htmlFor="r-year">
                    <Input
                      id="r-year"
                      inputMode="numeric"
                      value={realization.year}
                      onChange={(event) =>
                        setRealization({ ...realization, year: event.target.value.replace(/\D/g, '').slice(0, 4) })
                      }
                    />
                  </Field>
                  <Field label="Surface" htmlFor="r-surface" hint="m²">
                    <Input
                      id="r-surface"
                      inputMode="numeric"
                      value={realization.surface_m2}
                      onChange={(event) =>
                        setRealization({ ...realization, surface_m2: event.target.value.replace(/\D/g, '') })
                      }
                    />
                  </Field>
                  <Field label="Budget" htmlFor="r-budget" hint="FCFA">
                    <Input
                      id="r-budget"
                      inputMode="numeric"
                      value={realization.budget_xaf}
                      onChange={(event) =>
                        setRealization({ ...realization, budget_xaf: event.target.value.replace(/\D/g, '') })
                      }
                    />
                  </Field>
                </div>

                <Field label="Description" htmlFor="r-description" required hint="60 caractères minimum">
                  <Textarea
                    id="r-description"
                    rows={4}
                    value={realization.description}
                    onChange={(event) => setRealization({ ...realization, description: event.target.value })}
                    placeholder="Construction complète d'une villa R+1 de 320 m² habitables, livrée en 11 mois avec suivi hebdomadaire."
                  />
                </Field>

                <Button
                  type="submit"
                  block
                  loading={createRealization.isPending}
                  icon={<Send className="size-4" aria-hidden />}
                >
                  Publier la réalisation
                </Button>
              </form>
            </section>
          </div>
        ) : null}

        {tab === 'candidatures' ? (
          <section className="rounded-k-lg border border-k-line bg-white p-5">
            <h2 className="text-[1.125rem]">Mes candidatures aux marchés</h2>

            {applications.isLoading ? (
              <div className="mt-4 space-y-3">
                {Array.from({ length: 3 }).map((_, index) => (
                  <CardSkeleton key={index} lines={2} />
                ))}
              </div>
            ) : (applications.data?.results ?? []).length === 0 ? (
              <div className="mt-4">
                <EmptyState
                  title="Aucune candidature déposée"
                  description="Parcourez les marchés ouverts et candidatez avec votre profil, vos références et votre proposition."
                  action={
                    <ButtonLink to="/opportunites" size="sm">
                      Voir les marchés ouverts
                    </ButtonLink>
                  }
                />
              </div>
            ) : (
              <ul className="mt-5 divide-y divide-k-line">
                {(applications.data?.results ?? []).map((application) => (
                  <li key={application.id} className="flex flex-wrap items-start justify-between gap-3 py-4">
                    <div className="min-w-0">
                      <Link
                        to={`/opportunites/${application.opportunity_slug}`}
                        className="text-[0.9375rem] font-medium text-k-ink hover:text-k-blue"
                      >
                        {application.opportunity_title}
                      </Link>
                      <p className="mt-0.5 text-[0.75rem] text-k-muted">
                        {application.reference} · envoyée le {formatDate(application.created_at)}
                        {application.location ? ` · ${application.location}` : ''}
                      </p>
                      <p className="mt-0.5 text-[0.75rem] text-k-muted">
                        {application.budget_label ? `Budget proposé ${application.budget_label}` : 'Budget non communiqué'}
                        {application.proposed_duration_days
                          ? ` · ${application.proposed_duration_days} jours`
                          : ''}
                        {application.score ? ` · score ${Number(application.score)}/100` : ''}
                      </p>
                    </div>
                    <StatusBadge code={application.status} label={application.status_label} />
                  </li>
                ))}
              </ul>
            )}
          </section>
        ) : null}

        {tab === 'abonnement' ? (
          <div className="grid gap-6 lg:grid-cols-2">
            <section className="rounded-k-lg border border-k-line bg-white p-5">
              <h2 className="flex items-center gap-2 text-[1.125rem]">
                <Wallet className="size-4 text-k-blue" aria-hidden />
                Mon abonnement
              </h2>

              {subscription.isLoading ? (
                <CardSkeleton lines={3} />
              ) : subscription.data?.subscription ? (
                <div className="mt-4 rounded-k border border-k-line p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-display text-[1.125rem] font-semibold text-k-ink">
                        Offre {subscription.data.subscription.plan.name}
                      </p>
                      <p className="mt-1 text-[0.8125rem] text-k-muted">
                        {subscription.data.subscription.plan.price_xaf > 0
                          ? `${formatXaf(subscription.data.subscription.plan.price_xaf)} / mois`
                          : 'Offre gratuite'}
                      </p>
                    </div>
                    <StatusBadge
                      code={subscription.data.subscription.status}
                      label={subscription.data.subscription.status_label}
                    />
                  </div>
                  <p className="mt-3 text-[0.75rem] text-k-muted">
                    Prochaine échéance le {formatDate(subscription.data.subscription.current_period_end)} ·{' '}
                    {subscription.data.subscription.applications_used} candidature(s) utilisée(s)
                    {subscription.data.limits?.applications_per_month
                      ? ` sur ${subscription.data.limits.applications_per_month}`
                      : ''}
                  </p>
                </div>
              ) : (
                <Alert tone="info" className="mt-4">
                  {subscription.data?.message ??
                    'Vous utilisez l\u2019offre gratuite. Passez à une offre payante pour publier davantage de réalisations et candidater à plus de marchés.'}
                </Alert>
              )}
            </section>

            <section className="rounded-k-lg border border-k-line bg-white p-5">
              <h2 className="text-[1.125rem]">Changer d&apos;offre</h2>
              <p className="mt-1.5 text-[0.8125rem] text-k-muted">
                Paiement Mobile Money (MTN ou Orange), carte bancaire ou virement. Les prix sont définis par KEMTA et
                affichés en francs CFA.
              </p>

              {plans.isLoading ? (
                <CardSkeleton lines={4} />
              ) : (
                <ul className="mt-4 space-y-3">
                  {(plans.data?.results ?? []).map((plan) => (
                    <li
                      key={plan.id}
                      className="flex flex-wrap items-center justify-between gap-3 rounded-k border border-k-line p-4"
                    >
                      <div className="min-w-0">
                        <p className="font-display text-[0.9375rem] font-semibold text-k-ink">{plan.name}</p>
                        <p className="mt-0.5 text-[0.8125rem] text-k-muted">
                          {plan.price_label || (plan.price_xaf > 0 ? `${formatXaf(plan.price_xaf)} / mois` : 'Gratuit')}{' '}
                          · {plan.tagline}
                        </p>
                        <p className="mt-1 text-[0.75rem] text-k-muted">
                          Réalisations : {plan.limits?.realizations ?? 'illimitées'} · Candidatures :{' '}
                          {plan.limits?.applications_per_month ?? 'illimitées'} / mois
                        </p>
                      </div>
                      <Button
                        size="sm"
                        variant={plan.is_recommended ? 'primary' : 'secondary'}
                        loading={subscribe.isPending && subscribe.variables?.planCode === plan.code}
                        onClick={() => subscribe.mutate({ planCode: plan.code, provider: 'MANUAL' })}
                      >
                        {plan.price_xaf > 0 ? 'Souscrire' : 'Revenir au gratuit'}
                      </Button>
                    </li>
                  ))}
                </ul>
              )}

              {subscribe.isSuccess ? (
                <Alert tone="success" className="mt-4" title="Abonnement mis à jour">
                  Votre facture est disponible dans votre espace. Le paiement Mobile Money est confirmé par KEMTA dès
                  réception de la référence de transaction.
                </Alert>
              ) : null}
            </section>
          </div>
        ) : null}
      </div>
    </>
  );
}
