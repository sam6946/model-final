import {
  Building2,
  ClipboardCheck,
  Compass,
  FileCheck2,
  HardHat,
  Handshake,
  Home,
  Landmark,
  ListChecks,
  Receipt,
  Ruler,
  ShieldCheck,
  Smartphone,
  Video,
  Wrench,
} from 'lucide-react';

/**
 * Contenu éditorial du site.
 *
 * Il est centralisé ici (et non dispersé dans les composants) pour que la
 * direction éditoriale reste cohérente : une phrase par promesse, aucune
 * répétition d'une section à l'autre, vocabulaire du marché camerounais.
 */

export const HERO = {
  eyebrow: 'Suivi de chantier & gestion immobilière · Cameroun',
  title: 'Confiez-nous votre projet. Suivez-le depuis n\'importe où.',
  lead:
    'KEMTA pilote votre construction, surveille votre chantier et entretient votre propriété au Cameroun. Vous recevez des preuves photo horodatées, un budget contrôlé poste par poste et un interlocuteur unique — depuis votre téléphone, même à 6 000 km.',
  primaryCta: 'Démarrer une demande',
  primaryHint: 'Réponse d\'un conseiller sous 48 h ouvrées',
  secondaryCta: 'Voir comment ça marche',
  guarantees: [
    'Aucun engagement avant le devis',
    'Entreprises BTP vérifiées pièce par pièce',
    'Vos données restent confidentielles',
  ],
};

export type ServiceBlock = {
  slug: string;
  title: string;
  promise: string;
  description: string;
  icon: typeof Building2;
  bullets: string[];
  startingPrice: string;
};

export const SERVICES: ServiceBlock[] = [
  {
    slug: 'construire',
    title: 'Faire construire',
    promise: 'De la première brique à la remise des clés',
    description:
      'Nous cadrons votre budget, sélectionnons l\'entreprise BTP, puis suivons le chantier étape par étape avec un contrôle technique et financier indépendant.',
    icon: HardHat,
    bullets: [
      'Étude du projet, plans et métrés vérifiés',
      'Appel d\'offres auprès d\'entreprises vérifiées',
      'Contrôle des étapes avant chaque décaissement',
      'Réception des travaux et dossier de garantie',
    ],
    startingPrice: 'Devis sur mesure',
  },
  {
    slug: 'suivi-chantier',
    title: 'Suivre un chantier en cours',
    promise: 'Reprenez le contrôle de votre chantier',
    description:
      'Votre chantier est commencé, vous êtes loin ou vous doutez de l\'avancement réel : nous auditons la situation puis prenons le suivi en main.',
    icon: Ruler,
    bullets: [
      'Audit d\'avancement et de conformité sous 5 jours',
      'Rapport photo hebdomadaire horodaté',
      'Contrôle du budget réellement consommé',
      'Alerte immédiate en cas d\'écart ou d\'arrêt',
    ],
    startingPrice: 'À partir de 150 000 FCFA / mois',
  },
  {
    slug: 'entretien-propriete',
    title: 'Entretenir une propriété',
    promise: 'Votre patrimoine reste en bon état, même sans vous',
    description:
      'Villas, immeubles et locaux : visites planifiées, petites réparations, suivi des locataires et compte rendu à chaque passage.',
    icon: Wrench,
    bullets: [
      'Visites programmées (mensuel à annuel)',
      'Carnet d\'entretien numérique par bien',
      'Interventions correctives documentées',
      'Photos avant / après systématiques',
    ],
    startingPrice: 'À partir de 90 000 FCFA / an',
  },
  {
    slug: 'diagnostic-patrimoine',
    title: 'Auditer un patrimoine',
    promise: 'Savoir exactement ce que vous possédez',
    description:
      'Inventaire, état des lieux, valeur estimée et plan d\'entretien priorisé pour préparer une location, une vente ou une succession.',
    icon: ClipboardCheck,
    bullets: [
      'Inventaire photographique complet',
      'État des lieux et relevé des désordres',
      'Estimation de la valeur locative',
      'Plan d\'action hiérarchisé et chiffré',
    ],
    startingPrice: 'Forfait par bien',
  },
];

export const HOW_IT_WORKS = [
  {
    step: '01',
    title: 'Vous décrivez votre besoin',
    description:
      'Un formulaire guidé en 4 étapes — construire, suivre un chantier existant, entretenir ou autre besoin. Vous pouvez l\'interrompre et reprendre plus tard.',
    icon: Compass,
    duration: '6 minutes',
  },
  {
    step: '02',
    title: 'Un conseiller vous appelle',
    description:
      'Un chargé de suivi KEMTA vous rappelle sous 48 h ouvrées pour qualifier le dossier, vérifier le terrain et cadrer le budget réaliste.',
    icon: Smartphone,
    duration: '48 h ouvrées',
  },
  {
    step: '03',
    title: 'Le projet est cadré et lancé',
    description:
      'Devis détaillé, entreprise sélectionnée, calendrier et budget par poste. Vous validez en ligne, sans engagement caché.',
    icon: FileCheck2,
    duration: '5 à 10 jours',
  },
  {
    step: '04',
    title: 'Vous suivez tout à distance',
    description:
      'Preuves photo horodatées, avancement par phase, dépenses engagées, prochaine visite : tout est dans votre espace client.',
    icon: ListChecks,
    duration: 'Chaque semaine',
  },
];

