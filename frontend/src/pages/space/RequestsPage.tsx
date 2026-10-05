import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, ArrowRight, FileText, HelpCircle, Plus } from 'lucide-react';

import { http } from '@/lib/api';
import { Seo } from '@/components/Seo';
import { Alert, CardSkeleton, EmptyState, ErrorState } from '@/components/ui/Feedback';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { Button, ButtonLink } from '@/components/ui/Button';
import { useMyRequests } from '@/lib/hooks';
import { formatDate, formatXaf, relativeTime } from '@/lib/format';
import { qk } from '@/lib/query';
import type { ServiceRequestDetail } from '@/lib/types';

export default function RequestsPage() {
  const { data, isLoading, isError, refetch } = useMyRequests();
  const [selected, setSelected] = useState<string | null>(null);

  const detail = useQuery<ServiceRequestDetail>({
    queryKey: [...qk.myRequests(), selected],
    enabled: Boolean(selected),
    queryFn: () => http.get<ServiceRequestDetail>(`/requests/mine/${selected}/`),
  });

  const requests = data?.results ?? [];

  if (selected) {
    return (
      <>
        <Seo
          title={`Demande ${selected}`}
          description="Détail de votre demande de service KEMTA : statut, historique des échanges et prochaines étapes."
          path={`/espace/demandes/${selected}`}
          noIndex
        />

        <div className="flex flex-col gap-6">
          <button
            type="button"
            onClick={() => setSelected(null)}
            className="inline-flex w-fit items-center gap-1.5 text-[0.8125rem] text-k-muted transition-colors hover:text-k-blue"
          >
            <ArrowLeft className="size-3.5" aria-hidden />
            Retour à mes demandes
          </button>

          {detail.isLoading ? (
            <CardSkeleton lines={6} />
          ) : detail.isError || !detail.data ? (
            <ErrorState
              message="Cette demande n'a pas pu être chargée. Elle appartient peut-être à un autre compte."
              onRetry={() => void detail.refetch()}
            />
          ) : (
            <>
              <header className="rounded-k-lg border border-k-line bg-white p-5 sm:p-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-display text-[1.25rem] font-bold text-k-blue">{detail.data.reference}</p>
                    <p className="mt-1 text-[0.875rem] text-k-muted">
                      {detail.data.kind_label} · déposée le {formatDate(detail.data.created_at)}
                    </p>
                  </div>
                  <StatusBadge code={detail.data.status} label={detail.data.status_label} />
                </div>

                <dl className="mt-5 grid gap-4 border-t border-k-line pt-5 sm:grid-cols-3">
                  <div>
                    <dt className="text-[0.75rem] uppercase tracking-wide text-k-muted">Localisation</dt>
                    <dd className="mt-0.5 text-[0.875rem] text-k-ink">
                      {detail.data.display_location || detail.data.location_text || '—'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[0.75rem] uppercase tracking-wide text-k-muted">Nature du projet</dt>
                    <dd className="mt-0.5 text-[0.875rem] text-k-ink">{detail.data.project_type || '—'}</dd>
                  </div>
                  <div>
                    <dt className="text-[0.75rem] uppercase tracking-wide text-k-muted">Budget annoncé</dt>
                    <dd className="mt-0.5 text-[0.875rem] text-k-ink">
                      {detail.data.budget_label ||
                        (detail.data.budget_max_xaf ? formatXaf(detail.data.budget_max_xaf) : 'Non précisé')}
                    </dd>
                  </div>
                </dl>

                {detail.data.assigned_to_name ? (
                  <p className="mt-4 text-[0.8125rem] text-k-muted">
                    Conseiller KEMTA en charge du dossier : <span className="text-k-ink">{detail.data.assigned_to_name}</span>
                  </p>
                ) : null}

                {detail.data.description ? (
                  <p className="mt-5 whitespace-pre-line border-t border-k-line pt-5 text-[0.875rem] leading-relaxed text-k-muted">
                    {detail.data.description}
                  </p>
                ) : null}

                {detail.data.converted_project_reference ? (
                  <Alert tone="success" className="mt-5" title="Votre projet est ouvert">
                    Un projet suivi a été créé à partir de cette demande : {detail.data.converted_project_reference}.
                    Retrouvez son avancement dans la vue d&apos;ensemble.
                    <div className="mt-3">
                      <ButtonLink to="/espace" size="sm">
                        Voir mes projets
                      </ButtonLink>
                    </div>
                  </Alert>
                ) : null}
              </header>

              <section className="rounded-k-lg border border-k-line bg-white p-5 sm:p-6">
                <h2 className="text-[1.125rem]">Suivi du dossier</h2>

                {detail.data.next_step_label ? (
                  <p className="mt-3 rounded-k bg-k-blue-soft/70 px-4 py-3 text-[0.875rem] text-k-ink">
                    Prochaine étape : {detail.data.next_step_label}
                  </p>
                ) : null}

                {detail.data.events.length ? (
                  <ol className="mt-5 space-y-4">
                    {detail.data.events
                      .filter((event) => event.is_customer_visible)
                      .map((event) => (
                        <li key={event.id} className="relative border-l border-k-line pl-4">
                          <span className="absolute -left-[5px] top-1.5 size-2.5 rounded-full bg-k-green" aria-hidden />
                          <div className="flex flex-wrap items-center gap-2">
                            <StatusBadge code={event.to_status} label={event.to_status_label} />
                            <span className="text-[0.75rem] text-k-muted">{formatDate(event.created_at)}</span>
                          </div>
                          {event.comment ? (
                            <p className="mt-1.5 text-[0.875rem] leading-relaxed text-k-ink">{event.comment}</p>
                          ) : null}
                          {event.actor_name ? (
                            <p className="mt-0.5 text-[0.6875rem] text-k-muted">par {event.actor_name}</p>
                          ) : null}
                        </li>
                      ))}
                  </ol>
                ) : (
                  <p className="mt-4 text-[0.875rem] text-k-muted">
                    Aucun événement publié pour le moment. Un conseiller vous contacte sous 48 heures ouvrées.
                  </p>
                )}
              </section>
            </>
          )}
        </div>
      </>
    );
  }

  return (
    <>
      <Seo
        title="Mes demandes"
        description="Retrouvez toutes vos demandes de service KEMTA, leur statut et l'historique de leur traitement."
        path="/espace/demandes"
        noIndex
      />

      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-[1.75rem]">Mes demandes</h1>
            <p className="mt-1.5 text-[0.9375rem] text-k-muted">
              Chaque demande déposée sur KEMTA apparaît ici avec sa référence, que vous pouvez citer lors de nos
              échanges.
            </p>
          </div>
          <ButtonLink to="/demande" size="sm" icon={<Plus className="size-4" aria-hidden />}>
            Nouvelle demande
          </ButtonLink>
        </header>

        {isError ? (
          <ErrorState message="Vos demandes n'ont pas pu être chargées." onRetry={() => void refetch()} />
        ) : isLoading ? (
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, index) => (
              <CardSkeleton key={index} lines={3} />
            ))}
          </div>
        ) : requests.length === 0 ? (
          <EmptyState
            icon={<FileText className="size-5" aria-hidden />}
            title="Aucune demande enregistrée"
            description="Déposez une demande pour faire construire, suivre un chantier existant ou entretenir un bien : un conseiller vous rappelle sous 48 heures ouvrées."
            action={<ButtonLink to="/demande">Déposer une demande</ButtonLink>}
          />
        ) : (
          <ul className="space-y-4">
            {requests.map((request) => (
              <li key={request.id} className="rounded-k-lg border border-k-line bg-white p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-display text-[1rem] font-semibold text-k-ink">{request.reference}</p>
                    <p className="mt-1 text-[0.8125rem] text-k-muted">
                      {request.kind_label} · {request.display_location || 'Localisation à préciser'} ·{' '}
                      {formatDate(request.created_at)}
                    </p>
                    {request.next_step_label ? (
                      <p className="mt-2 text-[0.8125rem] text-k-ink">
                        <span className="text-k-muted">Étape en cours :</span> {request.next_step_label}
                      </p>
                    ) : null}
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <StatusBadge code={request.status} label={request.status_label} />
                    {request.budget_label ? (
                      <span className="text-[0.75rem] text-k-muted">{request.budget_label}</span>
                    ) : null}
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <Button variant="secondary" size="sm" onClick={() => setSelected(request.reference)}>
                    Voir le dossier
                  </Button>
                  <span className="inline-flex items-center gap-1.5 text-[0.75rem] text-k-muted">
                    <HelpCircle className="size-3.5" aria-hidden />
                    Mise à jour {relativeTime(request.created_at)}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}

        <p className="flex items-center gap-1.5 text-[0.75rem] text-k-muted">
          <ArrowRight className="size-3.5 shrink-0" aria-hidden />
          Une demande déposée sans compte n&apos;est pas rattachée automatiquement :{' '}
          <Link to="/contact" className="font-medium text-k-blue hover:text-k-green-dark">
            écrivez-nous
          </Link>{' '}
          avec votre référence pour l&apos;ajouter à cet espace.
        </p>

        {requests.length ? (
          <p className="text-[0.75rem] text-k-muted">
            {requests.length} demande{requests.length > 1 ? 's' : ''} affichée{requests.length > 1 ? 's' : ''}
            {data?.count && data.count > requests.length ? ` sur ${data.count}` : ''}.{' '}
            {requests.some((request) => request.status === 'NEW')
              ? 'Une demande est en attente de qualification par un conseiller.'
              : 'Tous vos dossiers ont été qualifiés.'}
          </p>
        ) : null}

        <div className="rounded-k-lg border border-k-blue-line bg-k-blue-soft/60 p-5">
          <p className="flex items-center gap-2 font-medium text-k-ink">
            <Badge tone="blue" size="sm">
              Astuce
            </Badge>
            Suivre un chantier déjà démarré
          </p>
          <p className="mt-2 text-[0.875rem] text-k-muted">
            KEMTA peut reprendre le suivi d&apos;un chantier confié à une autre entreprise : contrôle des quantités,
            vérification des dépenses, preuves photo et rapports hebdomadaires.
          </p>
          <div className="mt-3">
            <ButtonLink to="/services/suivi-chantier" variant="secondary" size="sm">
              Découvrir le suivi de chantier
            </ButtonLink>
          </div>
        </div>
      </div>
    </>
  );
}
