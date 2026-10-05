import { useState } from 'react';
import { ChevronDown, MapPin, Quote, Star } from 'lucide-react';

import { Section, SectionHeading } from '@/components/layout/Section';
import { Badge } from '@/components/ui/Badge';
import { CardSkeleton, EmptyState } from '@/components/ui/Feedback';
import { usePublicContent } from '@/lib/hooks';
import { useReveal } from '@/hooks/useReveal';
import type { FaqItem } from '@/lib/types';

/* -------------------------------------------------------------- témoignages */

export function Testimonials() {
  const ref = useReveal<HTMLDivElement>();
  const { data, isLoading } = usePublicContent();
  const testimonials = data?.testimonials ?? [];

  return (
    <Section id="temoignages">
      <SectionHeading
        eyebrow="Ils ont confié un projet"
        title="Des clients au Cameroun et dans la diaspora"
        description="Aucun témoignage acheté : seuls les clients ayant un projet réellement suivi par KEMTA sont publiés."
      />

      <div ref={ref} data-reveal className="mt-12">
        {isLoading ? (
          <div className="grid gap-6 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <CardSkeleton key={index} lines={4} />
            ))}
          </div>
        ) : testimonials.length === 0 ? (
          <EmptyState
            title="Témoignages en cours de publication"
            description="Les retours de nos premiers clients suivis seront publiés après validation."
          />
        ) : (
          <div className="grid gap-6 lg:grid-cols-3">
            {testimonials.slice(0, 3).map((item) => (
              <figure
                key={item.id}
                className="flex flex-col rounded-k-lg border border-k-line bg-white p-6"
              >
                <Quote className="size-5 text-k-blue/30" aria-hidden />
                <blockquote className="mt-4 flex-1 text-[0.9375rem] leading-relaxed text-k-ink">
                  {item.quote}
                </blockquote>

                <figcaption className="mt-6 flex items-center gap-3 border-t border-k-line pt-5">
                  {item.photo_url ? (
                    <img
                      src={item.photo_url}
                      alt=""
                      loading="lazy"
                      className="size-11 shrink-0 rounded-full object-cover"
                    />
                  ) : (
                    <span
                      className="flex size-11 shrink-0 items-center justify-center rounded-full bg-k-blue-soft font-display text-[0.8125rem] font-semibold text-k-blue"
                      aria-hidden
                    >
                      {item.author_name
                        .split(' ')
                        .map((part) => part[0])
                        .slice(0, 2)
                        .join('')}
                    </span>
                  )}
                  <div className="min-w-0">
                    <p className="text-[0.875rem] font-medium text-k-ink">{item.author_name}</p>
                    <p className="text-[0.75rem] text-k-muted">
                      {item.author_role}
                      {item.author_city ? ` · ${item.author_city}` : ''}
                    </p>
                    {item.project_name ? (
                      <p className="mt-0.5 flex items-center gap-1 text-[0.6875rem] text-k-green-dark">
                        <MapPin className="size-3" aria-hidden />
                        {item.project_name}
                      </p>
                    ) : null}
                  </div>
                  {item.rating ? (
                    <span className="ml-auto inline-flex items-center gap-0.5" aria-label={`${item.rating} sur 5`}>
                      {Array.from({ length: item.rating }).map((_, index) => (
                        <Star key={index} className="size-3.5 fill-k-amber text-k-amber" aria-hidden />
                      ))}
                    </span>
                  ) : null}
                </figcaption>
              </figure>
            ))}
          </div>
        )}
      </div>
    </Section>
  );
}

/* ---------------------------------------------------------------------- FAQ */

export function Faq() {
  const ref = useReveal<HTMLDivElement>();
  const { data, isLoading } = usePublicContent();
  const [open, setOpen] = useState<string | null>(null);

  const groups: Array<[string, FaqItem[]]> = Object.entries(data?.faq ?? {});
  const total = groups.reduce((sum, [, items]) => sum + items.length, 0);

  return (
    <Section id="faq" tone="mist">
      <SectionHeading
        eyebrow="Questions fréquentes"
        title="Ce que les clients demandent avant de commencer"
        description="Délais, paiements, garanties, fonctionnement depuis l'étranger : les réponses sont écrites par l'équipe terrain, pas par un service marketing."
      />

      <div ref={ref} data-reveal className="mt-12 grid gap-10 lg:grid-cols-[1fr_1.4fr] lg:gap-16">
        <aside className="lg:sticky lg:top-24 lg:self-start">
          <Badge tone="blue" size="sm">
            {total || 0} réponses
          </Badge>
          <p className="mt-4 text-[0.9375rem] leading-relaxed text-k-muted">
            Vous ne trouvez pas votre réponse ? Écrivez-nous : un conseiller répond aux questions techniques sous 48 h
            ouvrées, sans discours commercial.
          </p>
          <a
            href="/contact"
            className="mt-4 inline-flex text-[0.875rem] font-medium text-k-blue hover:text-k-green-dark"
          >
            Poser une question à l&apos;équipe
          </a>
        </aside>

        <div>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, index) => (
                <CardSkeleton key={index} lines={2} />
              ))}
            </div>
          ) : groups.length === 0 ? (
            <EmptyState title="FAQ en cours de publication" />
          ) : (
            groups.map(([category, items]) => (
              <div key={category} className="mb-8 last:mb-0">
                <h3 className="text-[0.75rem] font-semibold uppercase tracking-wider text-k-muted">{category}</h3>
                <dl className="mt-3 divide-y divide-k-line border-y border-k-line">
                  {items.map((item) => {
                    const key = `${category}-${item.id}`;
                    const isOpen = open === key;
                    return (
                      <div key={key}>
                        <dt>
                          <button
                            type="button"
                            onClick={() => setOpen(isOpen ? null : key)}
                            aria-expanded={isOpen}
                            className="flex w-full items-start justify-between gap-4 py-4 text-left"
                          >
                            <span className="font-display text-[0.9375rem] font-semibold text-k-ink">
                              {item.question}
                            </span>
                            <ChevronDown
                              className={`mt-0.5 size-4 shrink-0 text-k-muted transition-transform ${isOpen ? 'rotate-180' : ''}`}
                              aria-hidden
                            />
                          </button>
                        </dt>
                        {isOpen ? (
                          <dd className="pb-5 pr-8 text-[0.9375rem] leading-relaxed text-k-muted">{item.answer}</dd>
                        ) : null}
                      </div>
                    );
                  })}
                </dl>
              </div>
            ))
          )}
        </div>
      </div>
    </Section>
  );
}
