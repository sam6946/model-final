import { Link } from 'react-router-dom';
import { ArrowRight, BadgeCheck, Building2, MapPin, Star, Users } from 'lucide-react';

import { Section, SectionHeading } from '@/components/layout/Section';
import { Badge } from '@/components/ui/Badge';
import { ButtonLink } from '@/components/ui/Button';
import { CardSkeleton, ErrorState, EmptyState, Skeleton } from '@/components/ui/Feedback';
import { Media } from '@/components/ui/Media';
import { CompanyTile, RealizationTile } from '@/components/ecosystem/Cards';
import { useCompanies, useOpportunities, useRealizations } from '@/lib/hooks';
import { ECOSYSTEM_PROMISES } from '@/lib/content';
import { formatDate, formatXaf } from '@/lib/format';
import { useReveal } from '@/hooks/useReveal';

/* ------------------------------------------------------------- entreprises */

export function Companies() {
  const ref = useReveal<HTMLDivElement>();
  const { data, isLoading, isError, refetch } = useCompanies({ page_size: 4, ordering: '-is_featured' });
  const companies = data?.results ?? [];

  return (
    <Section id="entreprises" tone="mist">
      <SectionHeading
        eyebrow="Entreprises BTP"
        title="Des entreprises dont le dossier a été contrôlé"
        description="Registre de commerce, attestation fiscale, CNPS, assurances et références de chantier : le badge KEMTA se mérite et se retire en cas de manquement grave."
        action={
          <ButtonLink to="/entreprises-btp" variant="secondary" size="sm">
            Explorer l&apos;annuaire
          </ButtonLink>
        }
      />

      <div ref={ref} data-reveal className="mt-12 grid gap-x-8 gap-y-10 lg:grid-cols-[1.05fr_1fr] lg:gap-14">
        <div className="grid gap-5 sm:grid-cols-2">
          {ECOSYSTEM_PROMISES.map((promise) => {
            const Icon = promise.icon;
            return (
              <div key={promise.title} className="rounded-k-lg border border-k-line bg-white p-5">
                <span className="flex size-9 items-center justify-center rounded-k bg-k-blue-soft text-k-blue" aria-hidden>
                  <Icon className="size-4" />
                </span>
                <h3 className="mt-4 text-[1rem] font-display font-semibold text-k-ink">{promise.title}</h3>
                <p className="mt-1.5 text-[0.875rem] leading-relaxed text-k-muted">{promise.description}</p>
              </div>
            );
          })}
        </div>

        <div>
          {isLoading ? (
            <div className="space-y-4">
              {Array.from({ length: 3 }).map((_, index) => (
                <CardSkeleton key={index} lines={2} />
              ))}
            </div>
          ) : isError ? (
            <ErrorState message="L'annuaire n'a pas pu être chargé." onRetry={() => void refetch()} />
          ) : companies.length === 0 ? (
            <EmptyState
              icon={<Building2 className="size-5" aria-hidden />}
              title="Annuaire en cours de constitution"
              description="Les premières entreprises vérifiées apparaîtront ici dès validation de leur dossier."
            />
          ) : (
            <div className="space-y-4">
              {companies.map((company) => (
                <CompanyTile key={company.id} company={company} />
              ))}
              <Link
                to="/entreprises-btp"
                className="inline-flex items-center gap-1.5 text-[0.875rem] font-medium text-k-blue hover:text-k-green-dark"
              >
                Voir les {data?.count ?? companies.length} entreprises référencées
                <ArrowRight className="size-3.5" aria-hidden />
              </Link>
            </div>
          )}
        </div>
      </div>
    </Section>
  );
}

/* ---------------------------------------------------------------- catalogue */

export function Catalog() {
  const ref = useReveal<HTMLDivElement>();
  const { data, isLoading, isError, refetch } = useRealizations({ page_size: 3, ordering: '-is_featured' });
  const realizations = data?.results ?? [];

  return (
    <Section id="catalogue">
      <SectionHeading
        eyebrow="Catalogue professionnel"
        title="Des réalisations documentées, pas des promesses commerciales"
        description="Photos avant/après, surface, durée réelle et parfois budget : le catalogue KEMTA montre le travail livré par les entreprises du réseau."
        action={
          <ButtonLink to="/realisations" variant="secondary" size="sm">
            Parcourir le catalogue
          </ButtonLink>
        }
      />

      <div ref={ref} data-reveal className="mt-12">
        {isLoading ? (
          <div className="grid gap-6 md:grid-cols-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <div key={index} className="space-y-3">
                <Skeleton className="h-44 w-full" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
              </div>
            ))}
          </div>
        ) : isError ? (
          <ErrorState message="Le catalogue n'a pas pu être chargé." onRetry={() => void refetch()} />
        ) : realizations.length === 0 ? (
          <EmptyState
            title="Catalogue en préparation"
            description="Les réalisations publiées par les entreprises vérifiées apparaîtront ici."
          />
        ) : (
          <div className="grid gap-6 md:grid-cols-3">
            {realizations.map((item) => (
              <RealizationTile key={item.id} realization={item} />
            ))}
          </div>
        )}
      </div>
    </Section>
  );
}

