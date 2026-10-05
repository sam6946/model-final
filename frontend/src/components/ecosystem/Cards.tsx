import { Link } from 'react-router-dom';
import { ArrowLeft, ArrowRight, BadgeCheck, CalendarClock, Eye, MapPin, Ruler, Star, Users } from 'lucide-react';

import { Badge, StatusBadge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { formatDate, formatXaf, initials } from '@/lib/format';
import type { CompanyCard, Opportunity, RealizationCard } from '@/lib/types';

export function resolveMedia(url?: string | null): string | null {
  if (!url) return null;
  return url.startsWith('http') ? url : url;
}

export function CompanyThumb({ name, url, size = 'md' }: { name: string; url?: string | null; size?: 'sm' | 'md' | 'lg' }) {
  const dimension = size === 'sm' ? 'size-10' : size === 'lg' ? 'size-16' : 'size-12';
  return url ? (
    <img
      src={url}
      alt={`Logo ${name}`}
      loading="lazy"
      className={`${dimension} shrink-0 rounded-k border border-k-line bg-white object-contain p-1`}
    />
  ) : (
    <span
      className={`${dimension} flex shrink-0 items-center justify-center rounded-k bg-k-blue-soft font-display text-sm font-bold text-k-blue`}
      aria-hidden
    >
      {initials(name)}
    </span>
  );
}

/* ------------------------------------------------------------------ pagination */

export function Pagination({
  page,
  pages,
  onChange,
  className,
}: {
  page: number;
  pages: number;
  onChange: (page: number) => void;
  className?: string;
}) {
  if (pages <= 1) return null;
  return (
    <nav aria-label="Pagination" className={`flex items-center justify-between gap-4 ${className ?? ''}`}>
      <Button
        variant="secondary"
        size="sm"
        disabled={page <= 1}
        onClick={() => onChange(Math.max(1, page - 1))}
        icon={<ArrowLeft className="size-3.5" aria-hidden />}
      >
        Précédent
      </Button>
      <p className="text-[0.8125rem] text-k-muted">
        Page <span className="font-medium text-k-ink">{page}</span> sur {pages}
      </p>
      <Button
        variant="secondary"
        size="sm"
        disabled={page >= pages}
        onClick={() => onChange(Math.min(pages, page + 1))}
        iconRight={<ArrowRight className="size-3.5" aria-hidden />}
      >
        Suivant
      </Button>
    </nav>
  );
}

/* ------------------------------------------------------------------- entreprises */

export function CompanyTile({ company }: { company: CompanyCard }) {
  return (
    <article className="group flex flex-col overflow-hidden rounded-k-lg border border-k-line bg-white transition-shadow duration-300 hover:shadow-k">
      <Link to={`/entreprises/${company.slug}`} className="block">
        <div className="relative h-40 overflow-hidden bg-k-blue-soft">
          {company.cover_url ? (
            <img
              src={company.cover_url}
              alt={`${company.name} — chantier`}
              loading="lazy"
              className="size-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
            />
          ) : (
            <div className="k-grid-lines size-full bg-k-blue" aria-hidden />
          )}
          <div className="absolute left-3 top-3 flex flex-wrap gap-2">
            {company.is_verified ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-white/95 px-2.5 py-1 text-[0.6875rem] font-medium text-k-green-dark">
                <BadgeCheck className="size-3" aria-hidden />
                Vérifiée
              </span>
            ) : (
              <span className="inline-flex items-center rounded-full bg-white/95 px-2.5 py-1 text-[0.6875rem] font-medium text-k-muted">
                Dossier en cours
              </span>
            )}
            {company.is_featured ? (
              <span className="inline-flex items-center rounded-full bg-k-blue px-2.5 py-1 text-[0.6875rem] font-medium text-white">
                Mise en avant
              </span>
            ) : null}
          </div>
        </div>
      </Link>

      <div className="flex flex-1 flex-col p-5">
        <div className="flex items-start gap-3">
          <CompanyThumb name={company.name} url={company.logo_url} size="sm" />
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

        <p className="mt-3 line-clamp-3 text-[0.875rem] leading-relaxed text-k-muted">{company.description}</p>

        <ul className="mt-4 flex flex-wrap gap-1.5">
          {(company.specialities ?? []).slice(0, 4).map((specialty) => (
            <li key={specialty.code}>
              <Badge tone="outline" size="sm">
                {specialty.name}
              </Badge>
            </li>
          ))}
        </ul>

        <dl className="mt-auto grid grid-cols-4 gap-2 border-t border-k-line pt-4 pt-4 text-center">
          <div>
            <dt className="text-[0.625rem] uppercase tracking-wide text-k-muted">Chantiers</dt>
            <dd className="font-display text-[0.9375rem] font-semibold text-k-ink">{company.projects_count}</dd>
          </div>
          <div>
            <dt className="text-[0.625rem] uppercase tracking-wide text-k-muted">Expérience</dt>
            <dd className="font-display text-[0.9375rem] font-semibold text-k-ink">{company.years_experience} ans</dd>
          </div>
          <div>
            <dt className="text-[0.625rem] uppercase tracking-wide text-k-muted">Réalisations</dt>
            <dd className="font-display text-[0.9375rem] font-semibold text-k-ink">{company.realizations_count}</dd>
          </div>
          <div>
            <dt className="text-[0.625rem] uppercase tracking-wide text-k-muted">Note</dt>
            <dd className="flex items-center justify-center gap-1 font-display text-[0.9375rem] font-semibold text-k-ink">
              {company.rating ? (
                <>
                  <Star className="size-3 fill-k-green text-k-green" aria-hidden />
                  {company.rating.toFixed(1)}
                </>
              ) : (
                '—'
              )}
            </dd>
          </div>
        </dl>
      </div>
    </article>
  );
}

