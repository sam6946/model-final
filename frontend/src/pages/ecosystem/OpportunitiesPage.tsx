import { useEffect, useMemo, useState } from 'react';
import { Search, X } from 'lucide-react';

import { Seo } from '@/components/Seo';
import { Section, SectionHeading } from '@/components/layout/Section';
import { Button, ButtonLink } from '@/components/ui/Button';
import { CardSkeleton, EmptyState, ErrorState } from '@/components/ui/Feedback';
import { Field, Input, Select } from '@/components/ui/Field';
import { OpportunityRow, Pagination } from '@/components/ecosystem/Cards';
import { useOpportunities } from '@/lib/hooks';
import { useAuth } from '@/hooks/useAuth';
import { breadcrumbSchema } from '@/lib/seo';

const PAGE_SIZE = 8;

const PROPERTY_TYPES = [
  { value: '', label: 'Tous les ouvrages' },
  { value: 'VILLA', label: 'Villas' },
  { value: 'MAISON', label: 'Maisons' },
  { value: 'IMMEUBLE', label: 'Immeubles' },
  { value: 'APPARTEMENT', label: 'Appartements' },
  { value: 'LOCAL_COMMERCIAL', label: 'Locaux commerciaux' },
  { value: 'ECOLE', label: 'Écoles' },
  { value: 'SANTE', label: 'Santé' },
  { value: 'ROUTE', label: 'Voirie' },
  { value: 'FORAGE', label: 'Forages' },
  { value: 'RENOVATION', label: 'Rénovations' },
];

export default function OpportunitiesPage() {
  const { isAuthenticated } = useAuth();
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [propertyType, setPropertyType] = useState('');
  const [status, setStatus] = useState('OPEN');
  const [page, setPage] = useState(1);

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
      property_type: propertyType || undefined,
      status: status || undefined,
      ordering: '-is_featured',
    }),
    [page, debounced, propertyType, status],
  );

  const { data, isLoading, isError, refetch } = useOpportunities(params);
  const items = data?.results ?? [];

  const reset = () => {
    setSearch('');
    setPropertyType('');
    setStatus('OPEN');
    setPage(1);
  };

  return (
    <>
      <Seo
        title="Marchés et opportunités BTP ouverts au Cameroun"
        description="Appels d'offres privés et marchés de construction publiés sur KEMTA : consultez les budgets, les délais et candidatez en ligne si vous êtes une entreprise vérifiée."
        path="/opportunites"
        jsonLd={breadcrumbSchema([
          { name: 'Accueil', path: '/' },
          { name: 'Opportunités', path: '/opportunites' },
        ])}
      />

      <section className="border-b border-k-line bg-white">
        <div className="k-container py-12 lg:py-16">
          <span className="k-eyebrow">
            <span className="h-px w-8 bg-k-green" aria-hidden />
            Marchés & opportunités
          </span>
          <h1 className="mt-5 max-w-[28ch]">Les marchés publiés sur KEMTA</h1>
          <p className="k-lead mt-5">
            Particuliers, bailleurs, entreprises et institutions publient ici leurs projets. Les entreprises
            vérifiées candidatent en ligne ; l&apos;instruction est tracée et chaque candidat reçoit une réponse
            motivée.
          </p>

          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Field label="Rechercher" htmlFor="opp-search">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-k-muted" aria-hidden />
                <Input
                  id="opp-search"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Titre, ville, référence…"
                  className="pl-9"
                />
              </div>
            </Field>
            <Field label="Type d'ouvrage" htmlFor="opp-type">
              <Select
                id="opp-type"
                value={propertyType}
                onChange={(event) => {
                  setPropertyType(event.target.value);
                  setPage(1);
                }}
              >
                {PROPERTY_TYPES.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Statut" htmlFor="opp-status">
              <Select
                id="opp-status"
                value={status}
                onChange={(event) => {
                  setStatus(event.target.value);
                  setPage(1);
                }}
              >
                <option value="OPEN">Ouverts aux candidatures</option>
                <option value="REVIEWING">En cours d&apos;instruction</option>
                <option value="">Tous les marchés</option>
              </Select>
            </Field>
          </div>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
            <p className="text-[0.8125rem] text-k-muted">
              {isLoading ? 'Chargement…' : `${data?.count ?? 0} marché${(data?.count ?? 0) > 1 ? 's' : ''}`}
            </p>
            <div className="flex items-center gap-2">
              {(search || propertyType || status !== 'OPEN') ? (
                <Button variant="ghost" size="sm" onClick={reset} icon={<X className="size-3.5" aria-hidden />}>
                  Réinitialiser
                </Button>
              ) : null}
              <ButtonLink to={isAuthenticated ? '/espace/entreprise' : '/espace-entreprise'} variant="secondary" size="sm">
                Déposer une candidature
              </ButtonLink>
            </div>
          </div>
        </div>
      </section>

      <Section>
        {isError ? (
          <ErrorState message="La liste des marchés n'a pas pu être chargée." onRetry={() => void refetch()} />
        ) : isLoading ? (
          <div className="space-y-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <CardSkeleton key={index} lines={4} />
            ))}
          </div>
        ) : items.length === 0 ? (
          <EmptyState
            title="Aucun marché ne correspond à ces critères"
            description="Élargissez la recherche ou affichez tous les marchés, y compris ceux en cours d'instruction."
            action={<Button onClick={reset}>Voir tous les marchés</Button>}
          />
        ) : (
          <>
            <div className="space-y-4">
              {items.map((item) => (
                <OpportunityRow key={item.id} opportunity={item} />
              ))}
            </div>
            <Pagination page={data?.page ?? 1} pages={data?.pages ?? 1} onChange={setPage} className="mt-10" />
          </>
        )}
      </Section>

      <Section tone="mist" className="!py-14">
        <SectionHeading
          eyebrow="Entreprises BTP"
          title="Comment candidater"
          description="La candidature se fait en ligne, avec une présentation, une méthodologie, un budget estimatif et un délai. Aucun dossier papier, aucune remise en main propre."
        />
        <ol className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { step: '1', title: 'Créez votre profil entreprise', text: 'Identité légale, corps d\u2019état, effectifs et matériel.' },
            { step: '2', title: 'Faites vérifier votre dossier', text: 'RCCM, attestation fiscale, CNPS et références contrôlées par KEMTA.' },
            { step: '3', title: 'Candidatez au marché', text: 'Présentation, méthodologie, budget estimatif et délai proposé.' },
            { step: '4', title: 'Recevez la décision', text: 'Présélection, visite de site éventuelle, puis attribution motivée.' },
          ].map((item) => (
            <li key={item.step} className="rounded-k-lg border border-k-line bg-white p-5">
              <span className="flex size-8 items-center justify-center rounded-full bg-k-blue font-display text-[0.8125rem] font-semibold text-white" aria-hidden>
                {item.step}
              </span>
              <p className="mt-4 font-display text-[1rem] font-semibold text-k-ink">{item.title}</p>
              <p className="mt-2 text-[0.8125rem] leading-relaxed text-k-muted">{item.text}</p>
            </li>
          ))}
        </ol>
        <div className="mt-8">
          <ButtonLink to="/espace-entreprise" size="lg">
            Inscrire mon entreprise
          </ButtonLink>
        </div>
      </Section>
    </>
  );
}
