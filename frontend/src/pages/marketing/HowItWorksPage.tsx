import { ArrowRight, BellRing, Camera, CheckCircle2, CreditCard, FileSignature, UserCheck } from 'lucide-react';

import { Seo } from '@/components/Seo';
import { Section, SectionHeading } from '@/components/layout/Section';
import { ButtonLink } from '@/components/ui/Button';
import { HowItWorks, Tracking } from '@/components/home/Process';
import { DashboardPreview } from '@/components/home/Product';
import { Faq } from '@/components/home/Proof';
import { breadcrumbSchema } from '@/lib/seo';

const DETAILS = [
  {
    icon: FileSignature,
    title: 'Vous validez un cadre écrit',
    text: "Avant toute intervention, vous recevez un devis qui précise la mission, les livrables, la fréquence des visites, les tarifs et les conditions d'arrêt. Rien ne commence sans votre accord.",
  },
  {
    icon: UserCheck,
    title: 'Un chargé de suivi nommé',
    text: "Un interlocuteur unique, joignable par téléphone et WhatsApp, qui connaît votre dossier, parle à l'entreprise et vous rend compte. Fini les groupes WhatsApp interminables.",
  },
  {
    icon: Camera,
    title: 'La preuve avant la parole',
    text: "Chaque visite produit des photos horodatées et géolocalisées, un relevé d'avancement et les points bloquants. Le rapport est publié dans votre espace, pas envoyé en pièce jointe.",
  },
  {
    icon: CreditCard,
    title: 'Vous payez ce qui est fait',
    text: "Les décaissements sont rattachés aux étapes validées. Un dépassement est signalé avant paiement, jamais après. Chaque mouvement génère une facture traçable.",
  },
  {
    icon: BellRing,
    title: 'Vous êtes alerté, pas noyé',
    text: "Retard, malfaçon, pièce manquante, visite planifiée : vous recevez une notification uniquement quand une décision est attendue de votre part.",
  },
  {
    icon: CheckCircle2,
    title: 'La réception est documentée',
    text: "En fin de chantier, nous listons les réserves, suivons leur levée et constituons le dossier de garantie. Votre bien est réceptionné sur des faits, pas sur une poignée de main.",
  },
];

export default function HowItWorksPage() {
  return (
    <>
      <Seo
        title="Comment ça marche — de la demande à la livraison"
        description="Le fonctionnement de KEMTA étape par étape : demande guidée, appel de qualification, cadre écrit, suivi documenté par preuves terrain et décaissements conditionnés."
        path="/comment-ca-marche"
        jsonLd={breadcrumbSchema([
          { name: 'Accueil', path: '/' },
          { name: 'Comment ça marche', path: '/comment-ca-marche' },
        ])}
      />

      <section className="border-b border-k-line bg-white">
        <div className="k-container py-14 lg:py-20">
          <span className="k-eyebrow">
            <span className="h-px w-8 bg-k-green" aria-hidden />
            Fonctionnement
          </span>
          <h1 className="mt-5 max-w-[26ch]">Un chantier se suit sur des faits, pas sur des promesses</h1>
          <p className="k-lead mt-5">
            KEMTA a été construit pour les propriétaires qui ne peuvent pas se rendre sur leur terrain tous les
            jours : diaspora, cadres en activité, bailleurs, entreprises. Voici précisément comment nous
            travaillons.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <ButtonLink to="/demande" size="lg">
              Démarrer une demande
            </ButtonLink>
            <ButtonLink to="/tarifs" variant="secondary" size="lg">
              Voir les offres
            </ButtonLink>
          </div>
        </div>
      </section>

      <HowItWorks />
      <Tracking />
      <DashboardPreview />

      <Section>
        <SectionHeading
          eyebrow="Les règles du jeu"
          title="Six engagements que nous tenons sur chaque dossier"
          description="Ces engagements figurent dans nos conditions générales. S'ils ne sont pas respectés, vous pouvez suspendre la mission sans frais."
        />
        <div className="mt-10 grid gap-x-10 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
          {DETAILS.map((item) => {
            const Icon = item.icon;
            return (
              <div key={item.title} className="border-t border-k-line pt-5">
                <span className="flex size-9 items-center justify-center rounded-k bg-k-blue-soft text-k-blue" aria-hidden>
                  <Icon className="size-4" />
                </span>
                <h3 className="mt-4 text-[1rem]">{item.title}</h3>
                <p className="mt-2 text-[0.875rem] leading-relaxed text-k-muted">{item.text}</p>
              </div>
            );
          })}
        </div>
      </Section>

      <Faq />

      <Section tone="blue" className="!py-14 k-grid-lines">
        <div className="flex flex-col items-start justify-between gap-6 md:flex-row md:items-center">
          <div>
            <h2 className="max-w-[24ch] text-white">Prêt à confier votre projet à une équipe qui documente tout ?</h2>
            <p className="mt-3 max-w-2xl text-[0.9375rem] text-white/75">
              Le formulaire prend six minutes. Un conseiller vous rappelle sous 48 heures ouvrées avec une première
              analyse gratuite.
            </p>
          </div>
          <ButtonLink
            to="/demande"
            variant="success"
            size="lg"
            iconRight={<ArrowRight className="size-4" aria-hidden />}
            className="shrink-0"
          >
            Commencer maintenant
          </ButtonLink>
        </div>
      </Section>
    </>
  );
}
