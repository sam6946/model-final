import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search, X } from 'lucide-react';

import { Seo } from '@/components/Seo';
import { Section } from '@/components/layout/Section';
import { Button, ButtonLink } from '@/components/ui/Button';
import { CardSkeleton, EmptyState, ErrorState } from '@/components/ui/Feedback';
import { Field, Input, Select } from '@/components/ui/Field';
import { Pagination, RealizationTile } from '@/components/ecosystem/Cards';
import { useRealizationFilters, useRealizations } from '@/lib/hooks';
import { breadcrumbSchema } from '@/lib/seo';

const PAGE_SIZE = 9;

const FALLBACK_TYPES = [
  { value: '', label: 'Tous les types' },
  { value: 'VILLA', label: 'Villas' },
  { value: 'MAISON', label: 'Maisons' },
  { value: 'IMMEUBLE', label: 'Immeubles' },
  { value: 'APPARTEMENT', label: 'Appartements' },
  { value: 'LOCAL_COMMERCIAL', label: 'Locaux commerciaux' },
  { value: 'ECOLE', label: 'Écoles' },
  { value: 'SANTE', label: 'Structures de santé' },
  { value: 'ROUTE', label: 'Voirie & routes' },
  { value: 'RENOVATION', label: 'Rénovations' },
  { value: 'BUREAU', label: 'Bureaux' },
  { value: 'FORAGE', label: 'Forages' },
  { value: 'AMENAGEMENT', label: 'Aménagements & VRD' },
];

const CURRENT_YEAR = new Date().getFullYear();
const YEARS = Array.from({ length: 6 }, (_, index) => CURRENT_YEAR - index);

export default function RealizationsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [type, setType] = useState('');
  const [year, setYear] = useState('');
  const [page, setPage] = useState(1);

  const companySlug = searchParams.get('company') ?? '';
  const { data: facets } = useRealizationFilters();
  const typeOptions = useMemo<Array<{ value: string; label: string; count?: number }>>(
    () =>
      facets?.types?.length
        ? [{ value: '', label: 'Tous les types' }, ...facets.types.map((item) => ({
            value: item.value,
            label: `${item.label} (${item.count})`,
            count: item.count,
          }))]
        : FALLBACK_TYPES,
    [facets],
  );

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebounced(search.trim());
      setPage(1);
    }, 350);
    return () => clearTimeout(timer);
  }, [search]);

  const params = useMemo(
    () => ({
      page,
      page_size: PAGE_SIZE,
      search: debounced || undefined,
      realization_type: type || undefined,
      year: year || undefined,
      company: companySlug || undefined,
      ordering: '-is_featured',
    }),
    [page, debounced, type, year, companySlug],
  );

  const { data, isLoading, isError, refetch } = useRealizations(params);
  const items = data?.results ?? [];

  const reset = () => {
    setSearch('');
    setType('');
    setYear('');
    setSearchParams({});
    setPage(1);
  };

  return (
    <>
      <Seo
        title="Catalogue de réalisations BTP au Cameroun"
        description="Villas, immeubles, écoles, locaux commerciaux : découvrez les réalisations des entreprises BTP vérifiées au Cameroun, avec surfaces, durées et localisations réelles."
        path="/realisations"
        jsonLd={breadcrumbSchema([
          { name: 'Accueil', path: '/' },
          { name: 'Réalisations', path: '/realisations' },
        ])}
      />

      <section className="border-b border-k-line bg-white">
        <div className="k-container py-12 lg:py-16">
          <span className="k-eyebrow">
            <span className="h-px w-8 bg-k-green" aria-hidden />
            Catalogue
          </span>
          <h1 className="mt-5 max-w-[28ch]">Ce que les entreprises KEMTA ont construit</h1>
          <p className="k-lead mt-5">
            Chaque fiche correspond à un chantier réel : surface, durée, localisation et, quand l&apos;entreprise
            l&apos;autorise, budget annoncé. Les photos sont fournies par l&apos;entreprise et validées par KEMTA.
          </p>

          {companySlug ? (
            <p className="mt-6 inline-flex items-center gap-2 rounded-full border border-k-blue-line bg-k-blue-soft px-3.5 py-1.5 text-[0.8125rem] text-k-blue">
              Filtre actif : réalisations de {companySlug.replace(/-/g, ' ')}
              <button type="button" onClick={() => setSearchParams({})} className="inline-flex items-center" aria-label="Retirer ce filtre">
                <X className="size-3.5" aria-hidden />
              </button>
            </p>
          ) : null}

          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Field label="Rechercher" htmlFor="real-search">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-k-muted" aria-hidden />
                <Input
                  id="real-search"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Titre, ville, entreprise…"
                  className="pl-9"
                />
              </div>
            </Field>
            <Field label="Type de réalisation" htmlFor="real-type">
              <Select id="real-type" value={type} onChange={(event) => { setType(event.target.value); setPage(1); }}>
                {typeOptions.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Année de livraison" htmlFor="real-year">
              <Select id="real-year" value={year} onChange={(event) => { setYear(event.target.value); setPage(1); }}>
                <option value="">Toutes les années</option>
                {YEARS.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
            <p className="text-[0.8125rem] text-k-muted">
              {isLoading ? 'Chargement…' : `${data?.count ?? 0} réalisation${(data?.count ?? 0) > 1 ? 's' : ''}`}
            </p>
            <div className="flex items-center gap-2">
              {(search || type || year || companySlug) ? (
                <Button variant="ghost" size="sm" onClick={reset} icon={<X className="size-3.5" aria-hidden />}>
                  Réinitialiser
                </Button>
              ) : null}
              <ButtonLink to="/demande" size="sm">
                Lancer mon projet
              </ButtonLink>
            </div>
          </div>
        </div>
      </section>

      <Section>
        {isError ? (
          <ErrorState message="Le catalogue n'a pas pu être chargé." onRetry={() => void refetch()} />
        ) : isLoading ? (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <CardSkeleton key={index} lines={4} />
            ))}
          </div>
        ) : items.length === 0 ? (
          <EmptyState
            title="Aucune réalisation ne correspond à ces critères"
            description="Essayez une autre année, un autre type de bâtiment, ou parcourez l'ensemble du catalogue."
            action={<Button onClick={reset}>Voir tout le catalogue</Button>}
          />
        ) : (
          <>
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((item) => (
                <RealizationTile key={item.id} realization={item} />
              ))}
            </div>
            <Pagination page={data?.page ?? 1} pages={data?.pages ?? 1} onChange={setPage} className="mt-10" />
          </>
        )}
      </Section>
    </>
  );
}