/* ------------------------------------------------------------- opportunités */

export function Opportunities() {
  const ref = useReveal<HTMLDivElement>();
  const { data, isLoading, isError, refetch } = useOpportunities({ page_size: 3 });
  const items = data?.results ?? [];

  return (
    <Section id="opportunites" tone="mist">
      <div className="grid gap-12 lg:grid-cols-[1fr_1.05fr] lg:items-center lg:gap-16">
        <div ref={ref} data-reveal>
          <Badge tone="green">
            <Users className="size-3.5" aria-hidden />
            Espace entreprises
          </Badge>
          <h2 className="mt-5 text-[1.875rem] sm:text-[2.25rem]">
            Les marchés arrivent là où sont les entreprises sérieuses
          </h2>
          <p className="mt-4 text-[1.0625rem] leading-relaxed text-k-muted">
            KEMTA publie les appels d&apos;offres de ses clients — particuliers, investisseurs, institutions — et les
            réserve aux entreprises du réseau. Vous candidatez en ligne avec vos références, le client compare les
            dossiers et KEMTA instruit.
          </p>

          <ul className="mt-7 space-y-3 text-[0.9375rem] text-k-ink">
            <li className="flex items-start gap-2.5">
              <BadgeCheck className="mt-0.5 size-4 shrink-0 text-k-green" aria-hidden />
              Seules les entreprises vérifiées peuvent candidater aux marchés privés.
            </li>
            <li className="flex items-start gap-2.5">
              <BadgeCheck className="mt-0.5 size-4 shrink-0 text-k-green" aria-hidden />
              Chaque candidature reçoit une référence et un statut consultable.
            </li>
            <li className="flex items-start gap-2.5">
              <BadgeCheck className="mt-0.5 size-4 shrink-0 text-k-green" aria-hidden />
              Le dossier entreprise se crée une fois, puis sert à chaque candidature.
            </li>
          </ul>

          <div className="mt-8 flex flex-wrap gap-3">
            <ButtonLink to="/espace-entreprise" iconRight={<ArrowRight className="size-4" aria-hidden />}>
              Inscrire mon entreprise
            </ButtonLink>
            <ButtonLink to="/opportunites" variant="secondary">
              Voir les marchés ouverts
            </ButtonLink>
          </div>
        </div>

        <div data-reveal className="space-y-5">
          <Media
            name="marche-btp"
            alt="Dossiers d'appel d'offres, plans et devis BTP posés sur une table de travail"
            ratio="4 / 3"
            sizes="(min-width: 1024px) 46vw, 100vw"
          />

          {isLoading ? (
            <CardSkeleton lines={3} />
          ) : isError ? (
            <ErrorState message="Les marchés n'ont pas pu être chargés." onRetry={() => void refetch()} />
          ) : items.length === 0 ? (
            <EmptyState
              title="Aucun marché publié pour l'instant"
              description="Inscrivez votre entreprise : vous recevrez une alerte dès la publication d'un marché correspondant à votre profil."
            />
          ) : (
            <ul className="space-y-3">
              {items.map((item) => (
                <li key={item.id} className="rounded-k-lg border border-k-line bg-white p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <Link
                        to={`/opportunites/${item.slug}`}
                        className="font-display text-[1rem] font-semibold text-k-ink hover:text-k-blue"
                      >
                        {item.title}
                      </Link>
                      <p className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-[0.75rem] text-k-muted">
                        <span className="inline-flex items-center gap-1">
                          <MapPin className="size-3" aria-hidden />
                          {item.display_location}
                        </span>
                        <span>{item.property_type_label}</span>
                        {item.application_deadline ? (
                          <span>Clôture le {formatDate(item.application_deadline)}</span>
                        ) : null}
                      </p>
                    </div>
                    {item.is_open ? (
                      <Badge tone="green" size="sm">
                        Ouvert
                      </Badge>
                    ) : (
                      <Badge tone="neutral" size="sm">
                        Clôturé
                      </Badge>
                    )}
                  </div>

                  <p className="mt-3 text-[0.8125rem] text-k-muted">
                    Budget : {item.budget_visible && item.budget_label ? item.budget_label : 'communiqué aux candidats'}
                    {item.applications_count ? ` · ${item.applications_count} candidature(s)` : ''}
                  </p>
                </li>
              ))}
            </ul>
          )}

          <p className="flex flex-wrap items-center gap-x-5 gap-y-2 text-[0.75rem] text-k-muted">
            <span className="inline-flex items-center gap-1.5">
              <Star className="size-3.5" aria-hidden />
              {formatXaf(25000)} / mois pour l&apos;offre Pro · prix affichés dans l&apos;espace entreprise
            </span>
          </p>
        </div>
      </div>
    </Section>
  );
}
