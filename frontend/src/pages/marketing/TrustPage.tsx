import { Database, Eye, Fingerprint, KeyRound, Lock, Receipt, ShieldCheck, Smartphone, UserCog } from 'lucide-react';

import { Seo } from '@/components/Seo';
import { Section, SectionHeading } from '@/components/layout/Section';
import { ButtonLink } from '@/components/ui/Button';
import { TRUST_COMMITMENTS } from '@/lib/content';
import { breadcrumbSchema } from '@/lib/seo';
import { Alert } from '@/components/ui/Feedback';

const SECURITY_POINTS = [
  {
    icon: Smartphone,
    title: 'Authentification par SMS à usage unique',
    text: "La création de compte et la connexion passent par un code envoyé par SMS sur votre numéro. Le code expire en 5 minutes, il est limité en nombre d'essais et son renvoi est temporisé.",
  },
  {
    icon: KeyRound,
    title: 'Sessions courtes et révocables',
    text: "Les jetons d'accès expirent rapidement et sont rafraîchis automatiquement. Une déconnexion révoque immédiatement la session côté serveur.",
  },
  {
    icon: UserCog,
    title: 'Rôles et permissions vérifiés côté serveur',
    text: "Chaque action est contrôlée par l'API : un client ne peut pas lire le chantier d'un autre, une entreprise ne voit que ses propres dossiers, et une candidature ne peut être instruite que par l'équipe KEMTA.",
  },
  {
    icon: Receipt,
    title: 'Paiements idempotents',
    text: "Chaque paiement porte une clé unique : une relance réseau ne peut pas provoquer un double débit. Les webhooks des opérateurs Mobile Money sont signés et dédupliqués.",
  },
  {
    icon: Database,
    title: 'Fichiers stockés avec des URL signées',
    text: "Les photos de chantier et documents sont déposés dans un stockage objet, organisés par dossier et non listables publiquement. Les liens de partage sont temporaires.",
  },
  {
    icon: Eye,
    title: 'Traçabilité des accès sensibles',
    text: "Les actions sensibles (vérification d'entreprise, validation de preuve, examen de document) sont journalisées avec l'auteur, la date et le motif.",
  },
];

