import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Bell,
  Building2,
  CalendarCheck,
  Camera,
  FileText,
  HardHat,
  Home,
  Plus,
  TrendingUp,
  Wallet,
} from 'lucide-react';

import { Seo } from '@/components/Seo';
import { Alert, CardSkeleton, EmptyState, ErrorState } from '@/components/ui/Feedback';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { ButtonLink } from '@/components/ui/Button';
import { useAuth } from '@/hooks/useAuth';
import { useDashboard, useMyRequests } from '@/lib/hooks';
import { clampPercent, formatDate, formatXaf, relativeTime } from '@/lib/format';

function StatCard({
  label,
  value,
  hint,
  icon: Icon,
}: {
  label: string;
  value: string;
  hint?: string;
  icon: typeof Wallet;
}) {
  return (
    <div className="rounded-k-lg border border-k-line bg-white p-5">
      <span className="flex size-9 items-center justify-center rounded-k bg-k-blue-soft text-k-blue" aria-hidden>
        <Icon className="size-4" />
      </span>
      <p className="mt-4 text-[0.75rem] uppercase tracking-wide text-k-muted">{label}</p>
      <p className="mt-1 font-display text-[1.5rem] font-bold text-k-ink">{value}</p>
      {hint ? <p className="mt-1 text-[0.75rem] text-k-muted">{hint}</p> : null}
    </div>
  );
}

