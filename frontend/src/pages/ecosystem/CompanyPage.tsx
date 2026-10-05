import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  BadgeCheck,
  Building2,
  ChevronRight,
  Mail,
  MapPin,
  Phone,
  ShieldCheck,
  Star,
  Users,
  Wrench,
} from 'lucide-react';

import { http } from '@/lib/api';
import { Seo } from '@/components/Seo';
import { Section, SectionHeading } from '@/components/layout/Section';
import { Button, ButtonLink } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { CardSkeleton, EmptyState, ErrorState } from '@/components/ui/Feedback';
import { CompanyThumb, RealizationTile } from '@/components/ecosystem/Cards';
import { useRealizations } from '@/lib/hooks';
import { breadcrumbSchema } from '@/lib/seo';
import { formatDate, formatPhone } from '@/lib/format';
import type { CompanyCard, RealizationCard } from '@/lib/types';

type CompanyDetail = CompanyCard & {
  address?: string;
  phone?: string;
  email?: string;
  website?: string;
  legal_name?: string;
  registration_number?: string;
  verified_at?: string | null;
  stats?: Record<string, number | string>;
  reviews?: Array<{
    id: number;
    author_name: string;
    rating: number;
    comment: string;
    created_at: string;
    work_quality?: number;
    deadline_respect?: number;
    communication?: number;
  }>;
};

function Stars({ value }: { value: number }) {
  return (
    <span className="flex items-center gap-0.5" aria-label={`${value} sur 5`}>
      {Array.from({ length: 5 }).map((_, index) => (
        <Star
          key={index}
          className={`size-3.5 ${index < Math.round(value) ? 'fill-k-green text-k-green' : 'text-k-line'}`}
          aria-hidden
        />
      ))}
    </span>
  );
}

