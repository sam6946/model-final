import { BellRing, Camera, FileText, Lock, MapPin, Receipt, Wallet } from 'lucide-react';

import { FINANCIAL_CONTROL } from '@/lib/content';
import { Section, SectionHeading } from '@/components/layout/Section';
import { Media } from '@/components/ui/Media';
import { Badge } from '@/components/ui/Badge';
import { ButtonLink } from '@/components/ui/Button';

/** Espace client : à quoi ressemble réellement le suivi, écran par écran. */
export function DashboardPreview() {
  return (
    <Section id="espace-client" tone="blue" className="k-grid-lines">
      <div className="grid gap-12 lg:grid-cols-[1fr_1.05fr] lg:items-center lg:gap-16">
        <div>
          <SectionHeading
            tone="light"
            eyebrow="Votre espace client"
            title="Tout votre projet sur un seul écran"
            description="Un tableau de bord agrégé : avancement, budget, prochaines visites, dernières preuves, demandes en cours et notifications. Une seule page à ouvrir, même en 3G."
          />

          <ul className="mt-8 space-y-5">
            {[
              {
                icon: Wallet,
                title: 'Budget et dépenses en direct',
                text: 'Ce qui est engagé, ce qui est payé, ce qui reste : poste par poste.',
              },
              {
                icon: Camera,
                title: 'Dernières preuves terrain',
                text: 'Photos horodatées, technicien, phase concernée, validation par l\'équipe.',
              },
              {
                icon: BellRing,
                title: 'Alertes utiles uniquement',
                text: 'Retard, dépassement, pièce manquante, visite planifiée. Pas de notification inutile.',
              },
              {
                icon: FileText,
                title: 'Rapports et documents',
                text: 'Comptes rendus de visite, rapports périodiques et factures, téléchargeables.',
              },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <li key={item.title} className="flex gap-4">
                  <span className="flex size-10 shrink-0 items-center justify-center rounded-k bg-white/10 text-white" aria-hidden>
                    <Icon className="size-4" />
                  </span>
                  <div>
                    <p className="font-display text-[1rem] font-semibold text-white">{item.title}</p>
                    <p className="mt-1 text-[0.875rem] leading-relaxed text-white/75">{item.text}</p>
                  </div>
                </li>
              );
            })}
          </ul>

          <ButtonLink to="/connexion" variant="secondary" size="lg" className="mt-9">
            Accéder à mon espace
          </ButtonLink>
        </div>

        {/* Représentation fidèle du tableau de bord client */}
        <div className="rounded-k-xl border border-white/15 bg-white p-4 shadow-k-lg sm:p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-display text-[0.9375rem] font-semibold text-k-ink">Bonjour Aïcha</p>
              <p className="text-[0.75rem] text-k-muted">Vos projets et votre patrimoine</p>
            </div>
            <Badge tone="green" size="sm">
              <Lock className="size-3" aria-hidden />
              Session sécurisée
            </Badge>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            {[
              { label: 'Projets suivis', value: '2' },
              { label: 'Budget engagé', value: '23,4 M' },
              { label: 'Prochaine visite', value: 'Ven. 09 h' },
            ].map((item) => (
              <div key={item.label} className="rounded-k border border-k-line bg-k-mist px-3.5 py-3">
                <p className="text-[0.6875rem] uppercase tracking-wide text-k-muted">{item.label}</p>
                <p className="mt-1 font-display text-[1.0625rem] font-semibold text-k-ink">{item.value}</p>
              </div>
            ))}
          </div>

          <div className="mt-4 rounded-k border border-k-line p-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-[0.875rem] font-medium text-k-ink">Villa Bonapriso — R+1</p>
              <Badge tone="blue" size="sm">En cours</Badge>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-k-line">
              <div className="h-full w-[62%] rounded-full bg-k-green" />
            </div>
            <div className="mt-2 flex items-center justify-between text-[0.6875rem] text-k-muted">
              <span>62 % d&apos;avancement pondéré</span>
              <span>Réception prévue en avril 2027</span>
            </div>
          </div>

          <ul className="mt-4 space-y-2.5">
            {[
              { icon: Camera, text: 'Coulage de la dalle haute — 4 photos', meta: 'il y a 2 jours' },
              { icon: Receipt, text: 'Facture matériaux n° 2026-0148 réglée', meta: 'il y a 5 jours' },
              { icon: MapPin, text: 'Visite de contrôle planifiée — Bonapriso', meta: 'vendredi 09 h' },
            ].map((row) => {
              const Icon = row.icon;
              return (
                <li key={row.text} className="flex items-center gap-3 rounded-k bg-k-mist px-3.5 py-2.5">
                  <Icon className="size-4 shrink-0 text-k-blue" aria-hidden />
                  <span className="flex-1 truncate text-[0.8125rem] text-k-ink">{row.text}</span>
                  <span className="shrink-0 text-[0.6875rem] text-k-muted">{row.meta}</span>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </Section>
  );
}

/** Preuves terrain : ce qui rend la promesse vérifiable. */
export function Evidence() {
  return (
    <Section id="preuves-terrain" tone="mist">
      <div className="grid gap-12 lg:grid-cols-2 lg:items-center lg:gap-16">
        <div className="order-2 lg:order-1">
          <Media
            name="preuve-terrain"
            alt="Technicien KEMTA photographiant des fondations fraîchement coulées sur un chantier à Douala"
            ratio="5 / 4"
            sizes="(min-width: 1024px) 48vw, 100vw"
            className="rounded-k-xl"
          />

          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {[
              { label: 'Horodatage', value: '12/09/2026 · 08:41' },
              { label: 'Coordonnées GPS', value: '4.0522 N · 9.7025 E' },
              { label: 'Technicien', value: 'Achille Fotso · KEMTA' },
              { label: 'Phase contrôlée', value: 'Fondations & soubassement' },
            ].map((item) => (
              <div key={item.label} className="rounded-k border border-k-line bg-white px-3.5 py-2.5">
                <p className="text-[0.6875rem] uppercase tracking-wide text-k-muted">{item.label}</p>
                <p className="mt-0.5 text-[0.8125rem] font-medium text-k-ink">{item.value}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="order-1 lg:order-2">
          <SectionHeading
            eyebrow="Preuves terrain"
            title="Une photo ne suffit pas : il faut qu'elle soit datée, située et vérifiée"
            description="Un chantier peut être photographié avec une belle lumière alors que rien n'a été fait. KEMTA impose une chaîne de preuve : qui est allé sur place, quand, à quel endroit précis, et ce que l'équipe a validé ensuite."
          />

          <ul className="mt-8 space-y-5">
            {[
              {
                title: 'Photos horodatées et géolocalisées',
                text: 'Chaque prise de vue conserve l\'heure, les coordonnées, l\'auteur et la phase du chantier.',
              },
              {
                title: 'Validation en deux temps',
                text: 'Le technicien publie, l\'équipe KEMTA contrôle et valide avant que le client ne la voie comme définitive.',
              },
              {
                title: 'Photos avant / après',
                text: 'Pour chaque intervention, vous comparez l\'état initial et le résultat — y compris en entretien.',
              },
              {
                title: 'Synchronisation hors ligne',
                text: 'Sur un chantier sans réseau, le technicien saisit puis synchronise : aucune preuve ne se perd.',
              },
            ].map((item) => (
              <li key={item.title} className="flex gap-4 border-t border-k-line pt-5 first:border-t-0 first:pt-0">
                <span className="mt-1 size-2 shrink-0 rounded-full bg-k-green" aria-hidden />
                <div>
                  <p className="font-display text-[1rem] font-semibold text-k-ink">{item.title}</p>
                  <p className="mt-1 text-[0.875rem] leading-relaxed text-k-muted">{item.text}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Section>
  );
}

/** Contrôle financier : le budget, le poste le plus sensible pour la diaspora. */
export function FinancialControl() {
  return (
    <Section id="controle-financier">
      <div className="grid gap-12 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:gap-16">
        <div>
          <SectionHeading
            eyebrow="Contrôle financier"
            title="Votre argent ne part pas sans contrepartie"
            description="Sur un chantier classique, 30 % du budget se perd en paiements non justifiés. KEMTA rattache chaque franc dépensé à un poste, une phase et une preuve."
          />

          <div className="mt-9 grid gap-x-8 gap-y-6 sm:grid-cols-2">
            {FINANCIAL_CONTROL.map((item) => (
              <div key={item.title}>
                <h3 className="text-[1rem]">{item.title}</h3>
                <p className="mt-2 text-[0.875rem] leading-relaxed text-k-muted">{item.description}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-k-xl border border-k-line bg-white p-5 shadow-k sm:p-6">
          <div className="flex items-center justify-between">
            <p className="font-display text-[0.9375rem] font-semibold text-k-ink">Répartition du budget</p>
            <span className="text-[0.75rem] text-k-muted">Villa R+1 · 38 000 000 FCFA</span>
          </div>

          <ul className="mt-5 space-y-4">
            {[
              { label: 'Matériaux', percent: 45, amount: '17 100 000' },
              { label: "Main-d'œuvre", percent: 30, amount: '11 400 000' },
              { label: 'Études & plans', percent: 7, amount: '2 660 000' },
              { label: 'Transport', percent: 8, amount: '3 040 000' },
              { label: 'Location matériel', percent: 5, amount: '1 900 000' },
              { label: 'Administratif', percent: 5, amount: '1 900 000' },
            ].map((line) => (
              <li key={line.label}>
                <div className="flex items-baseline justify-between gap-3">
                  <span className="text-[0.875rem] font-medium text-k-ink">{line.label}</span>
                  <span className="text-[0.8125rem] text-k-muted">{line.amount} FCFA</span>
                </div>
                <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-k-line">
                  <div className="h-full rounded-full bg-k-blue" style={{ width: `${line.percent}%` }} />
                </div>
              </li>
            ))}
          </ul>

          <div className="mt-6 space-y-2.5 border-t border-k-line pt-5 text-[0.8125rem]">
            <div className="flex items-center justify-between">
              <span className="text-k-muted">Engagé à ce jour</span>
              <span className="font-medium text-k-ink">23 400 000 FCFA</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-k-muted">Solde disponible</span>
              <span className="font-medium text-k-green-dark">14 600 000 FCFA</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-k-muted">Consommation du budget</span>
              <span className="font-medium text-k-ink">61,6 %</span>
            </div>
          </div>

          <p className="mt-5 rounded-k bg-k-green-pale px-3.5 py-3 text-[0.8125rem] leading-relaxed text-k-green-dark">
            Prochain décaissement conditionné à la validation de l&apos;élévation des murs et au rapport de
            visite.
          </p>
        </div>
      </div>
    </Section>
  );
}
