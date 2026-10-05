import { Link } from 'react-router-dom';
import { ArrowRight, Check, Sparkles } from 'lucide-react';

import { Seo } from '@/components/Seo';
import { Section, SectionHeading } from '@/components/layout/Section';
import { Button, ButtonLink } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { CardSkeleton } from '@/components/ui/Feedback';
import { SERVICES } from '@/lib/content';
import { usePlans } from '@/lib/hooks';
import { formatXaf } from '@/lib/format';
import { breadcrumbSchema, faqSchema } from '@/lib/seo';
import { Accordion } from '@/components/ui/Accordion';

const PRICING_FAQ = [
  {
    id: 'prix-derive',
    question: "Comment un dépassement de budget est-il traité ?",
    answer:
      "Il est signalé dès qu'il est constaté, avec le poste concerné, le montant et la cause. Le décaissement suivant est suspendu jusqu'à votre validation écrite. Nous ne payons jamais un dépassement sans votre accord.",
  },
  {
    id: 'prix-deplacement',
    question: 'Les frais de déplacement sont-ils inclus ?',
    answer:
      "Les visites dans les villes couvertes (Bafoussam, Douala, Yaoundé) sont incluses dans le tarif mensuel. Pour une localité éloignée, les frais réels de déplacement sont annoncés avant l'intervention.",
  },
  {
    id: 'prix-entreprise',
    question: "L'inscription d'une entreprise est-elle payante ?",
    answer:
      "Non. La création du profil, le dépôt des pièces et la vérification KEMTA sont gratuits. Les offres payantes concernent la visibilité et le nombre de candidatures aux marchés.",
  },
  {
    id: 'prix-facture',
    question: 'Recevons-nous une facture pour chaque paiement ?',
    answer:
      "Oui, chaque encaissement — Mobile Money, Orange Money ou carte — génère une facture KEMTA téléchargeable depuis votre espace, avec référence, montant et date.",
  },
];

