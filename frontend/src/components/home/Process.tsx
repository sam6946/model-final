import { Link } from 'react-router-dom';
import { ArrowRight, CalendarClock, Camera, MapPin, ShieldCheck } from 'lucide-react';

import { Section, SectionHeading } from '@/components/layout/Section';
import { Badge } from '@/components/ui/Badge';
import { ButtonLink } from '@/components/ui/Button';
import { Media } from '@/components/ui/Media';
import { HOW_IT_WORKS, TRACKING_PILLARS } from '@/lib/content';
import { useReveal } from '@/hooks/useReveal';

/** Le parcours client, du formulaire à la preuve hebdomadaire. */
export function HowItWorks() {
  const ref = useReveal<HTMLDivElement>();

  return (
    <Section id="comment-ca-marche" tone="mist">
      <SectionHeading
        eyebrow="Comment ça marche"
        title="De votre première description à la remise des clés"
        description="Un parcours balisé, avec des délais annoncés et un interlocuteur identifié à chaque étape."
      />

      <div ref={ref} data-reveal className="mt-12 grid gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-4">
        {HOW_IT_WORKS.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.step} className="relative flex flex-col">
              <div className="flex items-center gap-3">
                <span className="font-display text-[1.5rem] font-bold text-k-blue/25" aria-hidden>
                  {item.step}
                </span>
                <span className="flex size-9 items-center justify-center rounded-k bg-white text-k-blue shadow-k-sm" aria-hidden>
                  <Icon className="size-4" />
                </span>
              </div>
              <h3 className="mt-4 text-[1.0625rem]">{item.title}</h3>
              <p className="mt-2 text-[0.9375rem] leading-relaxed text-k-muted">{item.description}</p>
              <p className="mt-3 inline-flex items-center gap-1.5 text-[0.75rem] font-medium text-k-green-dark">
                <CalendarClock className="size-3.5" aria-hidden />
                {item.duration}
              </p>
            </div>
          );
        })}
      </div>

      <div className="mt-12 flex flex-wrap items-center gap-4 rounded-k-lg border border-k-blue-line bg-white p-5">
        <ShieldCheck className="size-5 shrink-0 text-k-green" aria-hidden />
        <p className="flex-1 text-[0.9375rem] text-k-ink">
          Vous restez propriétaire de votre projet et de vos documents. KEMTA ne signe ni ne paie à votre place sans
          validation écrite.
        </p>
        <ButtonLink to="/confiance" variant="secondary" size="sm">
          Nos engagements
        </ButtonLink>
      </div>
    </Section>
  );
}

/** Suivi de chantier : la promesse centrale, illustrée par la réalité terrain. */
export function Tracking() {
  const ref = useReveal<HTMLDivElement>();

  return (
    <Section id="suivi-chantier">
      <div className="grid gap-12 lg:grid-cols-[1fr_1.05fr] lg:items-center lg:gap-16">
        <div ref={ref} data-reveal>
          <Badge tone="green">
            <Camera className="size-3.5" aria-hidden />
            Suivi de chantier
          </Badge>
          <h2 className="mt-5 text-[1.875rem] sm:text-[2.25rem]">
            Vous ne croyez plus les rapports verbaux. Nous non plus.
          </h2>
          <p className="mt-4 text-[1.0625rem] leading-relaxed text-k-muted">
            Un chantier déclaré « à 80 % » peut n&apos;être qu&apos;un trou entouré de parpaings. KEMTA découpe le
            chantier en phases pondérées, visite le site selon un calendrier connu de vous, et publie des preuves
            horodatées que vous pouvez comparer d&apos;une semaine à l&apos;autre.
          </p>

          <div className="mt-8 space-y-5">
            {TRACKING_PILLARS.map((pillar) => {
              const Icon = pillar.icon;
              return (
                <div key={pillar.title} className="flex gap-4">
                  <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-k bg-k-blue-soft text-k-blue" aria-hidden>
                    <Icon className="size-4" />
                  </span>
                  <div>
                    <h3 className="text-[1rem] font-display font-semibold text-k-ink">{pillar.title}</h3>
                    <p className="mt-1 text-[0.9375rem] leading-relaxed text-k-muted">{pillar.description}</p>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-8 flex flex-wrap gap-3">
            <ButtonLink to="/demande?service=suivi-chantier" iconRight={<ArrowRight className="size-4" aria-hidden />}>
              Reprendre le suivi de mon chantier
            </ButtonLink>
            <Link
              to="/services/suivi-chantier"
              className="inline-flex items-center gap-1.5 self-center text-[0.875rem] font-medium text-k-blue hover:text-k-green-dark"
            >
              Ce que comprend la mission
              <ArrowRight className="size-3.5" aria-hidden />
            </Link>
          </div>
        </div>

        <div data-reveal className="relative">
          <Media
            name="hero-suivi-chantier"
            alt="Chargé de suivi KEMTA consultant l'avancement du chantier sur son téléphone, Douala"
            ratio="4 / 5"
            sizes="(min-width: 1024px) 46vw, 100vw"
            className="mx-auto w-full max-w-[30rem]"
          />
          <div className="mt-5 rounded-k-lg border border-k-line bg-white p-5 shadow-k-sm sm:absolute sm:-bottom-8 sm:-left-8 sm:mt-0 sm:max-w-[19rem]">
            <p className="flex items-center gap-2 text-[0.75rem] font-medium uppercase tracking-wide text-k-muted">
              <MapPin className="size-3.5 text-k-green" aria-hidden />
              Preuve du jour
            </p>
            <p className="mt-2 text-[0.875rem] leading-relaxed text-k-ink">
              Fondations coulées — semelles et longrines contrôlées, niveaux vérifiés au niveau de chantier.
            </p>
            <p className="mt-3 text-[0.75rem] text-k-muted">Photo horodatée · technicien identifié · phase 3/10</p>
          </div>
        </div>
      </div>
    </Section>
  );
}