export default function TrustPage() {
  return (
    <>
      <Seo
        title="Confiance, transparence et sécurité"
        description="Comment KEMTA protège vos données, vos paiements et la preuve de vos chantiers : authentification SMS, permissions serveur, paiements idempotents, stockage sécurisé et journal d'audit."
        path="/confiance"
        jsonLd={breadcrumbSchema([
          { name: 'Accueil', path: '/' },
          { name: 'Confiance & sécurité', path: '/confiance' },
        ])}
      />

      <section className="border-b border-k-line bg-white">
        <div className="k-container py-14 lg:py-20">
          <span className="k-eyebrow">
            <span className="h-px w-8 bg-k-green" aria-hidden />
            Confiance & sécurité
          </span>
          <h1 className="mt-5 max-w-[26ch]">La confiance ne se déclare pas : elle se prouve</h1>
          <p className="k-lead mt-5">
            Nous manipulons des informations sensibles : votre argent, vos titres, les photos de votre bien et
            l&apos;identité des entreprises. Voici, sans jargon, ce que nous mettons en place.
          </p>
        </div>
      </section>

      <Section>
        <SectionHeading
          eyebrow="Nos engagements clients"
          title="Quatre promesses tenues sur chaque dossier"
        />
        <div className="mt-10 grid gap-x-10 gap-y-8 sm:grid-cols-2 lg:grid-cols-4">
          {TRUST_COMMITMENTS.map((item) => {
            const Icon = item.icon;
            return (
              <div key={item.title} className="border-t border-k-line pt-5">
                <span className="flex size-9 items-center justify-center rounded-k bg-k-green-pale text-k-green-dark" aria-hidden>
                  <Icon className="size-4" />
                </span>
                <h3 className="mt-4 text-[1rem]">{item.title}</h3>
                <p className="mt-2 text-[0.875rem] leading-relaxed text-k-muted">{item.description}</p>
              </div>
            );
          })}
        </div>
      </Section>

      <Section tone="mist">
        <div className="grid gap-12 lg:grid-cols-[0.85fr_1.15fr] lg:gap-16">
          <SectionHeading
            eyebrow="Sécurité technique"
            title="Ce que cela signifie concrètement"
            description="Un exemple simple : un technicien de terrain peut publier une preuve sur son téléphone sans réseau ; une fois en ligne, la preuve est synchronisée, contrôlée, puis publiée au client."
          />

          <div className="grid gap-6 sm:grid-cols-2">
            {SECURITY_POINTS.map((point) => {
              const Icon = point.icon;
              return (
                <div key={point.title} className="rounded-k-lg border border-k-line bg-white p-5">
                  <span className="flex size-9 items-center justify-center rounded-k bg-k-blue-soft text-k-blue" aria-hidden>
                    <Icon className="size-4" />
                  </span>
                  <h3 className="mt-4 text-[0.9375rem]">{point.title}</h3>
                  <p className="mt-2 text-[0.8125rem] leading-relaxed text-k-muted">{point.text}</p>
                </div>
              );
            })}
          </div>
        </div>
      </Section>

      <Section>
        <div className="grid gap-12 lg:grid-cols-2 lg:gap-16">
          <div>
            <SectionHeading eyebrow="Vos données" title="Ce que nous stockons, et pourquoi" />
            <dl className="mt-8 divide-y divide-k-line">
              {[
                {
                  term: 'Identité et contact',
                  detail:
                    "Nom, numéro de téléphone, ville, e-mail si vous le fournissez. Nécessaires pour créer votre compte, vous joindre et établir les documents contractuels.",
                },
                {
                  term: 'Données de projet',
                  detail:
                    "Adresse du chantier ou du bien, plans, photos, rapports, budgets. Utilisées uniquement pour assurer la mission confiée.",
                },
                {
                  term: 'Données de paiement',
                  detail:
                    "Nous ne stockons aucune donnée bancaire. Les paiements Mobile Money sont traités par les opérateurs ; nous conservons la référence, le montant et le statut de la transaction.",
                },
                {
                  term: 'Trace technique',
                  detail:
                    "Journaux d'accès et d'audit, conservés pour la sécurité et la résolution de litiges, puis purgés selon notre politique de rétention.",
                },
              ].map((row) => (
                <div key={row.term} className="py-5">
                  <dt className="font-display text-[1rem] font-semibold text-k-ink">{row.term}</dt>
                  <dd className="mt-1.5 text-[0.875rem] leading-relaxed text-k-muted">{row.detail}</dd>
                </div>
              ))}
            </dl>

            <Alert tone="info" title="Vos droits" className="mt-8">
              Vous pouvez demander une copie de vos données, la correction d&apos;une information inexacte ou la
              suppression de votre compte en écrivant à <strong>privacy@kemta.cm</strong>. Nous répondons sous 15
              jours ouvrables.
            </Alert>
          </div>

          <div className="space-y-6">
            <div className="rounded-k-lg border border-k-line bg-k-mist p-6">
              <span className="flex size-10 items-center justify-center rounded-k bg-white text-k-blue" aria-hidden>
                <Lock className="size-5" />
              </span>
              <h3 className="mt-4 text-[1.0625rem]">Sécurité des accès internes</h3>
              <p className="mt-2 text-[0.875rem] leading-relaxed text-k-muted">
                Les membres de l&apos;équipe KEMTA disposent de permissions limitées à leur fonction : un chargé de
                suivi ne peut pas modifier une facture, un comptable ne peut pas valider une preuve technique. Ces
                actions sont enregistrées et consultables.
              </p>
            </div>

            <div className="rounded-k-lg border border-k-line bg-white p-6">
              <span className="flex size-10 items-center justify-center rounded-k bg-k-green-pale text-k-green-dark" aria-hidden>
                <Fingerprint className="size-5" />
              </span>
              <h3 className="mt-4 text-[1.0625rem]">Vérification des entreprises</h3>
              <p className="mt-2 text-[0.875rem] leading-relaxed text-k-muted">
                Le badge « Vérifiée » suppose un dossier complet : registre de commerce, attestation fiscale,
                couverture sociale, assurance le cas échéant, et des références de chantier contrôlables. Un dossier
                incomplet est refusé, un dossier contesté peut être suspendu.
              </p>
              <ButtonLink to="/entreprises-btp" variant="secondary" size="sm" className="mt-4">
                Voir les entreprises vérifiées
              </ButtonLink>
            </div>

            <div className="rounded-k-lg border border-k-blue-line bg-k-blue-soft/60 p-6">
              <span className="flex size-10 items-center justify-center rounded-k bg-white text-k-blue" aria-hidden>
                <ShieldCheck className="size-5" />
              </span>
              <h3 className="mt-4 text-[1.0625rem]">Signaler un problème</h3>
              <p className="mt-2 text-[0.875rem] leading-relaxed text-k-muted">
                Une suspicion de fraude, un démarchage abusif au nom de KEMTA ou un chantier non conforme ? Écrivez à
                <strong> securite@kemta.cm</strong> : chaque signalement est examiné, y compris anonymement.
              </p>
            </div>
          </div>
        </div>
      </Section>
    </>
  );
}
