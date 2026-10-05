import { Link } from 'react-router-dom';
import { ArrowRight, BadgeCheck, Building2, CalendarClock, MapPin, Ruler, Users } from 'lucide-react';

import { useCompanies, useOpportunities, useRealizations } from '@/lib/hooks';
import { Section, SectionHeading } from '@/components/layout/Section';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { ButtonLink } from '@/components/ui/Button';
import { CardSkeleton, EmptyState } from '@/components/ui/Feedback';
import { Media } from '@/components/ui/Media';
import { formatDate, formatXaf, initials, statusLabel } from '@/lib/format';
import { ECOSYSTEM_PROMISES } from '@/lib/content';

const API_ORIGIN = '';

function resolveMedia(url?: string | null): string | null {
  if (!url) return null;
  return url.startsWith('http') ? url : `${API_ORIGIN}${url}`;
}

function CompanyLogo({ name, url, size = 'md' }: { name: string; url?: string | null; size?: 'sm' | 'md' }) {
  const resolved = resolveMedia(url);
  const dimension = size === 'sm' ? 'size-10' : 'size-12';
  if (resolved) {
    return (
      <img
        src={resolved}
        alt={`Logo ${name}`}
        loading="lazy"
        className={`${dimension} shrink-0 rounded-k border border-k-line bg-white object-contain p-1`}
      />
    );
  }
  return (
    <span
      className={`${dimension} flex shrink-0 items-center justify-center rounded-k bg-k-blue-soft font-display text-sm font-bold text-k-blue`}
      aria-hidden
    >
      {initials(name)}
    </span>
  );
}

/* ------------------------------------------------------- entreprises BTP */

export function Companies() {
  const { data, isLoading, isError, refetch } = useCompanies({ page_size: 3, ordering: '-is_featured' });
  const companies = data?.results ?? [];

  return (
    <Section id="entreprises-btp">
      <SectionHeading
        eyebrow="Réseau d'entreprises BTP"
        title="Des entreprises dont le dossier a été contrôlé"
        description="Registre de commerce, attestation fiscale, CNPS, références de chantier : le badge « Vérifiée » n'est attribué qu'après examen par l'équipe KEMTA."
        action={
          <ButtonLink to="/entreprises-btp" variant="secondary" iconRight={<ArrowRight className="size-4" aria-hidden />}>
            Parcourir l&apos;annuaire
          </ButtonLink>
        }
      />

      <div className="mt-10 grid gap-6 md:grid-cols-3">
        {isLoading
          ? Array.from({ length: 3 }).map((_, index) => <CardSkeleton key={index} lines={4} />)
          : companies.map((company) => (
              <article
                key={company.id}
                className="group flex flex-col overflow-hidden rounded-k-lg border border-k-line bg-white transition-shadow duration-300 hover:shadow-k"
              >
                <Link to={`/entreprises/${company.slug}`} className="block">
                  <div className="relative h-36 overflow-hidden bg-k-blue-soft">
                    {resolveMedia(company.cover_url) ? (
                      <img
                        src={resolveMedia(company.cover_url) ?? ''}
                        alt={`${company.name} — chantier`}
                        loading="lazy"
                        className="size-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
                      />
                    ) : (
                      <div className="k-grid-lines size-full bg-k-blue" aria-hidden />
                    )}
                    {company.is_verified ? (
                      <span className="absolute left-3 top-3 inline-flex items-center gap-1 rounded-full bg-white/95 px-2.5 py-1 text-[0.6875rem] font-medium text-k-green-dark">
                        <BadgeCheck className="size-3" aria-hidden />
                        Vérifiée
                      </span>
                    ) : null}
                  </div>
                </Link>

                <div className="flex flex-1 flex-col p-5">
                  <div className="flex items-start gap-3">
                    <CompanyLogo name={company.name} url={company.logo_url} size="sm" />
                    <div className="min-w-0">
                      <h3 className="truncate text-[1rem]">
                        <Link to={`/entreprises/${company.slug}`} className="hover:text-k-blue">
                          {company.name}
                        </Link>
                      </h3>
                      <p className="mt-0.5 flex items-center gap-1 text-[0.75rem] text-k-muted">
                        <MapPin className="size-3" aria-hidden />
                        {company.city}
                        {company.intervention_label ? ` · ${company.intervention_label}` : ''}
                      </p>
                    </div>
                  </div>

                  <p className="mt-3 line-clamp-2 text-[0.875rem] leading-relaxed text-k-muted">
                    {company.description}
                  </p>

                  <ul className="mt-4 flex flex-wrap gap-1.5">
                    {(company.specialities ?? []).slice(0, 3).map((specialty) => (
                      <li key={specialty.code}>
                        <Badge tone="outline" size="sm">
                          {specialty.name}
                        </Badge>
                      </li>
                    ))}
                  </ul>

                  <dl className="mt-5 grid grid-cols-3 gap-2 border-t border-k-line pt-4 text-center">
                    <div>
                      <dt className="text-[0.625rem] uppercase tracking-wide text-k-muted">Chantiers</dt>
                      <dd className="font-display text-[0.9375rem] font-semibold text-k-ink">{company.projects_count}</dd>
                    </div>
                    <div>
                      <dt className="text-[0.625rem] uppercase tracking-wide text-k-muted">Expérience</dt>
                      <dd className="font-display text-[0.9375rem] font-semibold text-k-ink">
                        {company.years_experience} ans
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[0.625rem] uppercase tracking-wide text-k-muted">Équipe</dt>
                      <dd className="font-display text-[0.9375rem] font-semibold text-k-ink">
                        {company.employees_count}
                      </dd>
                    </div>
                  </dl>
                </div>
              </article>
            ))}
      </div>

      {!isLoading && isError ? (
        <div className="mt-6">
          <EmptyState
            title="L'annuaire n'a pas pu être chargé"
            description="Vérifiez votre connexion puis réessayez : les profils d'entreprises sont servis depuis nos serveurs."
            action={
              <ButtonLink to="/entreprises-btp" variant="secondary" size="sm">
                Ouvrir l&apos;annuaire
              </ButtonLink>
            }
          />
          <button type="button" onClick={() => void refetch()} className="sr-only">
            Recharger
          </button>
        </div>
      ) : null}

      <div className="mt-12 grid gap-6 border-t border-k-line pt-10 sm:grid-cols-2 lg:grid-cols-4">
        {ECOSYSTEM_PROMISES.map((promise) => {
          const Icon = promise.icon;
          return (
            <div key={promise.title}>
              <span className="flex size-9 items-center justify-center rounded-k bg-k-blue-soft text-k-blue" aria-hidden>
                <Icon className="size-4" />
              </span>
              <h3 className="mt-4 text-[0.9375rem]">{promise.title}</h3>
              <p className="mt-1.5 text-[0.8125rem] leading-relaxed text-k-muted">{promise.description}</p>
            </div>
          );
        })}
      </div>
    </Section>
  );
}

