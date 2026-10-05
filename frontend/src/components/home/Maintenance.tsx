import { ArrowRight, CalendarDays, Droplets, ShieldAlert, Trees } from 'lucide-react';

import { MAINTENANCE_STEPS } from '@/lib/content';
import { Section, SectionHeading } from '@/components/layout/Section';
import { Media } from '@/components/ui/Media';
import { ButtonLink } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

/** Entretien de propriété : le service qui protège un patrimoine laissé au pays. */
export function Maintenance() {
  return (
    <Section id="entretien" tone="mist">
      <div className="grid gap-12 lg:grid-cols-[1fr_1fr] lg:items-center lg:gap-16">
        <div>
          <SectionHeading
            eyebrow="Entretien & patrimoine"
            title="Une maison non entretenue perd de la valeur chaque année"
            description="Vous vivez à Douala, Yaoundé, Paris ou Montréal : votre bien continue de vieillir sans vous. KEMTA passe, vérifie, répare et vous envoie la preuve."
          />

          <ol className="mt-9 space-y-6">
            {MAINTENANCE_STEPS.map((step, index) => (
              <li key={step.title} className="flex gap-4">
                <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-k-blue text-[0.75rem] font-semibold text-white" aria-hidden>
                  {index + 1}
                </span>
                <div>
                  <p className="font-display text-[1rem] font-semibold text-k-ink">{step.title}</p>
                  <p className="mt-1 text-[0.875rem] leading-relaxed text-k-muted">{step.description}</p>
                </div>
              </li>
            ))}
          </ol>

          <div className="mt-9 flex flex-wrap gap-3">
            <ButtonLink to="/services/entretien-propriete" size="md">
              Voir l&apos;offre d&apos;entretien
            </ButtonLink>
            <ButtonLink to="/demande?service=entretien-propriete" variant="secondary" size="md">
              Demander une visite
            </ButtonLink>
          </div>
        </div>

        <div className="space-y-4">
          <Media
            name="inspection-propriete"
            alt="Technicien KEMTA inspectant l'escalier extérieur et la citerne d'un immeuble locatif à Douala"
            ratio="16 / 10"
            sizes="(min-width: 1024px) 48vw, 100vw"
            className="rounded-k-xl"
          />

          <div className="rounded-k-lg border border-k-line bg-white p-4 sm:p-5">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <CalendarDays className="size-4 text-k-blue" aria-hidden />
                <p className="text-[0.875rem] font-medium text-k-ink">Visite trimestrielle — Immeuble Akwa</p>
              </div>
              <Badge tone="green" size="sm">Réalisée</Badge>
            </div>

            <ul className="mt-4 grid gap-3 sm:grid-cols-3">
              {[
                { icon: Droplets, label: 'Plomberie', state: 'Citerne nettoyée, vanne remplacée' },
                { icon: ShieldAlert, label: 'Sécurité', state: 'Serrures et éclairage conformes' },
                { icon: Trees, label: 'Extérieurs', state: 'Enclos et cour dégagés' },
              ].map((item) => {
                const Icon = item.icon;
                return (
                  <li key={item.label} className="rounded-k bg-k-mist px-3.5 py-3">
                    <span className="flex items-center gap-2 text-[0.6875rem] uppercase tracking-wide text-k-muted">
                      <Icon className="size-3.5 text-k-green" aria-hidden />
                      {item.label}
                    </span>
                    <p className="mt-1.5 text-[0.8125rem] leading-snug text-k-ink">{item.state}</p>
                  </li>
                );
              })}
            </ul>

            <div className="mt-4 flex flex-col gap-3 border-t border-k-line pt-4 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-[0.8125rem] text-k-muted">
                2 réparations mineures réalisées · 1 devis en attente de votre validation
              </p>
              <a
                href="#entretien"
                className="inline-flex items-center gap-1.5 text-[0.8125rem] font-medium text-k-blue hover:text-k-green-dark"
              >
                Voir le compte rendu complet
                <ArrowRight className="size-3.5" aria-hidden />
              </a>
            </div>
          </div>
        </div>
      </div>
    </Section>
  );
}