export default function PricingPage() {
  const { data: plans, isLoading } = usePlans();

  return (
    <>
      <Seo
        title="Tarifs et offres"
        description="Tarifs KEMTA : suivi de chantier à partir de 150 000 FCFA par mois, entretien de propriété à partir de 90 000 FCFA par an, offres entreprises du plan gratuit au plan Premium."
        path="/tarifs"
        jsonLd={[
          breadcrumbSchema([
            { name: 'Accueil', path: '/' },
            { name: 'Tarifs', path: '/tarifs' },
          ]),
          faqSchema(PRICING_FAQ.map(({ question, answer }) => ({ question, answer }))),
        ]}
      />

      <section className="border-b border-k-line bg-white">
        <div className="k-container py-14 lg:py-20">
          <span className="k-eyebrow">
            <span className="h-px w-8 bg-k-green" aria-hidden />
            Tarifs
          </span>
          <h1 className="mt-5 max-w-[26ch]">Des prix affichés, des devis écrits, aucune commission cachée</h1>
          <p className="k-lead mt-5">
            KEMTA se rémunère sur la prestation de suivi, jamais sur des rétrocommissions d&apos;entreprises. Les
            montants des abonnements entreprises sont servis par notre système : ils sont donc toujours à jour.
          </p>
        </div>
      </section>

      <Section>
        <SectionHeading
          eyebrow="Prestations aux particuliers"
          title="Suivi de chantier, construction et entretien"
          description="Le montant dépend de la surface, de la complexité et de la fréquence des visites. Le devis est établi après l'appel de qualification, sans frais tant que vous n'avez pas validé."
        />
        <div className="mt-10 overflow-hidden rounded-k-lg border border-k-line">
          <table className="w-full border-collapse text-left">
            <thead className="bg-k-mist">
              <tr>
                <th scope="col" className="px-5 py-3.5 text-[0.8125rem] font-semibold text-k-ink">
                  Prestation
                </th>
                <th scope="col" className="hidden px-5 py-3.5 text-[0.8125rem] font-semibold text-k-ink sm:table-cell">
                  Ce qui est inclus
                </th>
                <th scope="col" className="px-5 py-3.5 text-right text-[0.8125rem] font-semibold text-k-ink">
                  Repère tarifaire
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-k-line bg-white">
              {SERVICES.map((service) => (
                <tr key={service.slug} className="align-top">
                  <td className="px-5 py-4">
                    <Link to={`/services/${service.slug}`} className="font-display text-[0.9375rem] font-semibold text-k-ink hover:text-k-blue">
                      {service.title}
                    </Link>
                    <p className="mt-1 text-[0.8125rem] text-k-muted">{service.promise}</p>
                  </td>
                  <td className="hidden px-5 py-4 text-[0.8125rem] text-k-muted sm:table-cell">
                    {service.bullets[0]} · {service.bullets[1]}
                  </td>
                  <td className="px-5 py-4 text-right text-[0.875rem] font-medium text-k-blue">
                    {service.startingPrice}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4 text-[0.8125rem] text-k-muted">
          Frais de mise en relation, contrôle technique et déplacements hors Bafoussam, Douala et Yaoundé : indiqués dans le
          devis avant démarrage.
        </p>
      </Section>

      <Section tone="mist">
        <SectionHeading
          eyebrow="Offres entreprises BTP"
          title="Pour les entreprises du réseau KEMTA"
          description="Créez votre profil, faites vérifier votre dossier et candidatez aux marchés. Vous changez d'offre quand votre activité le justifie — sans engagement de durée."
        />

        <div className="mt-10 grid gap-6 lg:grid-cols-3">
          {isLoading
            ? Array.from({ length: 3 }).map((_, index) => <CardSkeleton key={index} lines={5} />)
            : (plans ?? []).map((plan) => {
                const recommended = plan.code === 'PRO';
                return (
                  <article
                    key={plan.id}
                    className={`flex flex-col rounded-k-lg border bg-white p-6 ${
                      recommended ? 'border-k-green shadow-k' : 'border-k-line'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="text-[1.125rem]">{plan.name}</h3>
                      {recommended ? (
                        <Badge tone="green" size="sm">
                          <Sparkles className="size-3" aria-hidden />
                          Recommandé
                        </Badge>
                      ) : null}
                    </div>

                    <p className="mt-2 text-[0.875rem] text-k-muted">{plan.tagline}</p>

                    <p className="mt-5 font-display text-[1.75rem] font-bold text-k-ink">
                      {plan.price_xaf > 0 ? formatXaf(plan.price_xaf) : 'Gratuit'}
                      {plan.price_xaf > 0 ? (
                        <span className="ml-1 text-[0.8125rem] font-normal text-k-muted">
                          / {plan.interval === 'YEARLY' ? 'an' : 'mois'}
                        </span>
                      ) : null}
                    </p>

                    <ul className="mt-5 flex-1 space-y-2.5">
                      {(plan.features ?? []).slice(0, 6).map((feature) => (
                        <li key={feature} className="flex items-start gap-2.5 text-[0.875rem] text-k-ink/85">
                          <Check className="mt-0.5 size-3.5 shrink-0 text-k-green" aria-hidden />
                          {feature}
                        </li>
                      ))}
                    </ul>

                    {plan.trial_days ? (
                      <p className="mt-4 text-[0.8125rem] text-k-green-dark">
                        {plan.trial_days} jours d&apos;essai inclus
                      </p>
                    ) : null}

                    <ButtonLink
                      to="/espace-entreprise"
                      variant={recommended ? 'primary' : 'secondary'}
                      block
                      className="mt-6"
                    >
                      {plan.code === 'FREE' ? 'Commencer gratuitement' : `Choisir ${plan.name}`}
                    </ButtonLink>
                  </article>
                );
              })}
        </div>

        <p className="mt-6 text-[0.8125rem] text-k-muted">
          Les prix sont affichés hors taxes et encaissés en francs CFA via Mobile Money ou carte bancaire. La
          facturation est émise automatiquement.
        </p>
      </Section>

      <Section>
        <div className="grid gap-12 lg:grid-cols-[0.9fr_1.1fr] lg:gap-16">
          <SectionHeading eyebrow="Questions sur les tarifs" title="Ce qui est facturé, et ce qui ne l'est pas" />
          <Accordion items={PRICING_FAQ} />
        </div>

        <div className="mt-12 flex flex-col items-start justify-between gap-6 rounded-k-lg border border-k-blue-line bg-k-blue-soft/50 p-6 md:flex-row md:items-center">
          <div>
            <p className="font-display text-[1.0625rem] font-semibold text-k-ink">
              Vous hésitez entre plusieurs formules ?
            </p>
            <p className="mt-1.5 text-[0.875rem] text-k-muted">
              Décrivez votre projet : nous vous recommandons la formule adaptée, sans chercher à vendre la plus
              chère.
            </p>
          </div>
          <div className="flex shrink-0 flex-col gap-2.5 sm:flex-row">
            <ButtonLink to="/demande" iconRight={<ArrowRight className="size-4" aria-hidden />}>
              Déposer une demande
            </ButtonLink>
            <Button variant="secondary" onClick={() => window.open('https://wa.me/237600000000', '_blank')}>
              Écrire sur WhatsApp
            </Button>
          </div>
        </div>
      </Section>
    </>
  );
}