/* ------------------------------------------------------------ réalisations */

export function Catalog() {
  const { data, isLoading } = useRealizations({ page_size: 4 });
  const items = data?.results ?? [];

  return (
    <Section id="catalogue" tone="mist">
      <SectionHeading
        eyebrow="Catalogue de réalisations"
        title="Ce que nos entreprises ont réellement construit"
        description="Chaque réalisation publiée est rattachée à une entreprise identifiée : photos, surface, durée de chantier et parfois budget annoncé par l'entreprise elle-même."
        action={
          <ButtonLink to="/realisations" variant="secondary" iconRight={<ArrowRight className="size-4" aria-hidden />}>
            Voir tout le catalogue
          </ButtonLink>
        }
      />

      <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {isLoading
          ? Array.from({ length: 4 }).map((_, index) => <CardSkeleton key={index} lines={3} />)
          : items.map((item) => (
              <article key={item.id} className="group flex flex-col overflow-hidden rounded-k-lg border border-k-line bg-white">
                <Link to={`/realisations/${item.slug}`} className="block">
                  <div className="h-44 overflow-hidden bg-k-blue-soft">
                    {resolveMedia(item.cover_url) ? (
                      <img
                        src={resolveMedia(item.cover_url) ?? ''}
                        alt={item.title}
                        loading="lazy"
                        className="size-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
                      />
                    ) : (
                      <div className="k-grid-lines size-full bg-k-blue" aria-hidden />
                    )}
                  </div>
                </Link>

                <div className="flex flex-1 flex-col p-5">
                  <Badge tone="blue" size="sm">
                    {item.type_label}
                  </Badge>
                  <h3 className="mt-3 line-clamp-2 text-[1rem]">
                    <Link to={`/realisations/${item.slug}`} className="hover:text-k-blue">
                      {item.title}
                    </Link>
                  </h3>
                  <p className="mt-2 flex items-center gap-1 text-[0.75rem] text-k-muted">
                    <MapPin className="size-3" aria-hidden />
                    {item.display_location || 'Cameroun'}
                  </p>

                  <div className="mt-auto pt-4">
                    <Link
                      to={`/entreprises/${item.company_slug}`}
                      className="flex items-center gap-1.5 text-[0.75rem] font-medium text-k-blue hover:text-k-green-dark"
                    >
                      <Building2 className="size-3.5" aria-hidden />
                      {item.company_name}
                      {item.company_verified ? <BadgeCheck className="size-3.5 text-k-green" aria-hidden /> : null}
                    </Link>

                    <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[0.6875rem] text-k-muted">
                      {item.surface_m2 ? (
                        <li className="inline-flex items-center gap-1">
                          <Ruler className="size-3" aria-hidden />
                          {Number(item.surface_m2).toLocaleString('fr-FR')} m²
                        </li>
                      ) : null}
                      {item.duration_days ? (
                        <li className="inline-flex items-center gap-1">
                          <CalendarClock className="size-3" aria-hidden />
                          {item.duration_days} jours
                        </li>
                      ) : null}
                      <li className="inline-flex items-center gap-1">
                        <Users className="size-3" aria-hidden />
                        {item.year}
                      </li>
                    </ul>
                  </div>
                </div>
              </article>
            ))}
      </div>
    </Section>
  );
}

