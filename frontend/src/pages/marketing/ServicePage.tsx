import { Link, useParams } from 'react-router-dom';
import { ArrowRight, Check, ChevronRight, Clock, FileText, HelpCircle, ShieldCheck } from 'lucide-react';

import { SERVICES } from '@/lib/content';
import { Section, SectionHeading } from '@/components/layout/Section';
import { ButtonLink } from '@/components/ui/Button';
import { Media, type MediaName } from '@/components/ui/Media';
import { Seo } from '@/components/Seo';
import { breadcrumbSchema, serviceSchema } from '@/lib/seo';
import NotFoundPage from '@/pages/NotFoundPage';

type ServiceDetail = {
  media: MediaName;
  mediaAlt: string;
  intro: string;
  included: Array<{ title: string; text: string }>;
  timeline: Array<{ step: string; title: string; duration: string }>;
  pricing: Array<{ label: string; detail: string; amount: string }>;
  faq: Array<{ question: string; answer: string }>;
};

const DETAILS: Record<string, ServiceDetail> = {
  construire: {
    media: 'equipe-btp',
    mediaAlt: "Équipe BTP camerounaise sur la dalle d'un bâtiment en construction",
    intro:
      "Construire au Cameroun sans être sur place expose à trois risques : un budget qui dérape, des malfaçons invisibles et un chantier qui s'arrête. KEMTA encadre les trois, de l'étude du terrain à la remise des clés.",
    included: [
      {
        title: "Étude et cadrage du projet",
        text: "Vérification du titre foncier, contrôle des plans et du métré, estimation réaliste du budget par poste avant tout engagement.",
      },
      {
        title: "Sélection de l'entreprise",
        text: "Appel d'offres auprès d'entreprises vérifiées du réseau KEMTA, comparaison des offres et recommandation argumentée.",
      },
      {
        title: "Suivi technique du chantier",
        text: "Visites planifiées à chaque étape clé : implantation, fondations, élévation, dalle, charpente, finitions.",
      },
      {
        title: "Contrôle budgétaire",
        text: "Chaque dépense est rattachée à un poste et à une phase validée. Les décaissements suivent l'avancement réel.",
      },
      {
        title: "Reporting client",
        text: "Rapport hebdomadaire avec photos horodatées, avancement pondéré, points bloquants et prochaines actions.",
      },
      {
        title: "Réception et garanties",
        text: "Levée des réserves avec l'entreprise, constitution du dossier de garantie et remise des documents de fin de chantier.",
      },
    ],
    timeline: [
      { step: "1", title: "Cadrage et devis KEMTA", duration: "3 à 7 jours" },
      { step: "2", title: "Appel d'offres et choix de l'entreprise", duration: "2 à 3 semaines" },
      { step: "3", title: "Travaux suivis par KEMTA", duration: "selon le programme" },
      { step: "4", title: "Réception et dossier final", duration: "1 à 2 semaines" },
    ],
    pricing: [
      { label: "Frais de cadrage", detail: "Étude, métré, appel d'offres", amount: "Sur devis" },
      {
        label: "Suivi de chantier",
        detail: "Par mois, selon la surface et la complexité",
        amount: "À partir de 150 000 FCFA / mois",
      },
      { label: "Contrôle technique renforcé", detail: "Chantiers complexes ou R+2 et plus", amount: "Sur devis" },
    ],
    faq: [
      {
        question: "Puis-je garder mon propre entrepreneur ?",
        answer:
          "Oui. KEMTA peut suivre un chantier mené par l'entreprise de votre choix. Nous auditons d'abord sa situation, puis nous assurons le contrôle technique et financier à votre place.",
      },
      {
        question: "Que se passe-t-il si les travaux sont mal faits ?",
        answer:
          "L'écart est documenté dans le rapport de visite, l'entreprise reçoit un délai de correction et le décaissement de l'étape suivante est suspendu tant que la reprise n'est pas validée.",
      },
      {
        question: "KEMTA peut-il acheter les matériaux à ma place ?",
        answer:
          "Nous contrôlons les achats, vérifions les quantités et les prix par rapport au marché local et centralisons les justificatifs. La commande reste validée par vous.",
      },
    ],
  },

  "suivi-chantier": {
    media: "hero-suivi-chantier",
    mediaAlt: "Chargé de suivi KEMTA relevant l'avancement d'un chantier sur son téléphone",
    intro:
      "Votre chantier a commencé sans vous, ou votre entreprise ne répond plus. Nous établissons d'abord la réalité du terrain — ce qui a été payé, ce qui a été exécuté, ce qui manque — avant de reprendre le suivi.",
    included: [
      {
        title: "Audit d'avancement sous 5 jours",
        text: "Visite approfondie du site : état des ouvrages, conformité aux plans, quantités réellement mises en œuvre.",
      },
      {
        title: "Rapport photo hebdomadaire",
        text: "Chaque semaine, un rapport daté avec photos, avancement par phase et points d'attention.",
      },
      {
        title: "Contrôle du budget consommé",
        text: "Rapprochement entre les sommes versées, les matériaux livrés et les travaux exécutés.",
      },
      {
        title: "Relance et coordination",
        text: "Nous relançons l'entreprise, organisons les réunions de chantier et consignons les engagements pris.",
      },
      {
        title: "Alerte immédiate",
        text: "Arrêt de chantier, malfaçon, dépassement de budget ou retard critique : vous êtes prévenu sous 24 h.",
      },
      {
        title: "Dossier en cas de litige",
        text: "Journal de bord horodaté, utilisable auprès d'un assureur, d'une banque ou d'un tribunal.",
      },
    ],
    timeline: [
      { step: "1", title: "Audit initial sur site", duration: "3 à 5 jours" },
      { step: "2", title: "Rapport de situation et plan de reprise", duration: "48 h après audit" },
      { step: "3", title: "Suivi hebdomadaire", duration: "chaque semaine" },
      { step: "4", title: "Clôture ou changement d'entreprise", duration: "selon le dossier" },
    ],
    pricing: [
      { label: "Audit initial", detail: "Visite complète et rapport de situation", amount: "Sur devis" },
      { label: "Suivi mensuel", detail: "4 visites et rapports par mois", amount: "À partir de 150 000 FCFA / mois" },
      { label: "Suivi renforcé", detail: "Chantier critique, 8 visites par mois", amount: "Sur devis" },
    ],
    faq: [
      {
        question: "Mon entreprise peut-elle refuser ce suivi ?",
        answer:
          "Le suivi fait partie de vos conditions contractuelles : vous êtes le maître d'ouvrage. Si l'entreprise s'y oppose, c'est en soi une information utile sur sa fiabilité.",
      },
      {
        question: "Intervenez-vous partout au Cameroun ?",
        answer:
          "Nous couvrons Douala, Yaoundé et les principales villes. Pour une localité éloignée, nous indiquons les frais de déplacement avant l'intervention.",
      },
    ],
  },

  "entretien-propriete": {
    media: "entretien-toiture",
    mediaAlt: "Techniciens KEMTA réparant la toiture et la gouttière d'une villa",
    intro:
      "Une villa fermée se dégrade deux fois plus vite : infiltration oubliée, menuiserie gonflée, peinture qui s'écaille, cour envahie. KEMTA passe régulièrement et vous envoie la preuve de chaque visite.",
    included: [
      {
        title: "Plan d'entretien personnalisé",
        text: "Selon le type de bien, sa vétusté et son usage : points de contrôle, fréquence et priorités.",
      },
      {
        title: "Visites programmées",
        text: "Mensuelles, trimestrielles ou semestrielles, annoncées à l'avance et confirmées au client.",
      },
      {
        title: "Compte rendu systématique",
        text: "Photos, points vérifiés, désordres constatés, réparations proposées avec estimation de coût.",
      },
      {
        title: "Petites réparations",
        text: "Plomberie, électricité, serrurerie, peinture, nettoyage : réalisées après votre accord.",
      },
      {
        title: "Gestion locative légère",
        text: "État des lieux, suivi des loyers et des occupants, préparation des entrées et sorties.",
      },
      {
        title: "Carnet numérique du bien",
        text: "Historique complet par propriété : interventions, photos avant / après, factures.",
      },
    ],
    timeline: [
      { step: "1", title: "État des lieux initial", duration: "une visite" },
      { step: "2", title: "Plan d'entretien validé", duration: "48 h" },
      { step: "3", title: "Visites récurrentes", duration: "mensuel à annuel" },
      { step: "4", title: "Interventions correctives", duration: "à la demande" },
    ],
    pricing: [
      {
        label: "Entretien annuel",
        detail: "Villa ou appartement, 4 visites par an",
        amount: "À partir de 90 000 FCFA / an",
      },
      { label: "Immeuble locatif", detail: "Visite par unité et suivi des occupants", amount: "Sur devis" },
      { label: "Intervention corrective", detail: "Réparation documentée avant / après", amount: "Selon devis" },
    ],
    faq: [
      {
        question: "Mes locataires doivent-ils être présents ?",
        answer:
          "Non. Nous convenons d'un créneau avec eux, mais l'absence du locataire ne bloque pas la visite extérieure et technique. Chaque passage est documenté.",
      },
      {
        question: "Puis-je confier un bien en location courte durée ?",
        answer:
          "Oui : contrôle du ménage, de l'équipement et de l'état à chaque rotation, avec compte rendu photo.",
      },
    ],
  },

  "diagnostic-patrimoine": {
    media: "controle-financier",
    mediaAlt: "Analyse du budget et des documents d'un patrimoine immobilier à Douala",
    intro:
      "Avant de louer, vendre, transmettre ou engager des travaux, il faut savoir précisément ce que vous possédez et dans quel état. KEMTA produit un inventaire documenté, chiffré et utilisable.",
    included: [
      {
        title: "Inventaire complet",
        text: "Recensement des biens, titres, surfaces et dépendances, avec reportage photographique.",
      },
      {
        title: "État des lieux technique",
        text: "Structure, toiture, réseaux, étanchéité, sécurité : relevé des désordres et de leur gravité.",
      },
      {
        title: "Estimation de valeur",
        text: "Fourchette de valeur vénale et locative cohérente avec le marché local, sur la base d'éléments comparables.",
      },
      {
        title: "Plan d'action priorisé",
        text: "Travaux classés par urgence avec estimation de coût, pour protéger la valeur du bien.",
      },
      {
        title: "Dossier de transmission",
        text: "Documents organisés et vérifiables, utiles pour une succession, un notaire ou un financement bancaire.",
      },
      {
        title: "Restitution claire",
        text: "Un rapport écrit, présenté en visioconférence si vous êtes à l'étranger.",
      },
    ],
    timeline: [
      { step: "1", title: "Collecte des documents", duration: "2 à 5 jours" },
      { step: "2", title: "Visites et relevés", duration: "1 à 3 jours par bien" },
      { step: "3", title: "Analyse et estimation", duration: "5 jours" },
      { step: "4", title: "Restitution et plan d'action", duration: "1 séance" },
    ],
    pricing: [
      { label: "Diagnostic par bien", detail: "Inventaire, état des lieux, estimation", amount: "Sur devis" },
      { label: "Portefeuille", detail: "Plusieurs biens, tarif dégressif", amount: "Sur devis" },
    ],
    faq: [
      {
        question: "Le rapport a-t-il une valeur juridique ?",
        answer:
          "C'est un rapport d'expertise privé : il documente des constats datés et photographiés. Il peut appuyer un dossier auprès d'un avocat, d'un notaire ou d'une assurance.",
      },
      {
        question: "Combien de temps pour un bien à Yaoundé ?",
        answer:
          "Comptez une semaine entre la collecte des documents et la restitution, si l'accès au site est immédiat.",
      },
    ],
  },
};