/* ------------------------------------------------------------------ réalisations */

export function RealizationTile({ realization }: { realization: RealizationCard }) {
  return (
    <article className="group flex flex-col overflow-hidden rounded-k-lg border border-k-line bg-white">
      <Link to={`/realisations/${realization.slug}`} className="block">
        <div className="h-48 overflow-hidden bg-k-blue-soft">
          {realization.cover_url ? (
            <img
              src={realization.cover_url}
              alt={realization.title}
              loading="lazy"
              className="size-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
            />
          ) : (
            <div className="k-grid-lines size-full bg-k-blue" aria-hidden />
          )}
        </div>
      </Link>

      <div className="flex flex-1 flex-col p-5">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="blue" size="sm">
            {realization.type_label}
          </Badge>
          {realization.is_featured ? (
            <Badge tone="green" size="sm">
              Coup de cœur
            </Badge>
          ) : null}
        </div>

        <h3 className="mt-3 line-clamp-2 text-[1.0625rem]">
          <Link to={`/realisations/${realization.slug}`} className="hover:text-k-blue">
            {realization.title}
          </Link>
        </h3>

        <p className="mt-2 flex items-center gap-1 text-[0.75rem] text-k-muted">
          <MapPin className="size-3" aria-hidden />
          {realization.display_location || 'Cameroun'}
        </p>

        <div className="mt-auto pt-4">
          <Link
            to={`/entreprises/${realization.company_slug}`}
            className="inline-flex items-center gap-1.5 text-[0.8125rem] font-medium text-k-blue hover:text-k-green-dark"
          >
            {realization.company_name}
            {realization.company_verified ? <BadgeCheck className="size-3.5 text-k-green" aria-hidden /> : null}
          </Link>

          <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[0.6875rem] text-k-muted">
            {realization.surface_m2 ? (
              <li className="inline-flex items-center gap-1">
                <Ruler className="size-3" aria-hidden />
                {Number(realization.surface_m2).toLocaleString('fr-FR')} m²
              </li>
            ) : null}
            {realization.duration_days ? (
              <li className="inline-flex items-center gap-1">
                <CalendarClock className="size-3" aria-hidden />
                {realization.duration_days} jours
              </li>
            ) : null}
            <li className="inline-flex items-center gap-1">
              <Users className="size-3" aria-hidden />
              {realization.year}
            </li>
          </ul>
        </div>
      </div>
    </article>
  );
}

/* ------------------------------------------------------------------ opportunités */

export function OpportunityRow({ opportunity }: { opportunity: Opportunity }) {
  return (
    <article className="flex flex-col gap-4 rounded-k-lg border border-k-line bg-white p-5 transition-colors hover:border-k-blue-line lg:flex-row lg:items-center">
      <div className="flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge code={opportunity.status} label={opportunity.status_label} />
          {opportunity.requires_verified_company ? (
            <Badge tone="outline" size="sm">
              Entreprises vérifiées
            </Badge>
          ) : null}
          {opportunity.is_open && opportunity.days_left !== null ? (
            <Badge tone={opportunity.days_left <= 7 ? 'amber' : 'neutral'} size="sm">
              {opportunity.days_left <= 0 ? 'Clôture imminente' : `Clôture dans ${opportunity.days_left} j`}
            </Badge>
          ) : null}
          {opportunity.already_applied ? (
            <Badge tone="green" size="sm">
              Candidature envoyée
            </Badge>
          ) : null}
        </div>

        <h3 className="mt-3 text-[1.0625rem]">
          <Link to={`/opportunites/${opportunity.slug}`} className="hover:text-k-blue">
            {opportunity.title}
          </Link>
        </h3>

        <p className="mt-2 line-clamp-2 text-[0.875rem] leading-relaxed text-k-muted">{opportunity.description}</p>

        <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 text-[0.8125rem] text-k-muted">
          <li className="inline-flex items-center gap-1.5">
            <MapPin className="size-3.5" aria-hidden />
            {opportunity.display_location || 'Cameroun'}
          </li>
          <li>{opportunity.property_type_label}</li>
          {opportunity.application_deadline ? (
            <li>Dossier avant le {formatDate(opportunity.application_deadline)}</li>
          ) : null}
          {opportunity.applications_count ? (
            <li>
              {opportunity.applications_count} candidature{opportunity.applications_count > 1 ? 's' : ''}
            </li>
          ) : null}
        </ul>

        <p className="mt-3 text-[0.9375rem] font-medium text-k-blue">
          {opportunity.budget_visible
            ? opportunity.budget_label
            : `Budget communiqué aux candidats · à partir de ${formatXaf(opportunity.budget_min_xaf, { compact: true })}`}
        </p>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        <Link
          to={`/opportunites/${opportunity.slug}`}
          className="inline-flex h-10 items-center gap-2 rounded-k border border-k-line px-4 text-[0.8125rem] font-medium text-k-ink transition-colors hover:border-k-blue-line hover:bg-k-mist"
        >
          <Eye className="size-3.5" aria-hidden />
          Détails
        </Link>
      </div>
    </article>
  );
}
