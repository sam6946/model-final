import { useEffect, useMemo, useState } from 'react';
import { BadgeCheck, Filter, Search, X } from 'lucide-react';

import { Seo } from '@/components/Seo';
import { Section, SectionHeading } from '@/components/layout/Section';
import { Button, ButtonLink } from '@/components/ui/Button';
import { CardSkeleton, EmptyState, ErrorState } from '@/components/ui/Feedback';
import { Field, Input, Select } from '@/components/ui/Field';
import { CompanyTile, Pagination } from '@/components/ecosystem/Cards';
import { useCompanies, useSpecialties } from '@/lib/hooks';
import { breadcrumbSchema } from '@/lib/seo';

const PAGE_SIZE = 9;

export default function CompaniesPage() {
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [city, setCity] = useState('');
  const [specialty, setSpecialty] = useState('');
  const [verifiedOnly, setVerifiedOnly] = useState(true);
  const [page, setPage] = useState(1);

  const { data: specialties } = useSpecialties();

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
      city: city.trim() || undefined,
      specialities__code: specialty || undefined,
      is_verified: verifiedOnly ? true : undefined,
      ordering: '-is_featured',
    }),
    [page, debounced, city, specialty, verifiedOnly],
  );

  const { data, isLoading, isError, refetch } = useCompanies(params);
  const companies = data?.results ?? [];
  const activeFilters = [debounced, city, specialty, verifiedOnly ? 'vérifiées' : ''].filter(Boolean).length;

  const reset = () => {
    setSearch('');
    setCity('');
    setSpecialty('');
    setVerifiedOnly(true);
    setPage(1);
  };

  return (
    <>
      <Seo
        title="Entreprises BTP vérifiées au Cameroun"
        description="Annuaire des entreprises BTP dont KEMTA a contrôlé le registre de commerce, l'attestation fiscale et les références de chantier. Filtrez par corps d'état et par ville."
        path="/entreprises-btp"
        jsonLd={breadcrumbSchema([
          { name: 'Accueil', path: '/' },
          { name: 'Entreprises BTP', path: '/entreprises-btp' },
        ])}
      />

      <section className="border-b border-k-line bg-white">
        <div className="k-container py-12 lg:py-16">
          <span className="k-eyebrow">
            <span className="h-px w-8 bg-k-green" aria-hidden />
            Réseau BTP
          </span>
          <h1 className="mt-5 max-w-[26ch]">Entreprises BTP vérifiées au Cameroun</h1>
          <p className="k-lead mt-5">
            Chaque entreprise de cet annuaire a déposé ses pièces administratives et ses références de chantier.
            Le badge « Vérifiée » est attribué après contrôle par l&apos;équipe KEMTA — il peut être retiré en cas de
            manquement constaté.
          </p>

          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Field label="Rechercher" htmlFor="company-search">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-k-muted" aria-hidden />
                <Input
                  id="company-search"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Nom, corps d'état, ville…"
                  className="pl-9"
                />
              </div>
            </Field>

            <Field label="Ville" htmlFor="company-city">
              <Input
                id="company-city"
                value={city}
                onChange={(event) => {
                  setCity(event.target.value);
                  setPage(1);
                }}
                placeholder="Douala, Yaoundé…"
              />
            </Field>

            <Field label="Corps d'état" htmlFor="company-specialty">
              <Select
                id="company-specialty"
                value={specialty}
                onChange={(event) => {
                  setSpecialty(event.target.value);
                  setPage(1);
                }}
              >
                <option value="">Tous les métiers</option>
                {(specialties?.results ?? []).map((item) => (
                  <option key={item.id} value={item.code}>
                    {item.name}
                  </option>
                ))}
              </Select>
            </Field>

            <Field label="Statut du dossier" htmlFor="company-status">
              <Select
                id="company-status"
                value={verifiedOnly ? 'verified' : 'all'}
                onChange={(event) => {
                  setVerifiedOnly(event.target.value === 'verified');
                  setPage(1);
                }}
              >
                <option value="verified">Vérifiées uniquement</option>
                <option value="all">Toutes les entreprises inscrites</option>
              </Select>
            </Field>
          </div>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
            <p className="text-[0.8125rem] text-k-muted">
              {isLoading ? 'Recherche en cours…' : `${data?.count ?? 0} entreprise${(data?.count ?? 0) > 1 ? 's' : ''} correspondante${(data?.count ?? 0) > 1 ? 's' : ''}`}
            </p>
            <div className="flex items-center gap-2">
              {activeFilters > 1 ? (
                <Button variant="ghost" size="sm" onClick={reset} icon={<X className="size-3.5" aria-hidden />}>
                  Réinitialiser les filtres
                </Button>
              ) : null}
              <ButtonLink to="/espace-entreprise" variant="secondary" size="sm">
                Inscrire mon entreprise
              </ButtonLink>
            </div>
          </div>
        </div>
      </section>

      <Section>
        {isError ? (
          <ErrorState
            message="L'annuaire n'a pas pu être chargé. Vérifiez votre connexion puis réessayez."
            onRetry={() => void refetch()}
          />
        ) : isLoading ? (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <CardSkeleton key={index} lines={5} />
            ))}
          </div>
        ) : companies.length === 0 ? (
          <EmptyState
            icon={<Filter className="size-5" aria-hidden />}
            title="Aucune entreprise ne correspond à ces filtres"
            description="Élargissez la recherche à toutes les villes, ou affichez toutes les entreprises inscrites — y compris celles dont le dossier est en cours d'examen."
            action={<Button onClick={reset}>Réinitialiser les filtres</Button>}
          />
        ) : (
          <>
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {companies.map((company) => (
                <CompanyTile key={company.id} company={company} />
              ))}
            </div>
            <Pagination page={data?.page ?? 1} pages={data?.pages ?? 1} onChange={setPage} className="mt-10" />
          </>
        )}
      </Section>

      <Section tone="mist" className="!py-14">
        <div className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr] lg:items-center">
          <div>
            <SectionHeading
              eyebrow="Comment nous vérifions"
              title="Le badge ne s'achète pas"
              description="Registre de commerce et du crédit mobilier, attestation de non-redevance fiscale, couverture CNPS, assurance responsabilité civile le cas échéant, puis contrôle de cohérence des références de chantier."
            />
          </div>
          <div className="rounded-k-lg border border-k-line bg-white p-6">
            <p className="flex items-center gap-2 font-display text-[0.9375rem] font-semibold text-k-ink">
              <BadgeCheck className="size-4 text-k-green" aria-hidden />
              Vous êtes une entreprise ?
            </p>
            <p className="mt-2 text-[0.875rem] leading-relaxed text-k-muted">
              Créez votre profil gratuitement, déposez vos pièces et candidatez aux marchés publiés sur KEMTA.
            </p>
            <ButtonLink to="/espace-entreprise" className="mt-4" block>
              Créer mon profil entreprise
            </ButtonLink>
          </div>
        </div>
      </Section>
    </>
  );
}
