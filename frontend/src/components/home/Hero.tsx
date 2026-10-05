import { ArrowRight, Camera, Check, MapPin, ShieldCheck } from 'lucide-react';

import { HERO } from '@/lib/content';
import { ButtonLink } from '@/components/ui/Button';
import { InterfaceFrame } from '@/components/ui/Media';
import { Badge } from '@/components/ui/Badge';

/** Aperçu de l'espace client : montre le produit plutôt que de le décrire. */
function SitePreview() {
  const phases = [
    { name: 'Fondations & soubassement', progress: 100, done: true },
    { name: 'Élévation des murs', progress: 72, done: false },
    { name: 'Charpente & toiture', progress: 15, done: false },
  ];

  return (
    <InterfaceFrame
      title="Villa Bonapriso — R+1"
      subtitle="Suivi KEMTA · mise à jour il y a 2 jours"
      className="w-full"
    >
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <Badge tone="green" size="sm">
            <ShieldCheck className="size-3" aria-hidden />
            Preuve validée
          </Badge>
          <span className="text-[0.6875rem] text-k-muted">Avancement global</span>
          <span className="font-display text-lg font-bold text-k-ink">62 %</span>
        </div>

        <div className="h-2 overflow-hidden rounded-full bg-k-line">
          <div className="h-full w-[62%] rounded-full bg-k-green" />
        </div>

        <ul className="space-y-2.5">
          {phases.map((phase) => (
            <li key={phase.name} className="flex items-center gap-3">
              <span
                className={`flex size-5 shrink-0 items-center justify-center rounded-full text-[0.625rem] font-semibold ${
                  phase.done ? 'bg-k-green text-white' : 'bg-k-blue-soft text-k-blue'
                }`}
                aria-hidden
              >
                {phase.done ? <Check className="size-3" /> : `${phase.progress}`}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[0.8125rem] font-medium text-k-ink">{phase.name}</p>
                <div className="mt-1 h-1 overflow-hidden rounded-full bg-k-line">
                  <div
                    className={`h-full rounded-full ${phase.done ? 'bg-k-green' : 'bg-k-blue'}`}
                    style={{ width: `${phase.progress}%` }}
                  />
                </div>
              </div>
              <span className="w-9 shrink-0 text-right text-[0.6875rem] text-k-muted">{phase.progress} %</span>
            </li>
          ))}
        </ul>

        <div className="grid grid-cols-2 gap-2 border-t border-k-line pt-3.5">
          <div className="rounded-k bg-k-mist px-3 py-2">
            <p className="text-[0.625rem] uppercase tracking-wide text-k-muted">Budget engagé</p>
            <p className="font-display text-[0.9375rem] font-semibold text-k-ink">23 400 000 FCFA</p>
          </div>
          <div className="rounded-k bg-k-mist px-3 py-2">
            <p className="text-[0.625rem] uppercase tracking-wide text-k-muted">Prochaine visite</p>
            <p className="font-display text-[0.9375rem] font-semibold text-k-ink">Vendredi 09 h</p>
          </div>
        </div>

        <div className="flex items-center gap-2.5 rounded-k border border-k-line bg-white px-3 py-2.5">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-k-sm bg-k-green-pale text-k-green-dark" aria-hidden>
            <Camera className="size-4" />
          </span>
          <div className="min-w-0">
            <p className="truncate text-[0.8125rem] font-medium text-k-ink">
              4 photos · Coulage de la dalle haute
            </p>
            <p className="flex items-center gap-1 text-[0.6875rem] text-k-muted">
              <MapPin className="size-3" aria-hidden />
              Bonapriso, Douala · technicien A. Fotso
            </p>
          </div>
        </div>
      </div>
    </InterfaceFrame>
  );
}

export function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-k-line bg-white">
      {/* Trame technique discrète, aucun dégradé décoratif. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-64 bg-[linear-gradient(to_right,rgba(6,59,92,0.05)_1px,transparent_1px),linear-gradient(to_bottom,rgba(6,59,92,0.05)_1px,transparent_1px)] bg-[size:48px_48px] [mask-image:linear-gradient(to_bottom,black,transparent)]"
      />

      <div className="k-container relative grid gap-12 py-14 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16 lg:py-24">
        <div className="flex flex-col justify-center gap-7">
          <p className="k-eyebrow">
            <span className="h-px w-8 bg-k-green" aria-hidden />
            {HERO.eyebrow}
          </p>

          <h1 className="max-w-[20ch]">{HERO.title}</h1>

          <p className="k-lead">{HERO.lead}</p>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <ButtonLink
              to="/demande"
              size="lg"
              iconRight={<ArrowRight className="size-4" aria-hidden />}
            >
              {HERO.primaryCta}
            </ButtonLink>
            <ButtonLink to="/comment-ca-marche" variant="secondary" size="lg">
              {HERO.secondaryCta}
            </ButtonLink>
          </div>

          <p className="text-[0.8125rem] text-k-muted">{HERO.primaryHint}</p>

          <ul className="flex flex-col gap-2.5 border-t border-k-line pt-6 sm:flex-row sm:flex-wrap sm:gap-x-6">
            {HERO.guarantees.map((item) => (
              <li key={item} className="flex items-center gap-2 text-[0.8125rem] text-k-ink/80">
                <Check className="size-3.5 shrink-0 text-k-green" aria-hidden />
                {item}
              </li>
            ))}
          </ul>
        </div>

        <div className="relative flex items-center lg:justify-end">
          <SitePreview />
        </div>
      </div>
    </section>
  );
}
