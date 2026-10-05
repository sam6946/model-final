import { Link } from 'react-router-dom';
import { ArrowRight, Compass, Home, Search } from 'lucide-react';

import { Seo } from '@/components/Seo';
import { ButtonLink } from '@/components/ui/Button';

const SUGGESTIONS = [
  { to: '/', label: 'Accueil', description: 'Présentation des services KEMTA' },
  { to: '/services/suivi-chantier', label: 'Suivi de chantier', description: 'Reprendre le contrôle d\'un chantier' },
  { to: '/entreprises-btp', label: 'Entreprises BTP', description: 'Annuaire des entreprises vérifiées' },
  { to: '/opportunites', label: 'Opportunités', description: 'Marchés ouverts aux entreprises' },
  { to: '/demande', label: 'Déposer une demande', description: 'Formulaire guidé en 4 étapes' },
  { to: '/contact', label: 'Contacter un conseiller', description: 'Téléphone, WhatsApp, e-mail' },
];

export default function NotFoundPage() {
  return (
    <>
      <Seo
        title="Page introuvable"
        description="La page demandée n'existe pas ou a été déplacée. Retrouvez les services KEMTA, les entreprises BTP vérifiées et les marchés ouverts."
        path="/404"
        noIndex
      />

      <section className="border-b border-k-line bg-white">
        <div className="k-container flex flex-col items-start gap-6 py-20">
          <span className="flex size-12 items-center justify-center rounded-full bg-k-blue-soft text-k-blue" aria-hidden>
            <Compass className="size-5" />
          </span>
          <p className="font-display text-[3.5rem] font-bold leading-none text-k-blue/12">404</p>
          <h1 className="max-w-[24ch]">Cette page n&apos;existe pas ou a été déplacée</h1>
          <p className="k-lead">
            Le lien est peut-être ancien, ou l&apos;adresse contient une faute de frappe. Voici les pages les plus
            consultées de KEMTA.
          </p>
          <div className="mt-2 flex flex-wrap gap-3">
            <ButtonLink to="/" icon={<Home className="size-4" aria-hidden />}>
              Revenir à l&apos;accueil
            </ButtonLink>
            <ButtonLink to="/demande" variant="secondary">
              Déposer une demande
            </ButtonLink>
          </div>
        </div>
      </section>

      <section className="bg-k-mist">
        <div className="k-container py-14">
          <h2 className="flex items-center gap-2.5 text-[1.25rem]">
            <Search className="size-4 text-k-blue" aria-hidden />
            Pages utiles
          </h2>
          <ul className="mt-7 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {SUGGESTIONS.map((item) => (
              <li key={item.to}>
                <Link
                  to={item.to}
                  className="group flex items-center justify-between gap-4 rounded-k-lg border border-k-line bg-white px-5 py-4 transition-colors hover:border-k-blue-line"
                >
                  <span>
                    <span className="block font-display text-[0.9375rem] font-semibold text-k-ink">{item.label}</span>
                    <span className="mt-0.5 block text-[0.8125rem] text-k-muted">{item.description}</span>
                  </span>
                  <ArrowRight className="size-4 shrink-0 text-k-muted transition-transform group-hover:translate-x-0.5 group-hover:text-k-blue" aria-hidden />
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </>
  );
}
