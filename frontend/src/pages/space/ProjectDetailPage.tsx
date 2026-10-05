import { Link, useParams } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowLeft,
  CalendarClock,
  Camera,
  CheckCircle2,
  Clock,
  FileText,
  HardHat,
  MapPin,
  MessageSquare,
  UserRound,
  Wallet,
} from 'lucide-react';

import { Seo } from '@/components/Seo';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { Alert, CardSkeleton, EmptyState, ErrorState } from '@/components/ui/Feedback';
import { ButtonLink } from '@/components/ui/Button';
import { useProject, useProjectTimeline } from '@/lib/hooks';
import { clampPercent, formatDate, formatDateTime, relativeTime } from '@/lib/format';

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const project = useProject(id);
  const timeline = useProjectTimeline(id);

  if (project.isError) {
    return (
      <ErrorState
        message="Ce projet est introuvable ou vous n'y avez pas accès. Vérifiez que vous êtes bien connecté au compte ayant déposé la demande."
        onRetry={() => void project.refetch()}
      />
    );
  }

  if (project.isLoading || !project.data) {
    return (
      <div className="space-y-6">
        <CardSkeleton lines={3} />
        <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
          <CardSkeleton lines={8} />
          <CardSkeleton lines={6} />
        </div>
      </div>
    );
  }

  const data = project.data;
  const metrics = data.metrics;
  const progress = clampPercent(Number(data.physical_progress));
  const updates = timeline.data ?? [];
  const evidenceShots = updates
    .map((update) => {
      const payload = (update.payload ?? {}) as Record<string, unknown>;
      return {
        id: update.id,
        url: typeof payload.thumbnail_url === 'string' ? payload.thumbnail_url : null,
        message: update.message,
        created_at: update.created_at,
        type: update.type_label,
      };
    })
    .filter((item) => item.url);

  return (
    <>
      <Seo
        title={`${data.name} — suivi de projet`}
        description={`Suivi du projet ${data.reference} : avancement, phases, budget, preuves terrain et journal de chantier.`}
        path={`/espace/projets/${id ?? ''}`}
        noIndex
      />

      <div className="flex flex-col gap-6">
        <div>
          <Link
            to="/espace"
            className="inline-flex items-center gap-1.5 text-[0.8125rem] text-k-muted transition-colors hover:text-k-blue"
          >
            <ArrowLeft className="size-3.5" aria-hidden />
            Retour à mon espace
          </Link>

          <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2.5">
                <StatusBadge code={data.status} label={data.status_label} />
                <Badge tone="outline">{data.kind_label}</Badge>
                <Badge tone={data.health === 'AT_RISK' ? 'amber' : 'green'}>{data.health_label}</Badge>
              </div>
              <h1 className="mt-3 text-[1.75rem]">{data.name}</h1>
              <p className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-[0.875rem] text-k-muted">
                <span className="inline-flex items-center gap-1.5">
                  <FileText className="size-3.5" aria-hidden />
                  {data.reference}
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <MapPin className="size-3.5" aria-hidden />
                  {data.display_location || 'Localisation à préciser'}
                </span>
                {data.manager ? (
                  <span className="inline-flex items-center gap-1.5">
                    <UserRound className="size-3.5" aria-hidden />
                    Chargé de suivi : {data.manager.name}
                  </span>
                ) : null}
              </p>
            </div>
            <ButtonLink to="/contact" variant="secondary" size="sm" icon={<MessageSquare className="size-4" aria-hidden />}>
              Poser une question
            </ButtonLink>
          </div>
        </div>

        {data.health_notes ? (
          <Alert tone={data.health === 'AT_RISK' ? 'warning' : 'info'} title="Note de suivi">
            {data.health_notes}
          </Alert>
        ) : null}

        {/* Indicateurs */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-k-lg border border-k-line bg-white p-5">
            <p className="text-[0.75rem] uppercase tracking-wide text-k-muted">Avancement du chantier</p>
            <p className="mt-1 font-display text-[1.75rem] font-bold text-k-ink">{progress} %</p>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-k-line">
              <div className="h-full rounded-full bg-k-green" style={{ width: `${progress}%` }} />
            </div>
            <p className="mt-2 text-[0.75rem] text-k-muted">
              {metrics.phases_done}/{metrics.phases_count} phases terminées
              {metrics.days_to_deadline !== null ? ` · ${metrics.days_to_deadline} jours avant échéance` : ''}
            </p>
          </div>

          <div className="rounded-k-lg border border-k-line bg-white p-5">
            <p className="text-[0.75rem] uppercase tracking-wide text-k-muted">Budget du projet</p>
            <p className="mt-1 font-display text-[1.25rem] font-bold text-k-ink">{data.budget_total_label}</p>
            <p className="mt-1 text-[0.75rem] text-k-muted">
              Contrat {data.contract_signed ? 'signé' : 'en attente de signature'}
            </p>
          </div>

          <div className="rounded-k-lg border border-k-line bg-white p-5">
            <p className="text-[0.75rem] uppercase tracking-wide text-k-muted">Dépensé &amp; justifié</p>
            <p className="mt-1 font-display text-[1.25rem] font-bold text-k-ink">{data.budget_spent_label}</p>
            <p className="mt-1 text-[0.75rem] text-k-muted">
              {clampPercent(data.budget_used_percent)} % du budget · reste {data.budget_remaining_label}
            </p>
          </div>

          <div className="rounded-k-lg border border-k-line bg-white p-5">
            <p className="text-[0.75rem] uppercase tracking-wide text-k-muted">Prochaine visite KEMTA</p>
            <p className="mt-1 font-display text-[1.0625rem] font-semibold text-k-ink">
              {data.next_visit_at ? formatDate(data.next_visit_at) : 'À planifier'}
            </p>
            <p className="mt-1 text-[0.75rem] text-k-muted">
              {data.planned_end ? `Réception prévue le ${formatDate(data.planned_end)}` : 'Calendrier en validation'}
            </p>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
          {/* Phases */}
          <section className="rounded-k-lg border border-k-line bg-white p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-[1.125rem]">Phases du chantier</h2>
              {metrics.phases_blocked ? (
                <Badge tone="amber" size="sm">
                  <AlertTriangle className="size-3" aria-hidden />
                  {metrics.phases_blocked} phase(s) bloquée(s)
                </Badge>
              ) : null}
            </div>

            {data.phases.length === 0 ? (
              <div className="mt-5">
                <EmptyState
                  icon={<Clock className="size-5" aria-hidden />}
                  title="Les phases seront définies au démarrage"
                  description="Votre chargé de suivi met en place le découpage du chantier dès la validation du calendrier."
                />
              </div>
            ) : (
              <ol className="mt-5 space-y-5">
                {data.phases.map((phase) => {
                  const phaseProgress = clampPercent(Number(phase.progress_percent));
                  const done = phase.status === 'COMPLETED';
                  return (
                    <li key={phase.id} className="flex gap-4">
                      <span
                        className={`mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full text-[0.6875rem] font-semibold ${
                          done ? 'bg-k-green text-white' : 'bg-k-blue-soft text-k-blue'
                        }`}
                        aria-hidden
                      >
                        {done ? <CheckCircle2 className="size-4" /> : phase.order + 1}
                      </span>
                      <div className="min-w-0 flex-1 border-b border-k-line pb-4">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <p className="font-display text-[0.9375rem] font-semibold text-k-ink">{phase.name}</p>
                          <StatusBadge code={phase.status} label={phase.status_label} />
                        </div>

                        <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-k-line">
                          <div
                            className={`h-full rounded-full ${done ? 'bg-k-green' : phase.is_overdue ? 'bg-k-amber' : 'bg-k-blue'}`}
                            style={{ width: `${phaseProgress}%` }}
                          />
                        </div>

                        <p className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[0.75rem] text-k-muted">
                          <span>{phaseProgress} % · poids {Number(phase.weight_percent)} %</span>
                          {phase.planned_start ? (
                            <span className="inline-flex items-center gap-1">
                              <CalendarClock className="size-3" aria-hidden />
                              {formatDate(phase.planned_start)}
                              {phase.planned_end ? ` → ${formatDate(phase.planned_end)}` : ''}
                            </span>
                          ) : null}
                          {phase.responsible ? <span>Responsable : {phase.responsible.name}</span> : null}
                          {phase.evidences_count ? <span>{phase.evidences_count} preuve(s)</span> : null}
                        </p>

                        {phase.blocked_reason ? (
                          <p className="mt-2 rounded-k bg-k-amber-pale px-3 py-2 text-[0.75rem] text-k-ink">
                            Point de blocage : {phase.blocked_reason}
                          </p>
                        ) : null}
                      </div>
                    </li>
                  );
                })}
              </ol>
            )}
          </section>

          {/* Journal */}
          <section className="rounded-k-lg border border-k-line bg-white p-5">
            <h2 className="flex items-center gap-2 text-[1.125rem]">
              <MessageSquare className="size-4 text-k-blue" aria-hidden />
              Journal du chantier
            </h2>

            {timeline.isLoading ? (
              <div className="mt-5 space-y-3">
                {Array.from({ length: 3 }).map((_, index) => (
                  <CardSkeleton key={index} lines={2} />
                ))}
              </div>
            ) : updates.length === 0 ? (
              <p className="mt-4 text-[0.875rem] text-k-muted">Aucune mise à jour publiée pour l&apos;instant.</p>
            ) : (
              <ol className="mt-5 space-y-4">
                {updates.slice(0, 12).map((update) => (
                  <li key={update.id} className="relative border-l border-k-line pl-4">
                    <span
                      className={`absolute -left-[5px] top-1.5 size-2.5 rounded-full ${
                        update.update_type === 'INCIDENT'
                          ? 'bg-k-red'
                          : update.update_type === 'EVIDENCE'
                            ? 'bg-k-green'
                            : 'bg-k-blue'
                      }`}
                      aria-hidden
                    />
                    <p className="text-[0.75rem] uppercase tracking-wide text-k-muted">{update.type_label}</p>
                    <p className="mt-1 text-[0.875rem] leading-relaxed text-k-ink">{update.message}</p>
                    <p className="mt-1 flex items-center gap-2 text-[0.6875rem] text-k-muted">
                      <Clock className="size-3" aria-hidden />
                      {relativeTime(update.created_at)}
                      {update.author_name ? ` · ${update.author_name}` : ''}
                    </p>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </div>

        {/* Preuves terrain */}
        <section className="rounded-k-lg border border-k-line bg-white p-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <h2 className="flex items-center gap-2 text-[1.125rem]">
              <Camera className="size-4 text-k-green" aria-hidden />
              Preuves terrain
            </h2>
            <p className="text-[0.8125rem] text-k-muted">
              Photos horodatées publiées par les techniciens KEMTA et validées par le contrôle qualité.
            </p>
          </div>

          {evidenceShots.length === 0 ? (
            <div className="mt-5">
              <EmptyState
                icon={<Camera className="size-5" aria-hidden />}
                title="Les prochaines preuves arriveront ici"
                description="À chaque visite, le technicien photographie le chantier : vous recevez une notification et retrouvez les photos dans ce dossier."
              />
            </div>
          ) : (
            <ul className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {evidenceShots.slice(0, 8).map((shot) => (
                <li key={shot.id} className="overflow-hidden rounded-k border border-k-line">
                  <img src={shot.url ?? ''} alt="" loading="lazy" className="h-36 w-full object-cover" />
                  <div className="p-3">
                    <p className="text-[0.75rem] font-medium text-k-ink">{shot.type}</p>
                    <p className="mt-0.5 line-clamp-2 text-[0.75rem] text-k-muted">{shot.message}</p>
                    <p className="mt-1 text-[0.6875rem] text-k-muted">{relativeTime(shot.created_at)}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <div className="flex flex-wrap gap-3">
          <ButtonLink to="/contact" variant="secondary" icon={<MessageSquare className="size-4" aria-hidden />}>
            Contacter mon chargé de suivi
          </ButtonLink>
          <ButtonLink to="/services/suivi-chantier" variant="ghost" icon={<Wallet className="size-4" aria-hidden />}>
            Comprendre le contrôle budgétaire
          </ButtonLink>
          <ButtonLink to="/comment-ca-marche" variant="ghost" icon={<HardHat className="size-4" aria-hidden />}>
            Comment KEMTA travaille
          </ButtonLink>
        </div>

        <p className="text-[0.75rem] text-k-muted">
          Dernière mise à jour du dossier : {formatDateTime(data.updated_at)} · Budget en {data.currency === 'XAF' ? 'francs CFA' : data.currency}
          {data.request_reference ? ` · Demande d'origine ${data.request_reference}` : ''}
        </p>
      </div>
    </>
  );
}
