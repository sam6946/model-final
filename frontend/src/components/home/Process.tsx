import { ArrowRight, CalendarCheck, ShieldCheck, TrendingUp } from 'lucide-react';

import { HOW_IT_WORKS, TRACKING_PILLARS } from '@/lib/content';
import { Section, SectionHeading } from '@/components/layout/Section';
import { Media } from '@/components/ui/Media';
import { ButtonLink } from '@/components/ui/Button';

/** Comment ça marche : le parcours complet, du formulaire à la livraison. */
export function HowItWorks() {
  return (
    <Section id="comment-ca-marche" tone="mist">
      <SectionHeading
        eyebrow="Comment ça marche"
        title="De votre demande à la remise des clés"
        description="Un parcours linéaire, sans zone d'ombre : vous savez à chaque instant ce qui a été fait, ce qui reste à faire et combien cela coûte."
      />

      <ol className="mt-12 grid gap-y-10 md:grid-cols-2 md:gap-x-10 lg:grid-cols-4 lg:gap-x-8">
        {HOW_IT_WORKS.map((step, index) => {
          const Icon = step.icon;
          return (
            <li key={step.step} className="relative flex flex-col">
              <div className="flex items-center gap-3">
                <span className="font-display text-[2rem] font-bold leading-none text-k-blue/15">{step.step}</span>
                <span className="flex size-9 items-center justify-center rounded-k border border-k-line bg-white text-k-blue" aria-hidden>
                  <Icon className="size-4" />
                </span>
              </div>

              <h3 className="mt-5 text-[1.0625rem]">{step.title}</h3>
              <p className="mt-2.5 text-[0.875rem] leading-relaxed text-k-muted">{step.description}</p>

              <span className="mt-4 inline-flex w-fit items-center gap-1.5 rounded-full bg-white px-2.5 py-1 text-[0.6875rem] font-medium text-k-blue">
                <CalendarCheck className="size-3" aria-hidden />
                {step.duration}
              </span>

              {index < HOW_IT_WORKS.length - 1 ? (
                <ArrowRight
                  className="absolute -right-6 top-3 hidden size-4 text-k-line lg:block"
                  aria-hidden
                />
              ) : null}
            </li>
          );
        })}
      </ol>

      <div className="mt-12 flex flex-col items-start gap-3 sm:flex-row sm:items-center">
        <ButtonLink to="/demande" iconRight={<ArrowRight className="size-4" aria-hidden />}>
          Commencer ma demande
        </ButtonLink>
        <p className="text-[0.8125rem] text-k-muted">
          Le formulaire vous prend 6 minutes. Vous pouvez l&apos;interrompre et reprendre plus tard.
        </p>
      </div>
    </Section>
  );
}

/** Suivi de chantier : la promesse centrale du produit, appuyée par la photographie terrain. */
export function Tracking() {
  return (
    <Section id="suivi-chantier">
      <div className="grid gap-12 lg:grid-cols-[0.95fr_1.05fr] lg:items-center lg:gap-16">
        <div className="relative">
          <Media
            name="hero-suivi-chantier"
            alt="Chargé de suivi KEMTA consultant l'avancement du chantier sur son téléphone, Douala"
            ratio="4 / 5"
            sizes="(min-width: 1024px) 45vw, 100vw"
            className="rounded-k-xl"
          />
          <div className="mt-4 grid grid-cols-2 gap-3 sm:absolute sm:-right-6 sm:bottom-8 sm:mt-0 sm:w-64 sm:grid-cols-1">
            <div className="rounded-k border border-k-line bg-white p-3.5 shadow-k">
              <p className="flex items-center gap-2 text-[0.6875rem] uppercase tracking-wide text-k-muted">
                <TrendingUp className="size-3.5 text-k-green" aria-hidden />
                Avancement réel
              </p>
              <p className="mt-1.5 font-display text-xl font-bold text-k-ink">62 %</p>
              <p className="text-[0.6875rem] text-k-muted">Moyenne pondérée des phases</p>
            </div>
            <div className="rounded-k border border-k-line bg-white p-3.5 shadow-k">
              <p className="flex items-center gap-2 text-[0.6875rem] uppercase tracking-wide text-k-muted">
                <ShieldCheck className="size-3.5 text-k-green" aria-hidden />
                Dernière preuve
              </p>
              <p className="mt-1.5 text-[0.8125rem] font-medium text-k-ink">Dalle haute coulée</p>
              <p className="text-[0.6875rem] text-k-muted">Validée hier · 4 photos</p>
            </div>
          </div>
        </div>

        <div>
          <SectionHeading
            eyebrow="Suivi de chantier"
            title="Vous voyez ce qui se passe réellement sur le terrain"
            description="KEMTA n'envoie pas un rapport commercial : nos techniciens se rendent sur site, photographient, mesurent et consignent. Vous recevez l'information brute, avec le nom de celui qui l'a relevée."
          />

          <div className="mt-9 grid gap-6 sm:grid-cols-2">
            {TRACKING_PILLARS.map((pillar) => {
              const Icon = pillar.icon;
              return (
                <div key={pillar.title} className="border-t border-k-line pt-5">
                  <span className="flex size-9 items-center justify-center rounded-k bg-k-green-pale text-k-green-dark" aria-hidden>
                    <Icon className="size-4" />
                  </span>
                  <h3 className="mt-4 text-[1rem]">{pillar.title}</h3>
                  <p className="mt-2 text-[0.875rem] leading-relaxed text-k-muted">{pillar.description}</p>
                </div>
              );
            })}
          </div>

          <div className="mt-9 rounded-k-lg border border-k-blue-line bg-k-blue-soft/50 p-5">
            <p className="text-[0.9375rem] font-medium text-k-ink">
              Chantier déjà commencé et entreprise injoignable ?
            </p>
            <p className="mt-1.5 text-[0.875rem] leading-relaxed text-k-muted">
              Nous réalisons un audit d&apos;avancement sous 5 jours ouvrés : ce qui a été payé, ce qui a été
              exécuté, ce qui manque. Puis nous reprenons le suivi, ou nous vous aidons à passer à une autre
              entreprise.
            </p>
            <ButtonLink to="/services/suivi-chantier" variant="secondary" size="sm" className="mt-4">
              Demander un audit de chantier
            </ButtonLink>
          </div>
        </div>
      </div>
    </Section>
  );
}
