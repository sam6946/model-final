import { ArrowRight, PhoneCall } from 'lucide-react';

import { ButtonLink } from '@/components/ui/Button';
import { Media } from '@/components/ui/Media';

/**
 * Appel à l'action final : une seule décision à prendre, deux chemins clairs
 * (déposer une demande ou parler à un conseiller), sans urgence artificielle.
 */
export function FinalCta() {
  return (
    <section className="border-t border-k-line bg-white">
      <div className="k-container grid gap-10 py-16 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:gap-16 lg:py-20">
        <div>
          <span className="k-eyebrow">
            <span className="h-px w-8 bg-k-green" aria-hidden />
            Prochaine étape
          </span>
          <h2 className="mt-5 max-w-[22ch] text-balance">
            Racontez-nous votre projet, nous nous occupons du reste.
          </h2>
          <p className="k-lead mt-5">
            Décrivez votre besoin en 4 étapes. Un chargé de suivi KEMTA vous rappelle sous 48 heures ouvrées
            avec une première analyse et une estimation de budget — sans engagement.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
            <ButtonLink to="/demande" size="lg" iconRight={<ArrowRight className="size-4" aria-hidden />}>
              Démarrer ma demande
            </ButtonLink>
            <a
              href="tel:+237600000000"
              className="inline-flex h-13 items-center justify-center gap-2 rounded-k border border-k-line px-6 text-base font-medium text-k-ink transition-colors hover:border-k-blue-line hover:bg-k-mist"
            >
              <PhoneCall className="size-4 text-k-green" aria-hidden />
              +237 600 000 000
            </a>
          </div>

          <ul className="mt-8 grid gap-3 text-[0.875rem] text-k-muted sm:grid-cols-3">
            <li>Réponse sous 48 h ouvrées</li>
            <li>Devis écrit avant tout engagement</li>
            <li>Vos données ne sont jamais revendues</li>
          </ul>
        </div>

        <Media
          name="villa-livree"
          alt="Villa moderne livrée par une entreprise du réseau KEMTA, Cameroun"
          ratio="4 / 3"
          sizes="(min-width: 1024px) 42vw, 100vw"
          className="rounded-k-xl"
        />
      </div>
    </section>
  );
}
