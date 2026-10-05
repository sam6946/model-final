import { ArrowRight, CalendarClock, Phone } from 'lucide-react';

import { Section } from '@/components/layout/Section';
import { ButtonLink } from '@/components/ui/Button';
import { Media } from '@/components/ui/Media';
import { usePublicContent } from '@/lib/hooks';
import { useReveal } from '@/hooks/useReveal';

/**
 * Appel à l'action final.
 * Le numéro de téléphone reste celui du backend (source unique de vérité) :
 * changer la ligne support ne demande aucun redéploiement du frontend.
 */
export function FinalCta() {
  const ref = useReveal<HTMLDivElement>();
  const { data } = usePublicContent();
  const supportPhone = data?.trust_stats?.find((stat) => stat.icon === 'phone')?.hint;

  return (
    <Section id="demarrer" tone="blue" className="!py-16 sm:!py-20">
      <div ref={ref} data-reveal className="grid gap-12 lg:grid-cols-[1.05fr_1fr] lg:items-center lg:gap-16">
        <div>
          <h2 className="text-[1.875rem] text-white sm:text-[2.375rem]">
            Décrivez votre projet aujourd&apos;hui, suivez-le dès demain.
          </h2>
          <p className="mt-4 max-w-[54ch] text-[1.0625rem] leading-relaxed text-white/75">
            Le formulaire prend six minutes. Un conseiller KEMTA vous rappelle sous 48 heures ouvrées pour qualifier le
            besoin, vérifier le terrain et vous annoncer un budget réaliste. Vous restez libre de refuser à tout
            moment.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
            <ButtonLink to="/demande" variant="secondary" size="lg" iconRight={<ArrowRight className="size-4" aria-hidden />}>
              Démarrer ma demande
            </ButtonLink>
            <a
              href={supportPhone ? `tel:${supportPhone.replace(/\s/g, '')}` : '/contact'}
              className="inline-flex items-center gap-2 text-[0.9375rem] font-medium text-white/85 transition-colors hover:text-white"
            >
              <Phone className="size-4" aria-hidden />
              {supportPhone ? `Appeler le ${supportPhone}` : 'Parler à un conseiller'}
            </a>
          </div>

          <p className="mt-4 flex items-center gap-2 text-[0.8125rem] text-white/60">
            <CalendarClock className="size-3.5" aria-hidden />
            Réponse d&apos;un conseiller sous 48 h ouvrées · devis sans engagement
          </p>
        </div>

        <div className="relative">
          <Media
            name="villa-livree"
            alt="Villa moderne livrée par KEMTA à Douala, façade claire et toiture anthracite"
            ratio="4 / 3"
            sizes="(min-width: 1024px) 46vw, 100vw"
          />
          <div className="mt-4 grid grid-cols-3 gap-4 text-white">
            <div>
              <p className="font-display text-[1.375rem] font-bold">48 h</p>
              <p className="mt-1 text-[0.75rem] text-white/70">pour être rappelé</p>
            </div>
            <div>
              <p className="font-display text-[1.375rem] font-bold">0 FCFA</p>
              <p className="mt-1 text-[0.75rem] text-white/70">avant le devis</p>
            </div>
            <div>
              <p className="font-display text-[1.375rem] font-bold">100 %</p>
              <p className="mt-1 text-[0.75rem] text-white/70">des dépenses justifiées</p>
            </div>
          </div>
        </div>
      </div>
    </Section>
  );
}
