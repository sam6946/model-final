import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  BadgeCheck,
  CalendarClock,
  ChevronRight,
  Layers,
  MapPin,
  Ruler,
  Shapes,
  Wallet,
} from 'lucide-react';

import { http } from '@/lib/api';
import { Seo } from '@/components/Seo';
import { Section, SectionHeading } from '@/components/layout/Section';
import { ButtonLink } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { CardSkeleton, EmptyState, ErrorState } from '@/components/ui/Feedback';
import { breadcrumbSchema } from '@/lib/seo';
import { formatXaf } from '@/lib/format';
import type { RealizationCard } from '@/lib/types';

type MediaItem = {
  id: number;
  kind: string;
  caption: string;
  url?: string;
  thumbnail_url?: string;
  medium_url?: string;
};

type RealizationDetail = RealizationCard & {
  description: string;
  company_logo_url?: string | null;
  company_city?: string;
  rooms_count?: number | null;
  levels_count?: number | null;
  budget_xaf?: string | null;
  client_name?: string;
  client_testimonial?: string;
  view_count?: number;
  media?: MediaItem[];
};

export default function RealizationPage() {
  const { slug } = useParams<{ slug: string }>();
  const [activeMedia, setActiveMedia] = useState(0);

  const { data, isLoading, isError, refetch } = useQuery<RealizationDetail>({
    queryKey: ['realization', slug],
    enabled: Boolean(slug),
    queryFn: () => http.get<RealizationDetail>(`/catalog/realizations/${slug}/`),
    staleTime: 10 * 60_000,
  });

  if (isError) {
    return (
      <Section>
        <ErrorState message="Cette réalisation n'a pas pu être chargée." onRetry={() => void refetch()} />
        <div className="mt-6 text-center">
          <ButtonLink to="/realisations" variant="secondary">
            Revenir au catalogue
          </ButtonLink>
        </div>
      </Section>
    );
  }

  if (isLoading || !data) {
    return (
      <Section>
        <CardSkeleton lines={8} />
      </Section>
    );
  }

  const media = data.media ?? [];
  const main = media[activeMedia];

  return (
    <>
      <Seo
        title={`${data.title} — réalisation ${data.type_label}`}
        description={`${data.description.slice(0, 155)}… Réalisation de ${data.company_name} à ${data.display_location}, ${data.year}.`}
        path={`/realisations/${data.slug}`}
        type="article"
        jsonLd={breadcrumbSchema([
          { name: 'Accueil', path: '/' },
          { name: 'Réalisations', path: '/realisations' },
          { name: data.title, path: `/realisations/${data.slug}` },
        ])}
      />

      <section className="border-b border-k-line bg-white">
        <div className="k-container py-10">
          <nav aria-label="Fil d'Ariane" className="flex flex-wrap items-center gap-1.5 text-[0.8125rem] text-k-muted">
            <Link to="/" className="hover:text-k-blue">
              Accueil
            </Link>
            <ChevronRight className="size-3.5" aria-hidden />
            <Link to="/realisations" className="hover:text-k-blue">
              Réalisations
            </Link>
            <ChevronRight className="size-3.5" aria-hidden />
            <span className="truncate text-k-ink">{data.title}</span>
          </nav>

          <div className="mt-6 flex flex-wrap items-center gap-2.5">
            <Badge tone="blue">{data.type_label}</Badge>
            {data.company_verified ? (
              <Badge tone="green">
                <BadgeCheck className="size-3.5" aria-hidden />
                Entreprise vérifiée
              </Badge>
            ) : null}
            <Badge tone="outline">Livré en {data.year}</Badge>
          </div>

          <h1 className="mt-4 max-w-[30ch]">{data.title}</h1>

          <p className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-[0.875rem] text-k-muted">
            <span className="inline-flex items-center gap-1.5">
              <MapPin className="size-3.5" aria-hidden />
              {data.display_location || 'Cameroun'}
            </span>
            <Link
              to={`/entreprises/${data.company_slug}`}
              className="inline-flex items-center gap-1.5 font-medium text-k-blue hover:text-k-green-dark"
            >
              {data.company_name}
              {data.company_verified ? <BadgeCheck className="size-3.5 text-k-green" aria-hidden /> : null}
            </Link>
          </p>
        </div>
      </section>

      <Section className="!pt-10">
        <div className="grid gap-10 lg:grid-cols-[1.5fr_1fr] lg:gap-14">
          <div className="space-y-8">
            <div>
              {main?.medium_url || main?.url || data.cover_url ? (
                <img
                  src={main?.medium_url ?? main?.url ?? data.cover_url ?? ''}
                  alt={main?.caption || data.title}
                  className="w-full rounded-k-xl border border-k-line object-cover"
                  style={{ aspectRatio: '16 / 10' }}
                />
              ) : (
                <div className="k-grid-lines flex w-full items-end rounded-k-xl bg-k-blue p-6" style={{ aspectRatio: '16 / 10' }}>
                  <span className="max-w-[26ch] text-[0.875rem] text-white/85">
                    Photos du chantier en cours d&apos;ajout par l&apos;entreprise
                  </span>
                </div>
              )}

              {media.length > 1 ? (
                <ul className="mt-4 grid grid-cols-4 gap-3">
                  {media.slice(0, 8).map((item, index) => (
                    <li key={item.id}>
                      <button
                        type="button"
                        onClick={() => setActiveMedia(index)}
                        aria-label={`Afficher la photo ${index + 1}`}
                        aria-current={index === activeMedia}
                        className={`block w-full overflow-hidden rounded-k border transition-all ${
                          index === activeMedia ? 'border-k-green ring-2 ring-k-green/25' : 'border-k-line hover:border-k-blue-line'
                        }`}
                      >
                        <img
                          src={item.thumbnail_url ?? item.medium_url ?? item.url ?? ''}
                          alt=""
                          loading="lazy"
                          className="aspect-[4/3] w-full object-cover"
                        />
                      </button>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>

            <div className="rounded-k-lg border border-k-line bg-white p-6">
              <h2 className="text-[1.25rem]">Le projet</h2>
              <p className="mt-3 whitespace-pre-line text-[0.9375rem] leading-relaxed text-k-muted">{data.description}</p>
            </div>

            {data.client_testimonial ? (
              <blockquote className="rounded-k-lg border-l-4 border-k-green bg-k-green-pale/50 p-6">
                <p className="text-[0.9375rem] leading-relaxed text-k-ink">« {data.client_testimonial} »</p>
                {data.client_name ? (
                  <footer className="mt-3 text-[0.8125rem] text-k-muted">— {data.client_name}</footer>
                ) : null}
              </blockquote>
            ) : null}
          </div>

          <aside className="space-y-6">
            <div className="rounded-k-lg border border-k-line bg-white p-5">
              <h3 className="text-[1.0625rem]">Chiffres clés</h3>
              <dl className="mt-4 divide-y divide-k-line">
                {[
                  { icon: Ruler, label: 'Surface', value: data.surface_m2 ? `${Number(data.surface_m2).toLocaleString('fr-FR')} m²` : '—' },
                  { icon: CalendarClock, label: 'Durée des travaux', value: data.duration_days ? `${data.duration_days} jours` : '—' },
                  { icon: Layers, label: 'Niveaux', value: data.levels_count ?? '—' },
                  { icon: Shapes, label: 'Pièces', value: data.rooms_count ?? '—' },
                  {
                    icon: Wallet,
                    label: 'Budget',
                    value: data.budget_display || (data.budget_xaf ? formatXaf(data.budget_xaf) : 'Non communiqué'),
                  },
                ].map((row) => {
                  const Icon = row.icon;
                  return (
                    <div key={row.label} className="flex items-center justify-between gap-4 py-3">
                      <dt className="inline-flex items-center gap-2 text-[0.8125rem] text-k-muted">
                        <Icon className="size-3.5" aria-hidden />
                        {row.label}
                      </dt>
                      <dd className="text-[0.875rem] font-medium text-k-ink">{row.value}</dd>
                    </div>
                  );
                })}
              </dl>
            </div>

            <div className="rounded-k-lg border border-k-line bg-white p-5">
              <h3 className="text-[1.0625rem]">L&apos;entreprise</h3>
              <Link
                to={`/entreprises/${data.company_slug}`}
                className="mt-3 flex items-center gap-3 rounded-k border border-k-line p-3 transition-colors hover:border-k-blue-line"
              >
                <span className="flex size-10 shrink-0 items-center justify-center rounded-k bg-k-blue-soft font-display text-sm font-bold text-k-blue" aria-hidden>
                  {data.company_name.slice(0, 2).toUpperCase()}
                </span>
                <span className="min-w-0">
                  <span className="block truncate text-[0.9375rem] font-medium text-k-ink">{data.company_name}</span>
                  <span className="block text-[0.75rem] text-k-muted">Voir le profil complet</span>
                </span>
              </Link>
            </div>

            <div className="rounded-k-lg border border-k-blue-line bg-k-blue-soft/50 p-5">
              <p className="font-display text-[0.9375rem] font-semibold text-k-ink">
                Un projet similaire à réaliser ?
              </p>
              <p className="mt-1.5 text-[0.875rem] leading-relaxed text-k-muted">
                KEMTA vous aide à cadrer le budget, choisir l&apos;entreprise et suivre le chantier jusqu&apos;à la
                réception.
              </p>
              <ButtonLink to="/demande" block className="mt-4">
                Déposer une demande
              </ButtonLink>
            </div>
          </aside>
        </div>
      </Section>

      <Section tone="mist" className="!py-12">
        <SectionHeading
          eyebrow="Aller plus loin"
          title="Découvrir d'autres réalisations"
          action={
            <ButtonLink to="/realisations" variant="secondary" size="sm">
              Tout le catalogue
            </ButtonLink>
          }
        />
        {media.length === 0 ? (
          <div className="mt-6">
            <EmptyState
              title="Reportage photo bientôt disponible"
              description="Cette fiche sera enrichie à mesure que l'entreprise transmet ses photos de chantier."
            />
          </div>
        ) : null}
      </Section>
    </>
  );
}
