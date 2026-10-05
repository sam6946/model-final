import { Link } from 'react-router-dom';
import { Clock, Mail, MapPin, Phone, ShieldCheck } from 'lucide-react';

import { BrandWordmark } from './Brand';

const COLUMNS = [
  {
    title: 'Services',
    links: [
      { to: '/services/construire', label: 'Construire avec KEMTA' },
      { to: '/services/suivi-chantier', label: 'Suivre un chantier en cours' },
      { to: '/services/entretien-propriete', label: 'Entretenir une propriété' },
      { to: '/demande', label: 'Déposer une demande' },
    ],
  },
  {
    title: 'Écosystème',
    links: [
      { to: '/entreprises-btp', label: 'Entreprises BTP vérifiées' },
      { to: '/realisations', label: 'Réalisations livrées' },
      { to: '/opportunites', label: 'Marchés & opportunités' },
      { to: '/espace-entreprise', label: 'Rejoindre le réseau BTP' },
    ],
  },
  {
    title: 'KEMTA',
    links: [
      { to: '/comment-ca-marche', label: 'Comment ça marche' },
      { to: '/tarifs', label: 'Offres et tarifs' },
      { to: '/confiance', label: 'Transparence & sécurité' },
      { to: '/contact', label: 'Contacter un conseiller' },
    ],
  },
];

export function Footer() {
  return (
    <footer className="border-t border-k-line bg-k-blue text-white">
      <div className="k-container py-14">
        <div className="grid gap-12 lg:grid-cols-[1.15fr_2fr]">
          <div className="space-y-5">
            <BrandWordmark tone="white" />
            <p className="max-w-sm text-[0.9375rem] leading-relaxed text-white/75">
              KEMTA suit votre construction, votre chantier en cours et votre patrimoine au Cameroun :
              preuves photo horodatées, budget contrôlé, entreprises BTP vérifiées.
            </p>
            <ul className="space-y-2.5 text-[0.875rem] text-white/80">
              <li className="flex items-center gap-2.5">
                <MapPin className="size-4 shrink-0 text-k-green" aria-hidden />
                <span>
                  Bafoussam — Quartier Administratif (siège)
                  <br />
                  <span className="text-white/60">Douala &amp; Yaoundé — permanences sur rendez-vous</span>
                </span>
              </li>
              <li className="flex items-center gap-2.5">
                <Phone className="size-4 shrink-0 text-k-green" aria-hidden />
                <a href="tel:+237600000000" className="hover:text-white">
                  +237 600 000 000
                </a>
                <span className="text-white/50">·</span>
                <a
                  href="https://wa.me/237600000000"
                  className="hover:text-white"
                  target="_blank"
                  rel="noreferrer"
                >
                  WhatsApp
                </a>
              </li>
              <li className="flex items-center gap-2.5">
                <Mail className="size-4 shrink-0 text-k-green" aria-hidden />
                <a href="mailto:contact@kemta.cm" className="hover:text-white">
                  contact@kemta.cm
                </a>
              </li>
              <li className="flex items-center gap-2.5">
                <Clock className="size-4 shrink-0 text-k-green" aria-hidden />
                Lundi — samedi, 7 h 30 à 18 h 30
              </li>
            </ul>
          </div>

          <div className="grid gap-8 sm:grid-cols-3">
            {COLUMNS.map((column) => (
              <div key={column.title}>
                <p className="font-display text-[0.8125rem] font-semibold uppercase tracking-[0.12em] text-white/60">
                  {column.title}
                </p>
                <ul className="mt-4 space-y-2.5">
                  {column.links.map((link) => (
                    <li key={link.to}>
                      <Link
                        to={link.to}
                        className="text-[0.875rem] text-white/80 transition-colors hover:text-white"
                      >
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-12 flex flex-col gap-4 border-t border-white/12 pt-6 text-[0.8125rem] text-white/60 sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} KEMTA SARL — Bafoussam, Cameroun. Tous droits réservés.</p>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
            <span className="inline-flex items-center gap-1.5">
              <ShieldCheck className="size-3.5 text-k-green" aria-hidden />
              Paiement sécurisé · Mobile Money & carte
            </span>
            <Link to="/confiance" className="hover:text-white">
              Confidentialité
            </Link>
            <Link to="/confiance" className="hover:text-white">
              Conditions d'utilisation
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