export const TRACKING_PILLARS = [
  {
    title: 'Preuves terrain',
    description:
      'Chaque passage sur site produit des photos géolocalisées et horodatées, avec le nom du technicien et la phase concernée. Impossible de déclarer un travail non fait.',
    icon: ShieldCheck,
  },
  {
    title: 'Avancement transparent',
    description:
      'Le chantier est découpé en phases pondérées. Votre avancement global est la moyenne réelle des phases validées, jamais une estimation commerciale.',
    icon: Ruler,
  },
  {
    title: 'Contrôle financier',
    description:
      'Le budget est réparti par poste (matériaux, main-d\'œuvre, transport, études). Chaque dépense se rattache à une phase et à une facture.',
    icon: Receipt,
  },
  {
    title: 'Un seul interlocuteur',
    description:
      'Vous n\'arbitrez plus entre le maçon, le ferrailleur et le plombier : KEMTA coordonne et vous alerte en cas de blocage.',
    icon: Handshake,
  },
];

export const MAINTENANCE_STEPS = [
  { title: 'Vous choisissez la fréquence', description: 'Mensuelle, trimestrielle, semestrielle ou annuelle, selon l\'usage du bien.' },
  { title: 'Le technicien intervient', description: 'Contrôle des réseaux, étanchéité, menuiseries, sécurité, extérieurs — avec photos.' },
  { title: 'Vous recevez le compte rendu', description: 'Ce qui a été vérifié, les désordres constatés, les réparations proposées et leur coût.' },
  { title: 'Les réparations sont suivies', description: 'Chaque intervention est tracée : devis validé, travail réalisé, photo avant / après.' },
];

export const FINANCIAL_CONTROL = [
  {
    title: 'Budget verrouillé par poste',
    description:
      'Matériaux, main-d\'œuvre, transport, location et études : chaque poste a son enveloppe. Un dépassement déclenche une alerte avant de payer.',
  },
  {
    title: 'Décaissements conditionnés',
    description:
      'Aucun paiement d\'étape sans preuve terrain validée. Le solde du projet reste visible en permanence.',
  },
  {
    title: 'Facture KEMTA à chaque mouvement',
    description:
      'Chaque encaissement — Mobile Money, Orange Money ou carte — génère une facture traçable, utile pour votre comptabilité et votre banque.',
  },
  {
    title: 'Historique inaltérable',
    description:
      'Journal de bord horodaté : qui a fait quoi, quand, avec quelle photo. En cas de litige, le dossier parle pour vous.',
  },
];

export const ECOSYSTEM_PROMISES = [
  {
    title: 'Entreprises vérifiées',
    description:
      'Registre de commerce, attestation fiscale, CNPS, références de chantier : le dossier est contrôlé avant l\'attribution du badge.',
    icon: Building2,
  },
  {
    title: 'Réalisations authentifiées',
    description:
      'Chaque réalisation publiée affiche les photos avant / après, la durée réelle et le budget quand l\'entreprise l\'autorise.',
    icon: Landmark,
  },
  {
    title: 'Marchés et opportunités',
    description:
      'Les appels d\'offres privés publiés sur KEMTA sont réservés aux entreprises du réseau, avec candidature et instruction en ligne.',
    icon: Handshake,
  },
  {
    title: 'Réputation mesurée',
    description:
      'Les avis proviennent uniquement de clients ayant un projet suivi sur KEMTA : qualité, respect des délais, communication.',
    icon: Video,
  },
];

export const TRUST_COMMITMENTS = [
  {
    title: 'Téléphone vérifié, compte protégé',
    description:
      'L\'accès se fait par un code SMS à usage unique. Aucun mot de passe n\'est jamais transmis par message.',
    icon: Smartphone,
  },
  {
    title: 'Documents d\'entreprise contrôlés',
    description:
      'Les pièces administratives sont examinées par l\'équipe KEMTA avant toute publication du profil.',
    icon: FileCheck2,
  },
  {
    title: 'Paiements idempotents et tracés',
    description:
      'Chaque transaction porte une référence unique : impossible d\'être débité deux fois pour le même paiement.',
    icon: Receipt,
  },
  {
    title: 'Données hébergées et cloisonnées',
    description:
      'Chaque client ne voit que ses projets. Les accès internes sont journalisés et limités par rôle.',
    icon: ShieldCheck,
  },
];

export const COMPANY_STEPS = [
  { title: 'Créez votre profil', description: 'Identité légale, corps d\'état, zone d\'intervention, effectifs et matériel.' },
  { title: 'Déposez vos pièces', description: 'RCCM, attestation fiscale, CNPS, assurance : déposées en photo, vérifiées par KEMTA.' },
  { title: 'Publiez vos réalisations', description: 'Photos avant / après, surface, durée, budget (affichage à votre convenance).' },
  { title: 'Recevez des marchés', description: 'Candidaturez aux appels d\'offres publiés et échangez avec les clients vérifiés.' },
  { title: 'Construisez votre réputation', description: 'Chaque chantier suivi génère un avis vérifié qui renforce votre positionnement.' },
];

export const HOME_SERVICE_OPTIONS = [
  {
    value: 'BUILD_PROJECT',
    label: 'Construire un projet',
    description: 'Villa, immeuble, local commercial ou bâtiment professionnel.',
    icon: Building2,
  },
  {
    value: 'EXISTING_SITE',
    label: 'Suivre un chantier existant',
    description: 'Chantier commencé, à reprendre, à contrôler ou à accélérer.',
    icon: Ruler,
  },
  {
    value: 'MAINTENANCE',
    label: 'Entretenir une propriété',
    description: 'Visites régulières, réparations et suivi de vos biens.',
    icon: Home,
  },
  {
    value: 'OTHER',
    label: 'Autre besoin',
    description: 'Audit, succession, litige, achat de terrain, conseil.',
    icon: Compass,
  },
] as const;

export type ServiceKindValue = (typeof HOME_SERVICE_OPTIONS)[number]['value'];