export default function CompanyPage() {
  const { slug } = useParams<{ slug: string }>();

  const { data: company, isLoading, isError, refetch } = useQuery<CompanyDetail>({
    queryKey: ['company', slug],
    enabled: Boolean(slug),
    queryFn: () => http.get<CompanyDetail>(`/companies/${slug}/`),
    staleTime: 5 * 60_000,
  });

  const { data: realizations } = useRealizations({ company: slug, page_size: 6 });

  if (isError) {
    return (
      <Section>
        <ErrorState
          message="Ce profil d'entreprise n'a pas pu être chargé. Le lien est peut-être obsolète."
          onRetry={() => void refetch()}
        />
        <div className="mt-6 text-center">
          <ButtonLink to="/entreprises-btp" variant="secondary">
            Revenir à l&apos;annuaire
          </ButtonLink>
        </div>
      </Section>
    );
  }

  if (isLoading || !company) {
    return (
      <Section>
        <div className="space-y-6">
          <CardSkeleton lines={3} />
          <div className="grid gap-6 lg:grid-cols-3">
            <CardSkeleton lines={6} />
            <CardSkeleton lines={6} />
            <CardSkeleton lines={6} />
          </div>
        </div>
      </Section>
    );
  }

  const items: RealizationCard[] = realizations?.results ?? [];

  return (
    <>
      <Seo
        title={`${company.name} — entreprise BTP à ${company.city}`}
        description={`${company.description.slice(0, 150)}… Profil ${company.is_verified ? 'vérifié' : 'en cours de vérification'} sur KEMTA.`}
        path={`/entreprises/${company.slug}`}
        type="article"
        jsonLd={[
          breadcrumbSchema([
            { name: 'Accueil', path: '/' },
            { name: 'Entreprises BTP', path: '/entreprises-btp' },
            { name: company.name, path: `/entreprises/${company.slug}` },
          ]),
          {
            '@context': 'https://schema.org',
            '@type': 'Organization',
            name: company.name,
            description: company.description,
            address: {
              '@type': 'PostalAddress',
              addressLocality: company.city,
              addressRegion: company.region,
              addressCountry: 'CM',
            },
            telephone: company.phone,
            email: company.email,
          },
        ]}
      />

      {/* Bandeau de couverture */}
      <section className="relative">
        <div className="h-44 w-full overflow-hidden bg-k-blue sm:h-60">
          {company.cover_url ? (
            <img src={company.cover_url} alt={`${company.name} — chantier`} className="size-full object-cover" />
          ) : (
            <div className="k-grid-lines size-full" aria-hidden />
          )}
        </div>

        <div className="k-container -mt-14 pb-8 lg:-mt-16">
          <div className="rounded-k-xl border border-k-line bg-white p-5 shadow-k sm:p-7">
            <nav aria-label="Fil d'Ariane" className="flex flex-wrap items-center gap-1.5 text-[0.8125rem] text-k-muted">
              <Link to="/" className="hover:text-k-blue">
                Accueil
              </Link>
              <ChevronRight className="size-3.5" aria-hidden />
              <Link to="/entreprises-btp" className="hover:text-k-blue">
                Entreprises BTP
              </Link>
              <ChevronRight className="size-3.5" aria-hidden />
              <span className="text-k-ink">{company.name}</span>
            </nav>

            <div className="mt-5 flex flex-col gap-5 sm:flex-row sm:items-start">
              <CompanyThumb name={company.name} url={company.logo_url} size="lg" />

              <div className="flex-1">
                <div className="flex flex-wrap items-center gap-2.5">
                  <h1 className="text-[1.6rem] leading-tight">{company.name}</h1>
                  {company.is_verified ? (
                    <Badge tone="green">
                      <BadgeCheck className="size-3.5" aria-hidden />
                      Entreprise vérifiée
                    </Badge>
                  ) : (
                    <Badge tone="amber">Dossier en cours d&apos;examen</Badge>
                  )}
                  {company.is_featured ? <Badge tone="blue">Recommandée par KEMTA</Badge> : null}
                </div>

                <p className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[0.875rem] text-k-muted">
                  <span className="inline-flex items-center gap-1.5">
                    <MapPin className="size-3.5" aria-hidden />
                    {company.address || company.city}
                    {company.region ? ` · ${company.region}` : ''}
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <Wrench className="size-3.5" aria-hidden />
                    {(company.specialities ?? []).slice(0, 3).map((item) => item.name).join(', ') || "Corps d'état non précisés"}
                  </span>
                  {company.rating_count ? (
                    <span className="inline-flex items-center gap-1.5">
                      <Stars value={company.rating} />
                      {company.rating.toFixed(1)} ({company.rating_count} avis)
                    </span>
                  ) : null}
                </p>

                <dl className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
                  {[
                    { label: 'Chantiers réalisés', value: company.projects_count },
                    { label: "Années d'expérience", value: company.years_experience },
                    { label: 'Collaborateurs', value: company.employees_count },
                    { label: 'Réalisations publiées', value: company.realizations_count },
                  ].map((item) => (
                    <div key={item.label}>
                      <dt className="text-[0.6875rem] uppercase tracking-wide text-k-muted">{item.label}</dt>
                      <dd className="mt-0.5 font-display text-[1.25rem] font-bold text-k-ink">{item.value}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            </div>

            <div className="mt-6 flex flex-wrap gap-3 border-t border-k-line pt-5">
              <ButtonLink to="/demande" size="md">
                Demander un devis à cette entreprise
              </ButtonLink>
              {company.phone ? (
                <a
                  href={`tel:${company.phone}`}
                  className="inline-flex h-11 items-center gap-2 rounded-k border border-k-line px-5 text-[0.9375rem] font-medium text-k-ink transition-colors hover:border-k-blue-line hover:bg-k-mist"
                >
                  <Phone className="size-4 text-k-green" aria-hidden />
                  {formatPhone(company.phone)}
                </a>
              ) : null}
              {company.email ? (
                <a
                  href={`mailto:${company.email}`}
                  className="inline-flex h-11 items-center gap-2 rounded-k border border-k-line px-5 text-[0.9375rem] font-medium text-k-ink transition-colors hover:border-k-blue-line hover:bg-k-mist"
                >
                  <Mail className="size-4 text-k-green" aria-hidden />
                  Écrire
                </a>
              ) : null}
            </div>
          </div>
        </div>
      </section>

      <Section tone="mist" className="!pt-12">
        <div className="grid gap-10 lg:grid-cols-[1.5fr_1fr] lg:gap-14">
          <div className="space-y-8">
            <div className="rounded-k-lg border border-k-line bg-white p-6">
              <h2 className="text-[1.25rem]">Présentation</h2>
              <p className="mt-3 whitespace-pre-line text-[0.9375rem] leading-relaxed text-k-muted">
                {company.description}
              </p>

              <ul className="mt-6 grid gap-4 sm:grid-cols-2">
                {(company.specialities ?? []).map((specialty) => (
                  <li key={specialty.code} className="flex items-start gap-2.5 text-[0.875rem] text-k-ink">
                    <Wrench className="mt-0.5 size-4 shrink-0 text-k-blue" aria-hidden />
                    {specialty.name}
                  </li>
                ))}
              </ul>

              {company.intervention_label ? (
                <p className="mt-5 flex items-start gap-2.5 border-t border-k-line pt-5 text-[0.875rem] text-muted">
                  <MapPin className="mt-0.5 size-4 shrink-0 text-k-green" aria-hidden />
                  Zones d&apos;intervention : {company.intervention_label}
                </p>
              ) : null}
            </div>

            <div>
              <SectionHeading
                eyebrow="Catalogue"
                title="Réalisations publiées"
                description="Chaque réalisation est rattachée à cette entreprise et validée avant publication."
                action={
                  <ButtonLink to={`/realisations?company=${company.slug}`} variant="secondary" size="sm">
                    Tout voir
                  </ButtonLink>
                }
              />

              <div className="mt-8 grid gap-6 sm:grid-cols-2">
                {items.length === 0 ? (
                  <div className="sm:col-span-2">
                    <EmptyState
                      icon={<Building2 className="size-5" aria-hidden />}
                      title="Aucune réalisation publiée pour le moment"
                      description="Cette entreprise n'a pas encore publié de réalisation vérifiée sur KEMTA."
                    />
                  </div>
                ) : (
                  items.map((item) => <RealizationTile key={item.id} realization={item} />)
                )}
              </div>
            </div>
          </div>

          <aside className="space-y-6">
            <div className="rounded-k-lg border border-k-line bg-white p-5">
              <h3 className="flex items-center gap-2 text-[1.0625rem]">
                <ShieldCheck className="size-4 text-k-green" aria-hidden />
                Dossier vérifié par KEMTA
              </h3>
              <ul className="mt-4 space-y-3 text-[0.8125rem] text-k-muted">
                <li className="flex items-start gap-2">
                  <BadgeCheck className="mt-0.5 size-3.5 shrink-0 text-k-green" aria-hidden />
                  Registre de commerce et du crédit mobilier
                </li>
                <li className="flex items-start gap-2">
                  <BadgeCheck className="mt-0.5 size-3.5 shrink-0 text-k-green" aria-hidden />
                  Attestation de non-redevance fiscale
                </li>
                <li className="flex items-start gap-2">
                  <BadgeCheck className="mt-0.5 size-3.5 shrink-0 text-k-green" aria-hidden />
                  Couverture sociale (CNPS)
                </li>
                <li className="flex items-start gap-2">
                  <BadgeCheck className="mt-0.5 size-3.5 shrink-0 text-k-green" aria-hidden />
                  Références de chantier contrôlées
                </li>
              </ul>
              {company.verified_at ? (
                <p className="mt-4 border-t border-k-line pt-4 text-[0.75rem] text-k-muted">
                  Dernière vérification : {formatDate(company.verified_at)}
                </p>
              ) : null}
              {company.registration_number ? (
                <p className="mt-1 text-[0.75rem] text-k-muted">RCCM : {company.registration_number}</p>
              ) : null}
            </div>

            <div className="rounded-k-lg border border-k-line bg-white p-5">
              <h3 className="flex items-center gap-2 text-[1.0625rem]">
                <Users className="size-4 text-k-blue" aria-hidden />
                Travailler avec cette entreprise
              </h3>
              <p className="mt-2 text-[0.875rem] leading-relaxed text-k-muted">
                KEMTA peut encadrer la relation : appel d&apos;offres, contrat, suivi de chantier et contrôle des
                paiements. Vous gardez la décision finale.
              </p>
              <ButtonLink to="/demande" block className="mt-4">
                Lancer une demande encadrée
              </ButtonLink>
              <ButtonLink to="/services/construire" variant="secondary" block className="mt-2.5">
                Voir la prestation de construction
              </ButtonLink>
            </div>

            {company.reviews?.length ? (
              <div className="rounded-k-lg border border-k-line bg-white p-5">
                <h3 className="text-[1.0625rem]">Avis de clients KEMTA</h3>
                <ul className="mt-4 space-y-4">
                  {company.reviews.slice(0, 3).map((review) => (
                    <li key={review.id} className="border-b border-k-line pb-4 last:border-0 last:pb-0">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-[0.875rem] font-medium text-k-ink">{review.author_name || 'Client KEMTA'}</p>
                        <Stars value={review.rating} />
                      </div>
                      <p className="mt-1.5 text-[0.8125rem] leading-relaxed text-k-muted">{review.comment}</p>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </aside>
        </div>
      </Section>

      <Section className="!py-12">
        <div className="flex flex-col items-start justify-between gap-5 rounded-k-lg border border-k-blue-line bg-k-blue-soft/50 p-6 md:flex-row md:items-center">
          <div>
            <p className="font-display text-[1.0625rem] font-semibold text-k-ink">
              Besoin de comparer plusieurs entreprises ?
            </p>
            <p className="mt-1.5 text-[0.875rem] text-k-muted">
              Décrivez votre projet une seule fois : KEMTA consulte le réseau et vous présente les meilleures offres.
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2.5">
            <ButtonLink to="/demande">Déposer une demande</ButtonLink>
            <ButtonLink to="/entreprises-btp" variant="secondary">
              Comparer les entreprises
            </ButtonLink>
          </div>
        </div>
      </Section>
    </>
  );
}