/* ------------------------------------------------------------ opportunités */

export function Opportunities() {
  const { data, isLoading } = useOpportunities({ page_size: 3, ordering: '-is_featured' });
  const items = data?.results ?? [];

  return (
    <Section id="opportunites">
      <div className="grid gap-12 lg:grid-cols-[1fr_1.4fr] lg:gap-16">
        <div>
          <SectionHeading
            eyebrow="Marchés & opportunités"
            title="Les appels d'offres privés du Cameroun"
            description="Particuliers, bailleurs, entreprises et institutions publient leurs marchés sur KEMTA. Les entreprises vérifiées candidatent en ligne, l'instruction est tracée et le donneur d'ordre décide en connaissance de cause."
          />

          <Media
            name="marche-btp"
            alt="Immeuble R+3 en construction avec grue à Douala"
            ratio="4 / 3"
            sizes="(min-width: 1024px) 38vw, 100vw"
            className="mt-8 rounded-k-lg"
          />

          <ul className="mt-8 space-y-3 text-[0.875rem] text-k-muted">
            <li className="flex items-start gap-2.5">
              <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-k-green" aria-hidden />
              Candidature avec présentation, méthodologie, budget et délai proposés.
            </li>
            <li className="flex items-start gap-2.5">
              <span className="mt-1.5 size-1.5 rounded-full bg-k-green" aria-hidden />
              Instruction : présélection, visite de site, attribution motivée.
            </li>
            <li className="flex items-start gap-2.5">
              <span className="mt-1.5 size-1.5 rounded-full bg-k-green" aria-hidden />
              Notification automatique des entreprises retenues et écartées.
            </li>
          </ul>

          <div className="mt-8 flex flex-wrap gap-3">
            <ButtonLink to="/opportunites">Voir les marchés ouverts</ButtonLink>
            <ButtonLink to="/espace-entreprise" variant="secondary">
              J&apos;inscris mon entreprise
            </ButtonLink>
          </div>
        </div>

        <div className="space-y-4">
          {isLoading
            ? Array.from({ length: 3 }).map((_, index) => <CardSkeleton key={index} lines={4} />)
            : items.map((item) => (
                <article
                  key={item.id}
                  className="flex flex-col gap-4 rounded-k-lg border border-k-line bg-white p-5 transition-colors hover:border-k-blue-line sm:flex-row sm:items-center"
                >
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge code={item.status} label={item.status_label || statusLabel(item.status)} />
                      {item.requires_verified_company ? (
                        <Badge tone="outline" size="sm">
                          Entreprises vérifiées
                        </Badge>
                      ) : null}
                      {item.days_left !== null && item.days_left !== undefined && item.is_open ? (
                        <Badge tone={item.days_left <= 7 ? 'amber' : 'neutral'} size="sm">
                          {item.days_left <= 0 ? 'Clôture imminente' : `Clôture dans ${item.days_left} j`}
                        </Badge>
                      ) : null}
                    </div>

                    <h3 className="mt-3 text-[1.0625rem]">
                      <Link to={`/opportunites/${item.slug}`} className="hover:text-k-blue">
                        {item.title}
                      </Link>
                    </h3>

                    <p className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-[0.8125rem] text-k-muted">
                      <span className="inline-flex items-center gap-1">
                        <MapPin className="size-3.5" aria-hidden />
                        {item.display_location || 'Cameroun'}
                      </span>
                      <span>{item.property_type_label}</span>
                      {item.application_deadline ? (
                        <span>Dossier avant le {formatDate(item.application_deadline)}</span>
                      ) : null}
                    </p>

                    <p className="mt-3 text-[0.875rem] font-medium text-k-blue">
                      {item.budget_visible
                        ? item.budget_label
                        : `Budget communiqué aux candidats · ${formatXaf(item.budget_min_xaf, { compact: true })}`}
                    </p>
                  </div>

                  <ButtonLink to={`/opportunites/${item.slug}`} variant="secondary" size="sm">
                    Voir le marché
                  </ButtonLink>
                </article>
              ))}

          {!isLoading && items.length === 0 ? (
            <EmptyState
              title="Aucun marché ouvert pour le moment"
              description="Les appels d'offres publiés apparaîtront ici. Inscrivez votre entreprise pour être notifiée dès la publication."
              action={<ButtonLink to="/espace-entreprise" size="sm">Inscrire mon entreprise</ButtonLink>}
            />
          ) : null}
        </div>
      </div>
    </Section>
  );
}
