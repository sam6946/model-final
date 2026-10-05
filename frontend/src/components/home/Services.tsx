import { Link } from 'react-router-dom';
import { ArrowRight, Check } from 'lucide-react';

import { SERVICES } from '@/lib/content';
import { Section, SectionHeading } from '@/components/layout/Section';

/** Les quatre prestations KEMTA, présentées avec leur promesse et leur contenu réel. */
export function Services() {
  return (
    <Section id="services">
      <SectionHeading
        eyebrow="Nos prestations"
        title="Quatre façons de confier votre projet à KEMTA"
        description="Chaque mission est cadrée par un devis écrit, suivie par un chargé de suivi dédié et documentée par des preuves que vous pouvez consulter à tout moment."
      />

      <div className="mt-12 grid gap-6 md:grid-cols-2">
        {SERVICES.map((service, index) => {
          const Icon = service.icon;
          const featured = index === 0;
          return (
            <article
              key={service.slug}
              className={`group flex flex-col rounded-k-lg border p-6 transition-all duration-300 sm:p-7 ${
                featured
                  ? 'border-k-blue-line bg-k-blue-soft/40 hover:border-k-blue/40'
                  : 'border-k-line bg-white hover:border-k-blue-line hover:shadow-k'
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <span
                  className={`flex size-11 items-center justify-center rounded-k ${
                    featured ? 'bg-k-blue text-white' : 'bg-k-blue-soft text-k-blue'
                  }`}
                  aria-hidden
                >
                  <Icon className="size-5" />
                </span>
                <span className="rounded-full border border-k-line bg-white px-3 py-1 text-[0.6875rem] font-medium text-k-muted">
                  {service.startingPrice}
                </span>
              </div>

              <p className="mt-5 text-[0.75rem] font-semibold uppercase tracking-[0.12em] text-k-green-dark">
                {service.promise}
              </p>
              <h3 className="mt-2">{service.title}</h3>
              <p className="mt-3 text-[0.9375rem] leading-relaxed text-k-muted">{service.description}</p>

              <ul className="mt-5 space-y-2.5">
                {service.bullets.map((bullet) => (
                  <li key={bullet} className="flex items-start gap-2.5 text-[0.875rem] text-k-ink/85">
                    <Check className="mt-0.5 size-4 shrink-0 text-k-green" aria-hidden />
                    {bullet}
                  </li>
                ))}
              </ul>

              <div className="mt-6 flex items-center justify-between border-t border-k-line pt-5">
                <Link
                  to={`/services/${service.slug}`}
                  className="inline-flex items-center gap-1.5 text-[0.875rem] font-medium text-k-blue transition-colors hover:text-k-green-dark"
                >
                  Découvrir la prestation
                  <ArrowRight className="size-3.5 transition-transform duration-200 group-hover:translate-x-0.5" aria-hidden />
                </Link>
                <Link
                  to={`/demande?service=${service.slug}`}
                  className="text-[0.8125rem] text-k-muted underline decoration-k-line underline-offset-4 transition-colors hover:text-k-blue"
                >
                  Demander
                </Link>
              </div>
            </article>
          );
        })}
      </div>
    </Section>
  );
}