export default function SpaceHomePage() {
  const { user, phoneVerified } = useAuth();
  const dashboard = useDashboard('CLIENT');
  const requests = useMyRequests();

  if (dashboard.isError) {
    return (
      <ErrorState
        message="Votre tableau de bord n'a pas pu être chargé. Vérifiez votre connexion puis réessayez."
        onRetry={() => void dashboard.refetch()}
      />
    );
  }

  const data = dashboard.data;
  const projects = data?.statistics?.projects;
  const properties = data?.statistics?.properties;
  const evidences = data?.statistics?.evidences;
  const projectList = data?.projects ?? [];
  const requestList = (requests.data?.results ?? data?.requests ?? []).slice(0, 4);
  const notifications = (data?.notifications ?? []).slice(0, 4);
  const latestEvidences = (data?.latest_evidences ?? []).slice(0, 4);
  const visits = (data?.next_visits ?? []).slice(0, 3);
  const actions = (data?.next_actions ?? []).slice(0, 4);

  return (
    <>
      <Seo
        title="Mon espace KEMTA"
        description="Suivez vos projets, vos propriétés, vos demandes et vos notifications depuis votre espace client KEMTA."
        path="/espace"
        noIndex
      />

      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-[1.75rem]">Bonjour {user?.first_name}</h1>
            <p className="mt-1.5 text-[0.9375rem] text-k-muted">
              {projectList.length
                ? `Vous suivez ${projectList.length} projet${projectList.length > 1 ? 's' : ''}${
                    properties?.total ? ` et ${properties.total} propriété${properties.total > 1 ? 's' : ''}` : ''
                  }.`
                : 'Bienvenue sur votre espace KEMTA. Déposez une demande pour démarrer votre premier projet.'}
            </p>
          </div>
          <div className="flex flex-wrap gap-2.5">
            <ButtonLink to="/demande" size="sm" icon={<Plus className="size-4" aria-hidden />}>
              Nouvelle demande
            </ButtonLink>
            <ButtonLink
              to="/espace/proprietes"
              variant="secondary"
              size="sm"
              icon={<Home className="size-4" aria-hidden />}
            >
              Mes propriétés
            </ButtonLink>
          </div>
        </header>

        {!phoneVerified ? (
          <Alert tone="warning" title="Vérifiez votre numéro de téléphone">
            Un numéro vérifié sécurise votre accès et permet à votre chargé de suivi de vous joindre. Contactez-nous
            si vous n&apos;avez pas reçu le code de vérification.
          </Alert>
        ) : null}

        {dashboard.isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <CardSkeleton key={index} lines={2} />
            ))}
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Projets suivis"
              value={String(projects?.active ?? projectList.length)}
              hint={projects?.completed ? `${projects.completed} réceptionné(s)` : `${projects?.total ?? 0} au total`}
              icon={HardHat}
            />
            <StatCard
              label="Budget sous gestion"
              value={projects?.budget_total_label ?? formatXaf(0, { compact: true })}
              hint={projects?.budget_spent_label ? `${projects.budget_spent_label} dépensés` : undefined}
              icon={Wallet}
            />
            <StatCard
              label="Propriétés"
              value={String(properties?.total ?? 0)}
              hint={
                properties?.portfolio_value_label && properties.total
                  ? `Valeur estimée ${properties.portfolio_value_label}`
                  : undefined
              }
              icon={Building2}
            />
            <StatCard
              label="Avancement moyen"
              value={`${clampPercent(projects?.budget_used_percent ?? 0)} %`}
              hint={evidences?.published ? `${evidences.published} preuves publiées` : undefined}
              icon={TrendingUp}
            />
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
          {/* Projets */}
          <section className="rounded-k-lg border border-k-line bg-white p-5">
            <div className="flex items-center justify-between gap-4">
              <h2 className="text-[1.125rem]">Mes projets</h2>
              <Link
                to="/espace/demandes"
                className="inline-flex items-center gap-1.5 text-[0.8125rem] font-medium text-k-blue hover:text-k-green-dark"
              >
                Mes demandes
                <ArrowRight className="size-3.5" aria-hidden />
              </Link>
            </div>

            {dashboard.isLoading ? (
              <div className="mt-5 space-y-4">
                {Array.from({ length: 2 }).map((_, index) => (
                  <CardSkeleton key={index} lines={3} />
                ))}
              </div>
            ) : projectList.length === 0 ? (
              <div className="mt-5">
                <EmptyState
                  icon={<HardHat className="size-5" aria-hidden />}
                  title="Aucun projet suivi pour le moment"
                  description="Dès qu'une demande est qualifiée par KEMTA, votre projet apparaît ici avec son avancement, son budget et ses preuves terrain."
                  action={<ButtonLink to="/demande" size="sm">Déposer une demande</ButtonLink>}
                />
              </div>
            ) : (
              <ul className="mt-5 space-y-4">
                {projectList.slice(0, 4).map((project) => (
                  <li key={project.id} className="rounded-k border border-k-line p-4 transition-colors hover:border-k-blue-line">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <Link
                          to={`/espace/projets/${project.id}`}
                          className="font-display text-[1rem] font-semibold text-k-ink hover:text-k-blue"
                        >
                          {project.name}
                        </Link>
                        <p className="mt-1 text-[0.75rem] text-k-muted">
                          {project.reference} · {project.display_location || 'Localisation à préciser'}
                        </p>
                      </div>
                      <StatusBadge code={project.status} label={project.status_label} />
                    </div>

                    <div className="mt-4 h-2 overflow-hidden rounded-full bg-k-line">
                      <div
                        className={`h-full rounded-full ${project.health === 'AT_RISK' ? 'bg-k-amber' : 'bg-k-green'}`}
                        style={{ width: `${clampPercent(project.progress_percent)}%` }}
                      />
                    </div>

                    <dl className="mt-3 grid grid-cols-2 gap-3 text-[0.75rem] sm:grid-cols-4">
                      <div>
                        <dt className="text-k-muted">Avancement</dt>
                        <dd className="font-medium text-k-ink">{clampPercent(project.progress_percent)} %</dd>
                      </div>
                      <div>
                        <dt className="text-k-muted">Budget</dt>
                        <dd className="font-medium text-k-ink">{project.budget_label || '—'}</dd>
                      </div>
                      <div>
                        <dt className="text-k-muted">Consommé</dt>
                        <dd className="font-medium text-k-ink">{clampPercent(project.budget_used_percent)} %</dd>
                      </div>
                      <div>
                        <dt className="text-k-muted">Réception prévue</dt>
                        <dd className="font-medium text-k-ink">
                          {project.planned_end ? formatDate(project.planned_end) : '—'}
                        </dd>
                      </div>
                    </dl>

                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <Badge tone="outline" size="sm">
                        {project.kind_label}
                      </Badge>
                      <Badge tone={project.health === 'AT_RISK' ? 'amber' : 'green'} size="sm">
                        {project.health_label}
                      </Badge>
                      {project.is_late ? (
                        <Badge tone="red" size="sm">
                          Retard signalé
                        </Badge>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* Colonne latérale */}
          <div className="space-y-6">
            {actions.length ? (
              <section className="rounded-k-lg border border-k-blue-line bg-k-blue-soft/60 p-5">
                <h2 className="text-[1.0625rem]">À faire de votre côté</h2>
                <ul className="mt-4 space-y-3">
                  {actions.map((action) => (
                    <li key={action.key} className="flex items-start gap-2.5">
                      <span
                        className={`mt-1.5 size-1.5 shrink-0 rounded-full ${
                          action.kind === 'warning' ? 'bg-k-amber' : 'bg-k-blue'
                        }`}
                        aria-hidden
                      />
                      <Link to={action.url} className="text-[0.875rem] text-k-ink hover:text-k-blue">
                        {action.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            <section className="rounded-k-lg border border-k-line bg-white p-5">
              <h2 className="flex items-center gap-2 text-[1.0625rem]">
                <Bell className="size-4 text-k-blue" aria-hidden />
                Notifications
              </h2>
              {notifications.length === 0 ? (
                <p className="mt-3 text-[0.875rem] text-k-muted">Aucune notification pour le moment.</p>
              ) : (
                <ul className="mt-4 space-y-3.5">
                  {notifications.map((item) => (
                    <li key={item.id} className="flex gap-3">
                      <span
                        className={`mt-1.5 size-1.5 shrink-0 rounded-full ${item.is_read ? 'bg-k-line' : 'bg-k-green'}`}
                        aria-hidden
                      />
                      <div className="min-w-0">
                        <p className="text-[0.875rem] font-medium text-k-ink">{item.title}</p>
                        <p className="mt-0.5 line-clamp-2 text-[0.8125rem] leading-relaxed text-k-muted">{item.body}</p>
                        <p className="mt-0.5 text-[0.6875rem] text-k-muted">
                          {item.age_label ?? relativeTime(item.created_at)}
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="rounded-k-lg border border-k-line bg-white p-5">
              <h2 className="flex items-center gap-2 text-[1.0625rem]">
                <CalendarCheck className="size-4 text-k-green" aria-hidden />
                Prochaines visites
              </h2>
              {visits.length === 0 ? (
                <p className="mt-3 text-[0.875rem] text-k-muted">
                  Aucune visite planifiée. Votre chargé de suivi vous prévient dès qu&apos;une date est fixée.
                </p>
              ) : (
                <ul className="mt-4 space-y-3">
                  {visits.map((visit) => (
                    <li key={visit.id} className="rounded-k bg-k-mist px-3.5 py-2.5">
                      <p className="text-[0.875rem] font-medium text-k-ink">{visit.title}</p>
                      <p className="mt-0.5 text-[0.75rem] text-k-muted">
                        {formatDate(visit.scheduled_for)}
                        {visit.property_name ? ` · ${visit.property_name}` : ''}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {latestEvidences.length ? (
              <section className="rounded-k-lg border border-k-line bg-white p-5">
                <h2 className="flex items-center gap-2 text-[1.0625rem]">
                  <Camera className="size-4 text-k-blue" aria-hidden />
                  Dernières preuves
                </h2>
                <ul className="mt-4 grid grid-cols-2 gap-3">
                  {latestEvidences.map((evidence) => (
                    <li key={evidence.id} className="overflow-hidden rounded-k border border-k-line">
                      {evidence.thumbnail_url ? (
                        <img
                          src={evidence.thumbnail_url}
                          alt={evidence.title}
                          loading="lazy"
                          className="h-24 w-full object-cover"
                        />
                      ) : (
                        <span className="flex h-24 items-center justify-center bg-k-mist text-k-muted" aria-hidden>
                          <Camera className="size-4" />
                        </span>
                      )}
                      <div className="p-2.5">
                        <p className="truncate text-[0.75rem] font-medium text-k-ink">{evidence.title}</p>
                        <p className="mt-0.5 text-[0.6875rem] text-k-muted">
                          {evidence.project_name ? `${evidence.project_name} · ` : ''}
                          {relativeTime(evidence.captured_at)}
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
          </div>
        </div>

        {/* Demandes récentes */}
        <section className="rounded-k-lg border border-k-line bg-white p-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <h2 className="flex items-center gap-2 text-[1.125rem]">
              <FileText className="size-4 text-k-blue" aria-hidden />
              Mes demandes
            </h2>
            <ButtonLink to="/espace/demandes" variant="secondary" size="sm">
              Toutes mes demandes
            </ButtonLink>
          </div>

          {requests.isLoading ? (
            <div className="mt-5 space-y-3">
              {Array.from({ length: 2 }).map((_, index) => (
                <CardSkeleton key={index} lines={2} />
              ))}
            </div>
          ) : requestList.length === 0 ? (
            <p className="mt-4 text-[0.875rem] text-k-muted">
              Vous n&apos;avez pas encore déposé de demande depuis ce compte. Les demandes envoyées sans compte
              peuvent être rattachées sur simple demande à notre équipe.
            </p>
          ) : (
            <div className="mt-5 overflow-x-auto">
              <table className="w-full min-w-[40rem] border-collapse text-left">
                <thead>
                  <tr className="border-b border-k-line">
                    <th scope="col" className="py-2.5 pr-4 text-[0.75rem] font-semibold uppercase tracking-wide text-k-muted">
                      Référence
                    </th>
                    <th scope="col" className="py-2.5 pr-4 text-[0.75rem] font-semibold uppercase tracking-wide text-k-muted">
                      Service
                    </th>
                    <th scope="col" className="py-2.5 pr-4 text-[0.75rem] font-semibold uppercase tracking-wide text-k-muted">
                      Localisation
                    </th>
                    <th scope="col" className="py-2.5 pr-4 text-[0.75rem] font-semibold uppercase tracking-wide text-k-muted">
                      Statut
                    </th>
                    <th scope="col" className="py-2.5 text-[0.75rem] font-semibold uppercase tracking-wide text-k-muted">
                      Déposée le
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-k-line">
                  {requestList.map((request) => (
                    <tr key={request.id}>
                      <td className="py-3 pr-4 text-[0.8125rem] font-medium text-k-blue">{request.reference}</td>
                      <td className="py-3 pr-4 text-[0.8125rem] text-k-ink">{request.kind_label}</td>
                      <td className="py-3 pr-4 text-[0.8125rem] text-k-muted">
                        {request.display_location || '—'}
                      </td>
                      <td className="py-3 pr-4">
                        <StatusBadge code={request.status} label={request.status_label} />
                      </td>
                      <td className="py-3 text-[0.8125rem] text-k-muted">{formatDate(request.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </>
  );
}
