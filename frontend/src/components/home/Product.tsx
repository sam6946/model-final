import { useState } from 'react';
import { ArrowRight, Camera, Check, ClipboardList, MapPin, Receipt, ShieldCheck, WifiOff } from 'lucide-react';

import { Section, SectionHeading } from '@/components/layout/Section';
import { Badge } from '@/components/ui/Badge';
import { ButtonLink } from '@/components/ui/Button';
import { InterfaceFrame, Media } from '@/components/ui/Media';
import { FINANCIAL_CONTROL } from '@/lib/content';
import { useReveal } from '@/hooks/useReveal';

/* ------------------------------------------------------------------ espace */

const TABS = [
  { id: 'chantier', label: 'Chantier' },
  { id: 'budget', label: 'Budget' },
  { id: 'preuves', label: 'Preuves' },
] as const;

type TabId = (typeof TABS)[number]['id'];

function TabChantier() {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-display text-[0.9375rem] font-semibold text-k-ink">Villa R+1 — 320 m²</p>
          <p className="text-[0.75rem] text-k-muted">KEMTA-PRJ-2026-00018 · Makepe, Douala</p>
        </div>
        <Badge tone="blue" size="sm">
          Phase 4/10 · Élévation
        </Badge>
      </div>

      <ol className="space-y-2.5">
        {[
          { name: 'Étude, plans et autorisations', state: 'done', value: '100 %' },
          { name: 'Terrassement et fondations', state: 'done', value: '100 %' },
          { name: 'Élévation et structure', state: 'current', value: '48 %' },
          { name: 'Dallage et planchers', state: 'next', value: '0 %' },
        ].map((phase) => (
          <li key={phase.name} className="flex items-center gap-3">
            <span
              className={`flex size-6 shrink-0 items-center justify-center rounded-full text-[0.625rem] font-semibold ${
                phase.state === 'done'
                  ? 'bg-k-green text-white'
                  : phase.state === 'current'
                    ? 'bg-k-blue text-white'
                    : 'bg-k-line text-k-muted'
              }`}
              aria-hidden
            >
              {phase.state === 'done' ? <Check className="size-3.5" /> : phase.value.replace(' %', '')}
            </span>
            <span className="flex-1 truncate text-[0.8125rem] text-k-ink">{phase.name}</span>
            <span className="text-[0.75rem] text-k-muted">{phase.value}</span>
          </li>
        ))}
      </ol>

      <p className="rounded-k bg-k-mist px-3.5 py-2.5 text-[0.75rem] text-k-muted">
        Prochaine visite KEMTA planifiée vendredi · chargé de suivi Clarisse Etoundi
      </p>
    </div>
  );
}

function TabBudget() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-[0.6875rem] uppercase tracking-wide text-k-muted">Budget validé</p>
          <p className="mt-0.5 font-display text-[1.125rem] font-bold text-k-ink">38 000 000</p>
        </div>
        <div>
          <p className="text-[0.6875rem] uppercase tracking-wide text-k-muted">Consommé</p>
          <p className="mt-0.5 font-display text-[1.125rem] font-bold text-k-ink">20 520 000</p>
        </div>
      </div>

      <ul className="space-y-3">
        {[
          { label: 'Matériaux', spent: 68, budget: '17 100 000' },
          { label: "Main-d'œuvre", spent: 41, budget: '11 400 000' },
          { label: 'Transport & location', spent: 22, budget: '4 940 000' },
          { label: 'Études & administratif', spent: 100, budget: '4 560 000' },
        ].map((line) => (
          <li key={line.label}>
            <div className="flex items-center justify-between text-[0.75rem]">
              <span className="text-k-ink">{line.label}</span>
              <span className="text-k-muted">{line.budget} FCFA</span>
            </div>
            <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-k-line">
              <div
                className={`h-full rounded-full ${line.spent >= 90 ? 'bg-k-amber' : 'bg-k-green'}`}
                style={{ width: `${line.spent}%` }}
              />
            </div>
          </li>
        ))}
      </ul>

      <p className="rounded-k bg-k-amber-pale px-3.5 py-2.5 text-[0.75rem] text-k-ink">
        Poste « Études » intégralement consommé : les dépenses suivantes seront refusées sans avenant validé.
      </p>
    </div>
  );
}

