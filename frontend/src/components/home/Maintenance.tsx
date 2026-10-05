import { ArrowRight, CalendarCheck, Wrench } from 'lucide-react';

import { Section, SectionHeading } from '@/components/layout/Section';
import { Badge } from '@/components/ui/Badge';
import { ButtonLink } from '@/components/ui/Button';
import { Media } from '@/components/ui/Media';
import { MAINTENANCE_STEPS } from '@/lib/content';
import { useReveal } from '@/hooks/useReveal';

/** Entretien de propriété : le service qui fidélise les propriétaires. */
export function Maintenance() {
  const ref = useReveal<HTMLDivElement>();

  return (
    <Section id="entretien">
      <SectionHeading
        eyebrow="Entretien & patrimoine"
        title="Votre maison reste vivante, même quand vous êtes à l'étranger"
        description="Un bien non visité se dégrade en silence : infiltration, citerne fissurée, portail forcé, locataire qui décroche. KEMTA passe, contrôle, répare et vous dit ce qui a changé."
        action={
          <ButtonLink to="/demande?service=entretien-propriete" size="sm">
            Planifier un entretien
          </ButtonLink>
        }
      />

      <div className="mt-12 grid gap-12 lg:grid-cols-[1.05fr_1fr] lg:items-center lg:gap-16">
        <div ref={ref} data-reveal className="order-2 lg:order-1">
          <Media
            name="inspection-propriete"
            alt="Technicien KEMTA inspectant l'escalier extérieur et la citerne d'un immeuble locatif à Douala"
            ratio="16 / 10"
            sizes="(min-width: 1024px) 48vw, 100vw"
          />
        </div>

        <div data-reveal className="order-1 lg:order-2">
          <div className="flex flex-wrap gap-2">
            <Badge tone="blue" size="sm">
              <CalendarCheck className="size-3.5" aria-hidden />
              Mensuel → annuel
            </Badge>
            <Badge tone="neutral" size="sm">
              <Wrench className="size-3.5" aria-hidden />
              Interventions suivies
            </Badge>
          </div>

          <ol className="mt-7 space-y-6">
            {MAINTENANCE_STEPS.map((step, index) => (
              <li key={step.title} className="flex gap-4">
                <span
                  className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-k-green-pale font-display text-[0.75rem] font-bold text-k-green-dark"
                  aria-hidden
                >
                  {index + 1}
                </span>
                <div>
                  <h3 className="text-[1rem] font-display font-semibold text-k-ink">{step.title}</h3>
                  <p className="mt-1 text-[0.9375rem] leading-relaxed text-k-muted">{step.description}</p>
                </div>
              </li>
            ))}
          </ol>

          <div className="mt-8 rounded-k-lg border border-k-line bg-k-mist p-5">
            <p className="text-[0.875rem] leading-relaxed text-k-ink">
              <span className="font-medium">Carnet d&apos;entretien numérique :</span> chaque bien conserve son
              historique — réparations, coûts, photos avant/après, prochaine échéance. Un atout le jour où vous
              louez, vendez ou transmettez.
            </p>
            <a
              href="/services/entretien-propriete"
              className="mt-3 inline-flex items-center gap-1.5 text-[0.875rem] font-medium text-k-blue hover:text-k-green-dark"
            >
              Voir le service entretien
              <ArrowRight className="size-3.5" aria-hidden />
            </a>
          </div>
        </div>
      </div>
    </Section>
  );
}
