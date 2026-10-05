import { Quote, Star } from 'lucide-react';

import { usePublicContent } from '@/lib/hooks';
import { Section, SectionHeading } from '@/components/layout/Section';
import { Accordion } from '@/components/ui/Accordion';
import { CardSkeleton, EmptyState } from '@/components/ui/Feedback';
import { initials } from '@/lib/format';

/** Témoignages : uniquement des clients avec un projet suivi, jamais de faux avis. */
export function Testimonials() {
  const { data, isLoading } = usePublicContent();
  const items = (data?.testimonials ?? []).slice(0, 3);

  return (
    <Section id="temoignages" tone="mist">
      <SectionHeading
        eyebrow="Ils ont confié leur projet"
        title="Ce que disent nos clients, ici et dans la diaspora"
        description="Les avis publiés proviennent de clients dont le projet est suivi sur KEMTA : impossibles à acheter."
      />

      <div className="mt-10 grid gap-6 lg:grid-cols-3">
        {isLoading
          ? Array.from({ length: 3 }).map((_, index) => <CardSkeleton key={index} lines={5} />)
          : items.map((testimonial) => (
              <figure
                key={testimonial.id}
                className="flex flex-col rounded-k-lg border border-k-line bg-white p-6"
              >
                <Quote className="size-6 text-k-blue/25" aria-hidden />

                <blockquote className="mt-4 flex-1 text-[0.9375rem] leading-relaxed text-k-ink/90">
                  « {testimonial.quote} »
                </blockquote>

                <figcaption className="mt-6 flex items-center gap-3 border-t border-k-line pt-5">
                  {testimonial.photo_url ? (
                    <img
                      src={testimonial.photo_url}
                      alt={testimonial.author_name}
                      loading="lazy"
                      className="size-11 rounded-full object-cover"
                    />
                  ) : (
                    <span
                      className="flex size-11 items-center justify-center rounded-full bg-k-blue-soft font-display text-sm font-semibold text-k-blue"
                      aria-hidden
                    >
                      {initials(testimonial.author_name)}
                    </span>
                  )}
                  <div className="min-w-0">
                    <p className="truncate text-[0.875rem] font-semibold text-k-ink">{testimonial.author_name}</p>
                    <p className="truncate text-[0.75rem] text-k-muted">
                      {testimonial.author_role}
                      {testimonial.author_city ? ` · ${testimonial.author_city}` : ''}
                    </p>
                  </div>
                  <span className="ml-auto flex shrink-0 gap-0.5" aria-label={`Note ${testimonial.rating} sur 5`}>
                    {Array.from({ length: testimonial.rating }).map((_, index) => (
                      <Star key={index} className="size-3.5 fill-k-green text-k-green" aria-hidden />
                    ))}
                  </span>
                </figcaption>
              </figure>
            ))}

        {!isLoading && items.length === 0 ? (
          <div className="lg:col-span-3">
            <EmptyState
              title="Les premiers témoignages arrivent"
              description="Nous publions un avis seulement après la réception des travaux d'un client suivi par KEMTA."
            />
          </div>
        ) : null}
      </div>
    </Section>
  );
}

/** FAQ : les objections réelles, avec des réponses précises. */
export function Faq() {
  const { data, isLoading } = usePublicContent();
  const grouped = data?.faq ?? {};
  const items = Object.values(grouped)
    .flat()
    .sort((a, b) => a.order - b.order)
    .map((item) => ({ id: item.id, question: item.question, answer: item.answer }));

  return (
    <Section id="faq">
      <div className="grid gap-12 lg:grid-cols-[0.85fr_1.15fr] lg:gap-16">
        <div>
          <SectionHeading
            eyebrow="Questions fréquentes"
            title="Les réponses avant de nous confier votre projet"
            description="Si votre question n'y figure pas, un conseiller vous répond sous 48 heures ouvrées — par téléphone ou WhatsApp."
          />
          <div className="mt-8 rounded-k-lg border border-k-line bg-k-mist p-5">
            <p className="font-display text-[0.9375rem] font-semibold text-k-ink">Parler à un conseiller</p>
            <p className="mt-1.5 text-[0.875rem] leading-relaxed text-k-muted">
              Lundi au samedi, 7 h 30 – 18 h 30 (heure de Douala).
            </p>
            <div className="mt-4 flex flex-col gap-2 text-[0.875rem]">
              <a href="tel:+237600000000" className="font-medium text-k-blue hover:text-k-green-dark">
                +237 600 000 000
              </a>
              <a
                href="https://wa.me/237600000000"
                target="_blank"
                rel="noreferrer"
                className="font-medium text-k-blue hover:text-k-green-dark"
              >
                Écrire sur WhatsApp
              </a>
            </div>
          </div>
        </div>

        <div>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, index) => (
                <CardSkeleton key={index} lines={2} />
              ))}
            </div>
          ) : (
            <Accordion items={items} />
          )}
        </div>
      </div>
    </Section>
  );
}
