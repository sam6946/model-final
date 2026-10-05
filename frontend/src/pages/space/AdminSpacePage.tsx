import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  BadgeCheck,
  Building2,
  ClipboardList,
  FileCheck2,
  ShieldCheck,
  TrendingUp,
  Users,
} from 'lucide-react';

import { ApiError, http, type Paginated } from '@/lib/api';
import { Seo } from '@/components/Seo';
import { Alert, CardSkeleton, EmptyState, ErrorState } from '@/components/ui/Feedback';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { Button, ButtonLink } from '@/components/ui/Button';
import { Field, Textarea } from '@/components/ui/Field';
import { useAuth } from '@/hooks/useAuth';
import { useDashboard } from '@/lib/hooks';
import { clampPercent, formatDate, formatXaf, relativeTime, statusLabel } from '@/lib/format';
import { qk } from '@/lib/query';
import type { AdminApplication, AdminCompany } from '@/lib/types';

const TABS = [
  { id: 'pilotage', label: 'Pilotage' },
  { id: 'verifications', label: 'Vérifications' },
  { id: 'candidatures', label: 'Candidatures' },
] as const;

type TabId = (typeof TABS)[number]['id'];

export default function AdminSpacePage() {
  const queryClient = useQueryClient();
  const { user, hasPermission } = useAuth();
  const canVerify = hasPermission('VERIFY_COMPANY') || hasPermission('MANAGE_COMPANY');
  const [tab, setTab] = useState<TabId>('pilotage');
  const [comment, setComment] = useState('');
  const [notice, setNotice] = useState<{ tone: 'success' | 'error'; message: string } | null>(null);

  const dashboard = useDashboard('ADMIN');

  const companies = useQuery<Paginated<AdminCompany>>({
    queryKey: qk.adminCompanies(),
    enabled: tab === 'verifications',
    queryFn: () => http.get<Paginated<AdminCompany>>('/admin/companies/', { params: { verification_status: 'PENDING' } }),
  });

  const applications = useQuery<Paginated<AdminApplication>>({
    queryKey: qk.adminApplications(),
    enabled: tab === 'candidatures',
    queryFn: () => http.get<Paginated<AdminApplication>>('/admin/applications/'),
  });

  const verifyCompany = useMutation({
    mutationFn: ({ id, approve, note }: { id: number; approve: boolean; note: string }) =>
      http.post(`/admin/companies/${id}/verify/`, {
        approve,
        notes: note || (approve ? 'Dossier conforme.' : 'Pièces à compléter.'),
      }),
    onSuccess: (_, variables) => {
      setNotice({
        tone: 'success',
        message: variables.approve
          ? 'Entreprise vérifiée : son badge est désormais visible sur l\u2019annuaire public.'
          : 'Vérification refusée : l\u2019entreprise est notifiée avec les motifs à corriger.',
      });
      setComment('');
      void queryClient.invalidateQueries({ queryKey: qk.adminCompanies() });
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
    onError: (error) => {
      setNotice({
        tone: 'error',
        message: error instanceof ApiError ? error.message : 'La vérification n\u2019a pas pu être enregistrée.',
      });
    },
  });

  const data = dashboard.data;
  const projects = data?.projects_at_risk ?? [];
  const pending = data?.pending_companies ?? [];
  const pendingCompanies = companies.data?.results ?? [];
  const applicationList = applications.data?.results ?? [];
  const stats = data?.statistics ?? {};

  return (
    <>
      <Seo
        title="Back-office KEMTA"
        description="Pilotage opérationnel KEMTA : projets à risque, vérification des entreprises, candidatures et activité récente."
        path="/espace/admin"
        noIndex
      />

      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="flex items-center gap-2 text-[0.8125rem] font-medium uppercase tracking-wide text-k-blue">
              <ShieldCheck className="size-4" aria-hidden />
              Accès opérations
            </p>
            <h1 className="mt-2 text-[1.75rem]">Back-office KEMTA</h1>
            <p className="mt-1.5 text-[0.9375rem] text-k-muted">
              Connecté en tant que {user?.full_name}. Chaque décision prise ici est journalisée et rattachée à votre
              compte.
            </p>
          </div>
          <ButtonLink to="/contact" variant="secondary" size="sm">
            Signaler un incident
          </ButtonLink>
        </header>

        {notice ? (
          <Alert tone={notice.tone === 'success' ? 'success' : 'error'}>{notice.message}</Alert>
        ) : null}

        <nav className="flex flex-wrap gap-2" aria-label="Sections du back-office">
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

        {tab === 'pilotage' ? (
          dashboard.isError ? (
            <ErrorState
              message="Le tableau de bord opérations n'a pas pu être chargé. Vérifiez vos droits d'accès."
              onRetry={() => void dashboard.refetch()}
            />
          ) : dashboard.isLoading ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {Array.from({ length: 4 }).map((_, index) => (
                <CardSkeleton key={index} lines={2} />
              ))}
            </div>
          ) : (
            <>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-k-lg border border-k-line bg-white p-5">
                  <span className="flex size-9 items-center justify-center rounded-k bg-k-blue-soft text-k-blue" aria-hidden>
                    <ClipboardList className="size-4" />
                  </span>
                  <p className="mt-4 text-[0.75rem] uppercase tracking-wide text-k-muted">Projets actifs</p>
                  <p className="mt-1 font-display text-[1.5rem] font-bold text-k-ink">
                    {stats.projects?.active ?? 0}
                  </p>
                  {stats.projects?.at_risk ? (
                    <p className="mt-1 flex items-center gap-1.5 text-[0.75rem] text-k-amber">
                      <AlertTriangle className="size-3.5" aria-hidden />
                      {stats.projects.at_risk} à risque
                    </p>
                  ) : (
                    <p className="mt-1 text-[0.75rem] text-k-muted">
                      {stats.projects?.total ?? 0} projets au total
                    </p>
                  )}
                </div>
                <div className="rounded-k-lg border border-k-line bg-white p-5">
                  <span className="flex size-9 items-center justify-center rounded-k bg-k-blue-soft text-k-blue" aria-hidden>
                    <FileCheck2 className="size-4" />
                  </span>
                  <p className="mt-4 text-[0.75rem] uppercase tracking-wide text-k-muted">Vérifications en attente</p>
                  <p className="mt-1 font-display text-[1.5rem] font-bold text-k-ink">{pending.length}</p>
                  <button
                    type="button"
                    onClick={() => setTab('verifications')}
                    className="mt-1 text-[0.75rem] font-medium text-k-blue hover:text-k-green-dark"
                  >
                    Traiter maintenant
                  </button>
                </div>
                <div className="rounded-k-lg border border-k-line bg-white p-5">
                  <span className="flex size-9 items-center justify-center rounded-k bg-k-blue-soft text-k-blue" aria-hidden>
                    <TrendingUp className="size-4" />
                  </span>
                  <p className="mt-4 text-[0.75rem] uppercase tracking-wide text-k-muted">Budget sous gestion</p>
                  <p className="mt-1 font-display text-[1.5rem] font-bold text-k-ink">
                    {stats.projects?.budget_total_label ?? formatXaf(0, { compact: true })}
                  </p>
                  <p className="mt-1 text-[0.75rem] text-k-muted">
                    {stats.evidences?.published ? `${stats.evidences.published} preuves publiées` : 'Preuves à jour'}
                  </p>
                </div>
                <div className="rounded-k-lg border border-k-line bg-white p-5">
                  <span className="flex size-9 items-center justify-center rounded-k bg-k-blue-soft text-k-blue" aria-hidden>
                    <Users className="size-4" />
                  </span>
                  <p className="mt-4 text-[0.75rem] uppercase tracking-wide text-k-muted">Entreprises</p>
                  <p className="mt-1 font-display text-[1.5rem] font-bold text-k-ink">
                    {typeof stats.companies === 'object' && stats.companies !== null && 'total' in stats.companies
                      ? Number((stats.companies as { total?: number }).total ?? pending.length)
                      : pending.length}
                  </p>
                  <p className="mt-1 text-[0.75rem] text-k-muted">
                    {typeof stats.applications === 'object' && stats.applications !== null && 'total' in stats.applications
                      ? `${Number((stats.applications as { total?: number }).total ?? 0)} candidatures reçues`
                      : 'Candidatures à instruire'}
                  </p>
                </div>
              </div>

              <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
                <section className="rounded-k-lg border border-k-line bg-white p-5">
                  <h2 className="text-[1.125rem]">Projets à surveiller</h2>
                  {projects.length === 0 ? (
                    <div className="mt-4">
                      <EmptyState
                        title="Aucun projet en alerte"
                        description="Les projets en retard, bloqués ou en dépassement de budget apparaissent ici pour arbitrage."
                      />
                    </div>
                  ) : (
                    <ul className="mt-5 divide-y divide-k-line">
                      {projects.slice(0, 8).map((project) => (
                        <li key={project.id} className="py-4">
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div className="min-w-0">
                              <Link
                                to={`/espace/projets/${project.id}`}
                                className="text-[0.9375rem] font-medium text-k-ink hover:text-k-blue"
                              >
                                {project.name}
                              </Link>
                              <p className="mt-0.5 text-[0.75rem] text-k-muted">
                                {project.reference} · client {project.customer_name}
                                {project.manager_name ? ` · suivi ${project.manager_name}` : ''}
                              </p>
                            </div>
                            {project.is_late ? <Badge tone="amber" size="sm">Retard</Badge> : null}
                          </div>

                          <div className="mt-3 flex items-center gap-3">
                            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-k-line">
                              <div
                                className="h-full rounded-full bg-k-green"
                                style={{ width: `${clampPercent(project.progress_percent)}%` }}
                              />
                            </div>
                            <span className="text-[0.75rem] text-k-muted">
                              {clampPercent(project.progress_percent)} % · budget {clampPercent(project.budget_used_percent)} %
                            </span>
                          </div>

                          {project.planned_end ? (
                            <p className="mt-2 text-[0.75rem] text-k-muted">
                              Échéance prévue le {formatDate(project.planned_end)}
                            </p>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  )}
                </section>

                <div className="space-y-6">
                  <section className="rounded-k-lg border border-k-line bg-white p-5">
                    <h2 className="text-[1.125rem]">Dossiers entreprise à vérifier</h2>
                    {pending.length === 0 ? (
                      <p className="mt-3 text-[0.875rem] text-k-muted">Aucun dossier en attente.</p>
                    ) : (
                      <ul className="mt-4 space-y-3.5">
                        {pending.slice(0, 5).map((company) => (
                          <li key={company.id} className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <p className="truncate text-[0.875rem] font-medium text-k-ink">{company.name}</p>
                              <p className="text-[0.75rem] text-k-muted">
                                {company.city} · {company.owner_name} · {company.owner_phone}
                              </p>
                              <p className="text-[0.6875rem] text-k-muted">
                                Soumis {relativeTime(company.created_at)}
                              </p>
                            </div>
                            <Button size="sm" variant="secondary" onClick={() => setTab('verifications')}>
                              Traiter
                            </Button>
                          </li>
                        ))}
                      </ul>
                    )}
                  </section>

                  <section className="rounded-k-lg border border-k-line bg-white p-5">
                    <h2 className="text-[1.125rem]">Activité récente</h2>
                    {(data?.recent_activity ?? []).length === 0 ? (
                      <p className="mt-4 text-[0.875rem] text-k-muted">Aucune activité sur les dernières 24 heures.</p>
                    ) : (
                      <ol className="mt-5 space-y-4">
                        {(data?.recent_activity ?? []).slice(0, 8).map((activity) => (
                          <li key={activity.id} className="relative border-l border-k-line pl-4">
                            <span
                              className={`absolute -left-[5px] top-1.5 size-2.5 rounded-full ${
                                activity.is_important ? 'bg-k-green' : 'bg-k-blue'
                              }`}
                              aria-hidden
                            />
                            <p className="text-[0.875rem] text-k-ink">{activity.message}</p>
                            <p className="mt-0.5 text-[0.6875rem] text-k-muted">
                              {activity.verb_label ? `${activity.verb_label} · ` : ''}
                              {activity.actor_name ? `${activity.actor_name} · ` : ''}
                              {relativeTime(activity.created_at)}
                            </p>
                          </li>
                        ))}
                      </ol>
                    )}
                  </section>
                </div>
              </div>
            </>
          )
        ) : null}

        {tab === 'verifications' ? (
          <section className="rounded-k-lg border border-k-line bg-white p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-[1.125rem]">Dossiers en attente de vérification</h2>
              {companies.data?.count ? (
                <Badge tone="amber" size="sm">
                  {companies.data.count} dossier{companies.data.count > 1 ? 's' : ''}
                </Badge>
              ) : null}
            </div>

            {!canVerify ? (
              <Alert tone="info" className="mt-4">
                Votre rôle permet la consultation mais pas la validation des dossiers. Demandez le droit « Vérifier une
                entreprise » à un administrateur.
              </Alert>
            ) : null}

            {companies.isLoading ? (
              <div className="mt-4 space-y-3">
                {Array.from({ length: 3 }).map((_, index) => (
                  <CardSkeleton key={index} lines={3} />
                ))}
              </div>
            ) : companies.isError ? (
              <ErrorState message="Les dossiers n'ont pas pu être chargés." onRetry={() => void companies.refetch()} />
            ) : pendingCompanies.length === 0 ? (
              <div className="mt-4">
                <EmptyState
                  icon={<BadgeCheck className="size-5 text-k-green" aria-hidden />}
                  title="Aucun dossier en attente"
                  description="Toutes les entreprises soumises ont été traitées. Les nouveaux dossiers apparaissent ici automatiquement."
                />
              </div>
            ) : (
              <>
                <div className="mt-5 max-w-xl">
                  <Field
                    label="Motivation transmise à l'entreprise"
                    htmlFor="verify-comment"
                    hint="Utilisée en cas de refus ; un commentaire par défaut est appliqué si vous laissez vide."
                  >
                    <Textarea
                      id="verify-comment"
                      rows={2}
                      value={comment}
                      onChange={(event) => setComment(event.target.value)}
                      placeholder="RCCM illisible, merci de redéposer une photo nette du document."
                    />
                  </Field>
                </div>

                <ul className="mt-5 divide-y divide-k-line">
                  {pendingCompanies.map((company) => (
                    <li
                      key={company.id}
                      className="flex flex-col gap-4 py-5 lg:flex-row lg:items-center lg:justify-between"
                    >
                      <div className="flex min-w-0 gap-4">
                        <span
                          className="flex size-12 shrink-0 items-center justify-center rounded-k bg-k-blue-soft text-k-blue"
                          aria-hidden
                        >
                          <Building2 className="size-5" />
                        </span>
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2.5">
                            <Link
                              to={`/entreprises/${company.slug}`}
                              className="font-display text-[1rem] font-semibold text-k-ink hover:text-k-blue"
                            >
                              {company.name}
                            </Link>
                            <Badge tone="outline" size="sm">
                              {company.status_label || statusLabel(company.verification_status)}
                            </Badge>
                          </div>
                          <p className="mt-1 text-[0.8125rem] text-k-muted">
                            {company.city} · {company.owner_name} ({company.owner_phone}) · créée le{' '}
                            {formatDate(company.created_at)}
                          </p>
                          <p className="mt-1 text-[0.75rem] text-k-muted">
                            {company.documents_count} pièce(s) · {company.realizations_count} réalisation(s) ·{' '}
                            {company.years_experience} an(s) d&apos;expérience · {company.projects_count} chantier(s)
                          </p>
                        </div>
                      </div>

                      <div className="flex shrink-0 flex-wrap gap-2.5">
                        <ButtonLink to={`/entreprises/${company.slug}`} variant="secondary" size="sm">
                          Examiner le dossier
                        </ButtonLink>
                        <Button
                          size="sm"
                          disabled={!canVerify}
                          loading={verifyCompany.isPending && verifyCompany.variables?.id === company.id}
                          onClick={() => verifyCompany.mutate({ id: company.id, approve: true, note: comment })}
                          icon={<BadgeCheck className="size-4" aria-hidden />}
                        >
                          Valider
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={!canVerify}
                          onClick={() => verifyCompany.mutate({ id: company.id, approve: false, note: comment })}
                        >
                          Refuser
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </section>
        ) : null}

        {tab === 'candidatures' ? (
          <section className="rounded-k-lg border border-k-line bg-white p-5">
            <h2 className="text-[1.125rem]">Candidatures reçues</h2>

            {applications.isLoading ? (
              <div className="mt-4 space-y-3">
                {Array.from({ length: 4 }).map((_, index) => (
                  <CardSkeleton key={index} lines={2} />
                ))}
              </div>
            ) : applications.isError ? (
              <ErrorState
                message="Les candidatures n'ont pas pu être chargées."
                onRetry={() => void applications.refetch()}
              />
            ) : applicationList.length === 0 ? (
              <div className="mt-4">
                <EmptyState
                  icon={<Building2 className="size-5" aria-hidden />}
                  title="Aucune candidature"
                  description="Les candidatures déposées sur les marchés publiés apparaissent ici pour arbitrage."
                />
              </div>
            ) : (
              <div className="mt-5 overflow-x-auto">
                <table className="w-full min-w-[48rem] border-collapse text-left">
                  <thead>
                    <tr className="border-b border-k-line">
                      <th scope="col" className="py-2.5 pr-4 text-[0.75rem] font-semibold uppercase tracking-wide text-k-muted">
                        Référence
                      </th>
                      <th scope="col" className="py-2.5 pr-4 text-[0.75rem] font-semibold uppercase tracking-wide text-k-muted">
                        Marché
                      </th>
                      <th scope="col" className="py-2.5 pr-4 text-[0.75rem] font-semibold uppercase tracking-wide text-k-muted">
                        Entreprise
                      </th>
                      <th scope="col" className="py-2.5 pr-4 text-[0.75rem] font-semibold uppercase tracking-wide text-k-muted">
                        Budget proposé
                      </th>
                      <th scope="col" className="py-2.5 pr-4 text-[0.75rem] font-semibold uppercase tracking-wide text-k-muted">
                        Score
                      </th>
                      <th scope="col" className="py-2.5 pr-4 text-[0.75rem] font-semibold uppercase tracking-wide text-k-muted">
                        Statut
                      </th>
                      <th scope="col" className="py-2.5 text-[0.75rem] font-semibold uppercase tracking-wide text-k-muted">
                        Reçue le
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-k-line">
                    {applicationList.map((application) => (
                      <tr key={application.id}>
                        <td className="py-3 pr-4 text-[0.8125rem] font-medium text-k-blue">{application.reference}</td>
                        <td className="py-3 pr-4 text-[0.8125rem] text-k-ink">
                          <Link
                            to={`/opportunites/${application.opportunity_slug}`}
                            className="hover:text-k-blue"
                          >
                            {application.opportunity_title}
                          </Link>
                          {application.location ? (
                            <span className="mt-0.5 block text-[0.75rem] text-k-muted">{application.location}</span>
                          ) : null}
                        </td>
                        <td className="py-3 pr-4 text-[0.8125rem] text-k-ink">
                          <Link to={`/entreprises/${application.company_slug}`} className="hover:text-k-blue">
                            {application.company_name}
                          </Link>
                          {application.company_verified ? (
                            <Badge tone="green" size="sm" className="ml-2">
                              Vérifiée
                            </Badge>
                          ) : null}
                        </td>
                        <td className="py-3 pr-4 text-[0.8125rem] text-k-muted">{application.budget_label || '—'}</td>
                        <td className="py-3 pr-4 text-[0.8125rem] text-k-muted">
                          {application.score ? `${Number(application.score)}/100` : '—'}
                        </td>
                        <td className="py-3 pr-4">
                          <StatusBadge code={application.status} label={application.status_label} />
                        </td>
                        <td className="py-3 text-[0.8125rem] text-k-muted">{formatDate(application.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        ) : null}
      </div>
    </>
  );
}