export default function ServicePage() {
  const { slug } = useParams<{ slug: string }>();
  const service = SERVICES.find((item) => item.slug === slug);
  const detail = slug ? DETAILS[slug] : undefined;

  if (!service || !detail) return <NotFoundPage />;

  const Icon = service.icon;
  const others = SERVICES.filter((item) => item.slug !== service.slug);

  return (
    <>
      <Seo
        title={`${service.title} — ${service.promise}`}
        description={`${service.description} Prestation KEMTA au Cameroun : ${service.startingPrice}.`}
        path={`/services/${service.slug}`}
        jsonLd={[
          serviceSchema({ name: service.title, description: service.description, url: `/services/${service.slug}` }),
          breadcrumbSchema([
            { name: "Accueil", path: "/" },
            { name: "Services", path: "/#services" },
            { name: service.title, path: `/services/${service.slug}` },
          ]),
        ]}
      />

      <section className="border-b border-k-line bg-white">
        <div className="k-container py-12 lg:py-16">
          <nav aria-label="Fil d'Ariane" className="flex flex-wrap items-center gap-1.5 text-[0.8125rem] text-k-muted">
            <Link to="/" className="hover:text-k-blue">
              Accueil
            </Link>
            <ChevronRight className="size-3.5" aria-hidden />
            <Link to="/#services" className="hover:text-k-blue">
              Services
            </Link>
            <ChevronRight className="size-3.5" aria-hidden />
            <span className="text-k-ink">{service.title}</span>
          </nav>

          <div className="mt-8 grid gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:gap-16">
            <div>
              <span className="flex size-12 items-center justify-center rounded-k bg-k-blue text-white" aria-hidden>
                <Icon className="size-6" />
              </span>
              <p className="mt-5 text-[0.75rem] font-semibold uppercase tracking-[0.12em] text-k-green-dark">
                {service.promise}
              </p>
              <h1 className="mt-3 max-w-[24ch]">{service.title}</h1>
              <p className="k-lead mt-5">{detail.intro}</p>

              <div className="mt-7 flex flex-wrap items-center gap-3">
                <ButtonLink to={`/demande?service=${service.slug}`} size="lg">
                  Demander cette prestation
                </ButtonLink>
                <ButtonLink to="/tarifs" variant="secondary" size="lg">
                  Voir les tarifs
                </ButtonLink>
              </div>

              <div className="mt-7 flex flex-wrap gap-4 text-[0.8125rem] text-k-muted">
                <span className="inline-flex items-center gap-1.5">
                  <ShieldCheck className="size-3.5 text-k-green" aria-hidden />
                  Devis écrit avant engagement
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <FileText className="size-3.5 text-k-green" aria-hidden />
                  Rapport documenté à chaque visite
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <Clock className="size-3.5 text-k-green" aria-hidden />
                  Réponse sous 48 h ouvrées
                </span>
              </div>
            </div>

            <Media
              name={detail.media}
              alt={detail.mediaAlt}
              ratio="4 / 3"
              priority
              sizes="(min-width: 1024px) 45vw, 100vw"
              className="rounded-k-xl"
            />
          </div>
        </div>
      </section>

      <Section>
        <SectionHeading
          eyebrow="Ce que comprend la prestation"
          title="Des livrables précis, pas des intentions"
          description="Chaque élément ci-dessous est repris dans notre devis : vous savez exactement ce que vous recevez et à quelle fréquence."
        />
        <div className="mt-10 grid gap-x-10 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
          {detail.included.map((item) => (
            <div key={item.title} className="border-t border-k-line pt-5">
              <span className="flex size-7 items-center justify-center rounded-full bg-k-green-pale text-k-green-dark" aria-hidden>
                <Check className="size-3.5" />
              </span>
              <h3 className="mt-4 text-[1rem]">{item.title}</h3>
              <p className="mt-2 text-[0.875rem] leading-relaxed text-k-muted">{item.text}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section tone="mist">
        <div className="grid gap-12 lg:grid-cols-[0.9fr_1.1fr] lg:gap-16">
          <div>
            <SectionHeading eyebrow="Déroulé" title="Comment la mission se déroule" />
            <ol className="mt-8 space-y-5">
              {detail.timeline.map((step) => (
                <li key={step.step} className="flex gap-4">
                  <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-k-blue font-display text-[0.8125rem] font-semibold text-white" aria-hidden>
                    {step.step}
                  </span>
                  <div className="flex-1 border-b border-k-line pb-4">
                    <p className="font-display text-[1rem] font-semibold text-k-ink">{step.title}</p>
                    <p className="mt-1 text-[0.8125rem] text-k-muted">{step.duration}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>

          <div className="rounded-k-xl border border-k-line bg-white p-6">
            <h3 className="text-[1.125rem]">Repères tarifaires</h3>
            <p className="mt-2 text-[0.875rem] text-k-muted">
              Les montants dépendent de la surface, de la localisation et de la complexité. Ils sont confirmés par
              devis après l&apos;appel de qualification.
            </p>
            <ul className="mt-6 divide-y divide-k-line">
              {detail.pricing.map((line) => (
                <li key={line.label} className="flex items-start justify-between gap-6 py-4">
                  <div>
                    <p className="text-[0.9375rem] font-medium text-k-ink">{line.label}</p>
                    <p className="mt-0.5 text-[0.8125rem] text-k-muted">{line.detail}</p>
                  </div>
                  <p className="shrink-0 text-right text-[0.875rem] font-semibold text-k-blue">{line.amount}</p>
                </li>
              ))}
            </ul>
            <ButtonLink to={`/demande?service=${service.slug}`} block className="mt-6">
              Recevoir un devis
            </ButtonLink>
          </div>
        </div>
      </Section>

      <Section>
        <div className="grid gap-12 lg:grid-cols-[0.9fr_1.1fr] lg:gap-16">
          <SectionHeading
            eyebrow="Questions fréquentes"
            title={`Ce qu'on nous demande sur ${service.title.toLowerCase()}`}
          />
          <div className="space-y-6">
            {detail.faq.map((item) => (
              <div key={item.question} className="border-b border-k-line pb-5">
                <p className="flex items-start gap-2.5 font-display text-[1rem] font-semibold text-k-ink">
                  <HelpCircle className="mt-0.5 size-4 shrink-0 text-k-blue" aria-hidden />
                  {item.question}
                </p>
                <p className="mt-2 pl-6 text-[0.875rem] leading-relaxed text-k-muted">{item.answer}</p>
              </div>
            ))}
          </div>
        </div>
      </Section>

      <Section tone="mist" className="!py-14">
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <h2 className="text-[1.5rem]">Découvrir les autres prestations</h2>
          <ButtonLink to="/demande" variant="secondary" size="sm" iconRight={<ArrowRight className="size-3.5" aria-hidden />}>
            Déposer une demande
          </ButtonLink>
        </div>
        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          {others.map((item) => {
            const OtherIcon = item.icon;
            return (
              <Link
                key={item.slug}
                to={`/services/${item.slug}`}
                className="group flex flex-col rounded-k-lg border border-k-line bg-white p-5 transition-colors hover:border-k-blue-line"
              >
                <span className="flex size-9 items-center justify-center rounded-k bg-k-blue-soft text-k-blue" aria-hidden>
                  <OtherIcon className="size-4" />
                </span>
                <p className="mt-4 font-display text-[1rem] font-semibold text-k-ink">{item.title}</p>
                <p className="mt-1 text-[0.8125rem] text-k-muted">{item.promise}</p>
                <span className="mt-4 inline-flex items-center gap-1.5 text-[0.8125rem] font-medium text-k-blue">
                  Voir la prestation
                  <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" aria-hidden />
                </span>
              </Link>
            );
          })}
        </div>
      </Section>
    </>
  );
}