function TabPreuves() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-2.5">
        {['Fondations', 'Poteaux P4', 'Dalle haute'].map((label, index) => (
          <div key={label} className="overflow-hidden rounded-k border border-k-line">
            <div
              className={`h-16 ${index === 1 ? 'bg-k-blue-line' : 'bg-k-mist'}`}
              aria-hidden
              style={{
                backgroundImage:
                  'repeating-linear-gradient(135deg, rgba(6,59,92,0.08) 0 6px, transparent 6px 12px)',
              }}
            />
            <p className="px-2 py-1.5 text-[0.6875rem] text-k-muted">{label}</p>
          </div>
        ))}
      </div>

      <ul className="space-y-2.5 text-[0.8125rem]">
        <li className="flex items-start gap-2 text-k-ink">
          <Camera className="mt-0.5 size-4 shrink-0 text-k-green" aria-hidden />
          Ferraillage poteaux P4 — validé le 14/03 à 09:12 (3 photos, coordonnées GPS relevées)
        </li>
        <li className="flex items-start gap-2 text-k-ink">
          <ClipboardList className="mt-0.5 size-4 shrink-0 text-k-blue" aria-hidden />
          Rapport hebdomadaire n°12 — envoyé au client et à l&apos;entreprise
        </li>
        <li className="flex items-start gap-2 text-k-ink">
          <WifiOff className="mt-0.5 size-4 shrink-0 text-k-muted" aria-hidden />
          Preuve capturée hors réseau à Nkolbisson, synchronisée dès le retour de connexion
        </li>
      </ul>
    </div>
  );
}

