import { Link } from 'react-router-dom';
import { ArrowRight, Check, MapPin, ShieldCheck, TriangleAlert, Wallet } from 'lucide-react';

import { ButtonLink } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { InterfaceFrame } from '@/components/ui/Media';
import { Section } from '@/components/layout/Section';
import { HERO } from '@/lib/content';
import { useReveal } from '@/hooks/useReveal';

/** Aperçu produit : l'espace de suivi tel que le client le reçoit. */
function TrackingPreview() {
  return (
    <InterfaceFrame
      title="Villa Bonapriso — Aïcha Mbarga"
      subtitle="KEMTA-PRJ-2026-00018 · Bonapriso, Douala"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex size-10 items-center justify-center rounded-k bg-k-green-pale font-display text-[0.8125rem] font-bold text-k-green-dark" aria-hidden>
            62%
          </span>
          <div>
            <p className="text-[0.8125rem] font-medium text-k-ink">Élévation et structure</p>
            <p className="text-[0.75rem] text-k-muted">Phase 4 sur 10 · dans les délais</p>
          </div>
        </div>
        <Badge tone="green" size="sm">
          Suivi actif
        </Badge>
      </div>

      <div className="mt-4 h-2 overflow-hidden rounded-full bg-k-line">
        <div className="h-full w-[62%] rounded-full bg-k-green" />
      </div>

      <dl className="mt-4 grid grid-cols-3 gap-3 border-t border-k-line pt-4">
        <div>
          <dt className="text-[0.6875rem] uppercase tracking-wide text-k-muted">Budget</dt>
          <dd className="mt-0.5 text-[0.8125rem] font-semibold text-k-ink">38 000 000 FCFA</dd>
        </div>
        <div>
          <dt className="text-[0.6875rem] uppercase tracking-wide text-k-muted">Consommé</dt>
          <dd className="mt-0.5 text-[0.8125rem] font-semibold text-k-ink">54 %</dd>
        </div>
        <div>
          <dt className="text-[0.6875rem] uppercase tracking-wide text-k-muted">Preuves</dt>
          <dd className="mt-0.5 text-[0.8125rem] font-semibold text-k-ink">18 photos</dd>
        </div>
      </dl>

      <div className="mt-4 space-y-2.5 rounded-k bg-k-mist p-3.5">
        <p className="flex items-start gap-2 text-[0.8125rem] text-k-ink">
          <ShieldCheck className="mt-0.5 size-4 shrink-0 text-k-green" aria-hidden />
          <span>
            <span className="font-medium">Preuve validée</span> — Ferraillage poteaux P4, photo horodatée du 14/03 à
            09:12.
          </span>
        </p>
        <p className="flex items-start gap-2 text-[0.8125rem] text-k-ink">
          <Wallet className="mt-0.5 size-4 shrink-0 text-k-blue" aria-hidden />
          <span>
            <span className="font-medium">Décaissement bloqué</span> — en attente de la facture ciment du lot 3.
          </span>
        </p>
        <p className="flex items-start gap-2 text-[0.8125rem] text-k-ink">
          <TriangleAlert className="mt-0.5 size-4 shrink-0 text-k-amber" aria-hidden />
          <span>
            <span className="font-medium">Point d&apos;attention</span> — livraison du sable retardée de 2 jours,
            planning ajusté.
          </span>
        </p>
      </div>
    </InterfaceFrame>
  );
}

export function Hero() {
  const ref = useReveal<HTMLDivElement>();

  return (
    <Section className="!pb-14 !pt-10 sm:!pt-14 lg:!pb-20 lg:!pt-16" containerClassName="grid gap-12 lg:grid-cols-[1.05fr_1fr] lg:items-center lg:gap-16">
      <div ref={ref} data-reveal className="flex flex-col items-start">
        <Badge tone="blue">
          <MapPin className="size-3.5" aria-hidden />
          {HERO.eyebrow}
        </Badge>

        <h1 className="mt-5 text-[2.125rem] leading-[1.08] sm:text-[2.75rem] lg:text-[3.25rem]">{HERO.title}</h1>

        <p className="mt-5 max-w-[58ch] text-[1.0625rem] leading-relaxed text-k-muted sm:text-[1.125rem]">
          {HERO.lead}
        </p>

        <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
          <ButtonLink to="/demande" size="lg" iconRight={<ArrowRight className="size-4" aria-hidden />}>
            {HERO.primaryCta}
          </ButtonLink>
          <ButtonLink to="/comment-ca-marche" variant="secondary" size="lg">
            {HERO.secondaryCta}
          </ButtonLink>
        </div>

        <p className="mt-3 text-[0.8125rem] text-k-muted">{HERO.primaryHint}</p>

        <ul className="mt-8 grid gap-2.5 sm:grid-cols-1">
          {HERO.guarantees.map((item) => (
            <li key={item} className="flex items-start gap-2.5 text-[0.875rem] text-k-ink">
              <Check className="mt-0.5 size-4 shrink-0 text-k-green" aria-hidden />
              {item}
            </li>
          ))}
        </ul>

        <p className="mt-8 text-[0.8125rem] text-k-muted">
          Déjà un projet chez KEMTA ?{' '}
          <Link to="/connexion" className="font-medium text-k-blue hover:text-k-green-dark">
            Accéder à mon espace
          </Link>
        </p>
      </div>

      <div data-reveal className="relative">
        <TrackingPreview />
        <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 px-1 text-[0.75rem] text-k-muted">
          <span className="inline-flex items-center gap-1.5">
            <span className="size-1.5 rounded-full bg-k-green" aria-hidden />
            Mise à jour il y a 2 h
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="size-1.5 rounded-full bg-k-blue" aria-hidden />
            Chargé de suivi : Clarisse E.
          </span>
        </div>
      </div>
    </Section>
  );
}
