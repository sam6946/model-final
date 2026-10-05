import { Link } from 'react-router-dom';
import { ArrowRight, Check } from 'lucide-react';

import { Section, SectionHeading } from '@/components/layout/Section';
import { Badge } from '@/components/ui/Badge';
import { SERVICES } from '@/lib/content';
import { useReveal } from '@/hooks/useReveal';

/** Les quatre métiers KEMTA — la porte d'entrée du parcours client. */
export function Services() {
  const ref = useReveal<HTMLDivElement>();

  return (
    <Section id="services">
      <SectionHeading
        eyebrow="Nos métiers"
        title="Quatre services, un même niveau d'exigence"
        description="Chaque mission est encadrée par un chargé de suivi KEMTA, documentée par des preuves terrain et facturée sans coût caché."
        action={
          <Link
            to="/tarifs"
            className="inline-flex items-center gap-1.5 text-[0.875rem] font-medium text-k-blue hover:text-k-green-dark"
          >
            Voir les tarifs
            <ArrowRight className="size-4" aria-hidden />
          </Link>
        }
      />

      <div ref={ref} data-reveal className="mt-12 grid gap-6 lg:grid-cols-2">
        {SERVICES.map((service) => {
          const Icon = service.icon;
          return (
            <article
              key={service.slug}
              className="group flex flex-col rounded-k-lg border border-k-line bg-white p-6 transition-colors hover:border-k-blue-line sm:p-7"
            >
              <div className="flex items-start justify-between gap-4">
                <span
                  className="flex size-11 items-center justify-center rounded-k bg-k-blue-soft text-k-blue transition-colors group-hover:bg-k-blue group-hover:text-white"
                  aria-hidden
                >
                  <Icon className="size-5" />
                </span>
                <Badge tone="neutral" size="sm">
                  {service.startingPrice}
                </Badge>
              </div>

              <h3 className="mt-5 text-[1.25rem]">{service.title}</h3>
              <p className="mt-1.5 font-medium text-[0.9375rem] text-k-green-dark">{service.promise}</p>
              <p className="mt-3 text-[0.9375rem] leading-relaxed text-k-muted">{service.description}</p>

              <ul className="mt-5 space-y-2.5">
                {service.bullets.map((bullet) => (
                  <li key={bullet} className="flex items-start gap-2.5 text-[0.875rem] text-k-ink">
                    <Check className="mt-0.5 size-4 shrink-0 text-k-green" aria-hidden />
                    {bullet}
                  </li>
                ))}
              </ul>

              <div className="mt-6 flex flex-wrap gap-3 border-t border-k-line pt-5">
                <Link
                  to={`/services/${service.slug}`}
                  className="inline-flex items-center gap-1.5 text-[0.875rem] font-medium text-k-blue hover:text-k-green-dark"
                >
                  Déroulé complet
                  <ArrowRight className="size-3.5" aria-hidden />
                </Link>
                <Link
                  to={`/demande?service=${service.slug}`}
                  className="inline-flex items-center gap-1.5 text-[0.875rem] font-medium text-k-ink hover:text-k-blue"
                >
                  Demander ce service
                </Link>
              </div>
            </article>
          );
        })}
      </div>
    </Section>
  );
}