/** Espace client : ce que le client voit réellement, écran par écran. */
export function DashboardPreview() {
  const [tab, setTab] = useState<TabId>('chantier');
  const ref = useReveal<HTMLDivElement>();

  return (
    <Section id="espace-client" tone="blue">
      <div className="grid gap-12 lg:grid-cols-[0.95fr_1.05fr] lg:items-center lg:gap-16">
        <div ref={ref} data-reveal>
          <Badge tone="outline">
            <span className="!text-white/80">Espace client KEMTA</span>
          </Badge>
          <h2 className="mt-5 text-[1.875rem] text-white sm:text-[2.25rem]">
            Tout votre projet sur un seul écran, accessible au Cameroun comme à l&apos;étranger
          </h2>
          <p className="mt-4 text-[1.0625rem] leading-relaxed text-white/75">
            Avancement par phase, budget engagé, preuves photo, prochaines visites, documents et factures : votre
            espace est la source de vérité du chantier. Il fonctionne sur un téléphone modeste et une connexion
            instable — les preuves capturées hors réseau se synchronisent au retour de la connexion.
          </p>

          <ul className="mt-8 space-y-3">
            {[
              'Aucune application à installer : l’espace fonctionne dans le navigateur',
              'Alertes dès qu’un écart de budget ou de planning est détecté',
              'Historique complet conservé, même après la réception des travaux',
              'Chaque accès est journalisé et limité à vos projets',
            ].map((item) => (
              <li key={item} className="flex items-start gap-2.5 text-[0.9375rem] text-white/85">
                <Check className="mt-0.5 size-4 shrink-0 text-k-green" aria-hidden />
                {item}
              </li>
            ))}
          </ul>

          <div className="mt-8">
            <ButtonLink to="/demande" variant="secondary" size="lg" iconRight={<ArrowRight className="size-4" aria-hidden />}>
              Ouvrir une demande
            </ButtonLink>
          </div>
        </div>

        <div data-reveal>
          <div className="mb-4 flex flex-wrap gap-2" role="tablist" aria-label="Aperçu de l'espace client">
            {TABS.map((item) => (
              <button
                key={item.id}
                type="button"
                role="tab"
                aria-selected={tab === item.id}
                onClick={() => setTab(item.id)}
                className={`rounded-k px-3.5 py-2 text-[0.8125rem] font-medium transition-colors ${
                  tab === item.id ? 'bg-white text-k-blue' : 'bg-white text-k-blue/60 hover:bg-white'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>

          <InterfaceFrame title="Mon projet — suivi KEMTA" subtitle="Aperçu de l'espace client">
            {tab === 'chantier' ? <TabChantier /> : tab === 'budget' ? <TabBudget /> : <TabPreuves />}
          </InterfaceFrame>
        </div>
      </div>
    </Section>
  );
}

/** Contrôle financier : la partie qui rassure la diaspora. */
export function FinancialControl() {
  const ref = useReveal<HTMLDivElement>();

  return (
    <Section id="controle-financier">
      <div className="grid gap-12 lg:grid-cols-[1fr_1fr] lg:items-start lg:gap-16">
        <div ref={ref} data-reveal>
          <Badge tone="amber">
            <Receipt className="size-3.5" aria-hidden />
            Contrôle financier
          </Badge>
          <h2 className="mt-5 text-[1.875rem] sm:text-[2.25rem]">
            L&apos;argent ne part jamais sans preuve
          </h2>
          <p className="mt-4 text-[1.0625rem] leading-relaxed text-k-muted">
            La majorité des chantiers dérapent sur la gestion, pas sur la technique. KEMTA décaisse par étape
            validée : sans photo conforme et facture rattachée, le paiement suivant est bloqué et vous êtes alerté.
          </p>

          <div className="mt-8">
            <Media
              name="preuve-terrain"
              alt="Technicien KEMTA photographiant des fondations fraîchement coulées sur un chantier à Douala"
              ratio="5 / 4"
              sizes="(min-width: 1024px) 46vw, 100vw"
            />
          </div>
        </div>

        <div data-reveal className="grid gap-5 sm:grid-cols-2 lg:mt-16 lg:grid-cols-1">
          {FINANCIAL_CONTROL.map((item, index) => (
            <div key={item.title} className="rounded-k-lg border border-k-line bg-white p-5">
              <div className="flex items-start gap-4">
                <span
                  className="flex size-9 shrink-0 items-center justify-center rounded-k bg-k-green-pale font-display text-[0.8125rem] font-bold text-k-green-dark"
                  aria-hidden
                >
                  {String(index + 1).padStart(2, '0')}
                </span>
                <div>
                  <h3 className="text-[1rem] font-display font-semibold text-k-ink">{item.title}</h3>
                  <p className="mt-1.5 text-[0.9375rem] leading-relaxed text-k-muted">{item.description}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Section>
  );
}

/** Preuves terrain : la section qui matérialise la promesse. */
export function Evidence() {
  const ref = useReveal<HTMLDivElement>();

  return (
    <Section id="preuves-terrain" tone="mist">
      <SectionHeading
        eyebrow="Preuves terrain"
        title="Une photo datée vaut mieux qu'un rapport de trois pages"
        description="Chaque visite produit un dossier de preuve : photos, coordonnées, technicien, phase concernée et observations. Vous comparez, vous validez, vous contestez si besoin."
      />

      <div ref={ref} data-reveal className="mt-12 grid gap-8 lg:grid-cols-3">
        {[
          {
            title: 'Ce qui est vérifié',
            items: [
              'Quantités livrées sur site (ciment, fer, sable, gravier)',
              'Conformité du ferraillage et des sections avant coulage',
              'Niveaux, aplombs et épaisseurs des ouvrages',
              'Étanchéité, réseaux et évacuations avant fermeture',
            ],
          },
          {
            title: 'Ce que vous recevez',
            items: [
              'Photos horodatées, avec le nom du technicien',
              'Rapport hebdomadaire en français clair',
              'Alerte immédiate en cas d’écart ou d’arrêt de chantier',
              'Récapitulatif des dépenses rattachées aux preuves',
            ],
          },
          {
            title: 'Ce que KEMTA refuse',
            items: [
              'Payer une étape sans preuve conforme',
              'Valider un avancement déclaratif sans visite',
              'Laisser un désordre structurel sans signalement écrit',
              'Modifier un devis sans votre accord écrit',
            ],
          },
        ].map((column) => (
          <div key={column.title} className="rounded-k-lg border border-k-line bg-white p-6">
            <h3 className="flex items-center gap-2 text-[1.0625rem]">
              <ShieldCheck className="size-4 text-k-blue" aria-hidden />
              {column.title}
            </h3>
            <ul className="mt-4 space-y-2.5">
              {column.items.map((item) => (
                <li key={item} className="flex items-start gap-2.5 text-[0.875rem] leading-relaxed text-k-ink">
                  <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-k-green" aria-hidden />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <p className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-2 text-[0.8125rem] text-k-muted">
        <span className="inline-flex items-center gap-1.5">
          <MapPin className="size-3.5" aria-hidden />
          Position relevée à la capture, jamais modifiable après envoi
        </span>
        <span className="inline-flex items-center gap-1.5">
          <WifiOff className="size-3.5" aria-hidden />
          Capture possible hors réseau, synchronisation automatique ensuite
        </span>
      </p>
    </Section>
  );
}
