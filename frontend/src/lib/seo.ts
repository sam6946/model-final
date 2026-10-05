/**
 * Référencement et partage social.
 *
 * Le site est utilisé depuis la diaspora : les liens doivent produire un aperçu
 * propre sur WhatsApp, Facebook et LinkedIn, et les pages doivent être indexables
 * avec des URL lisibles (`/services/suivi-chantier`, `/entreprises-btp`…).
 */

export const SITE_URL = 'https://kemta.cm';
export const SITE_NAME = 'KEMTA';
export const DEFAULT_OG_IMAGE = `${SITE_URL}/images/og-kemta.jpg`;

const PHONE = '+237600000000';

export const ORGANIZATION_SCHEMA = {
  '@context': 'https://schema.org',
  '@type': 'ProfessionalService',
  name: SITE_NAME,
  description:
    "Suivi de chantier à distance, construction, contrôle de budget et entretien de propriété au Cameroun.",
  url: SITE_URL,
  telephone: PHONE,
  email: 'contact@kemta.cm',
  areaServed: [
    { '@type': 'Country', name: 'Cameroun' },
    { '@type': 'City', name: 'Douala' },
    { '@type': 'City', name: 'Yaoundé' },
  ],
  address: {
    '@type': 'PostalAddress',
    streetAddress: 'Rue Njo-Njo, Bonanjo',
    addressLocality: 'Douala',
    addressRegion: 'Littoral',
    addressCountry: 'CM',
  },
  openingHours: 'Mo-Sa 07:30-18:30',
  priceRange: 'FCFA',
  sameAs: ['https://wa.me/237600000000'],
};

export function serviceSchema(input: { name: string; description: string; url: string }) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Service',
    serviceType: input.name,
    description: input.description,
    url: `${SITE_URL}${input.url}`,
    provider: { '@type': 'Organization', name: SITE_NAME, telephone: PHONE },
    areaServed: { '@type': 'Country', name: 'Cameroun' },
  };
}

export function faqSchema(items: Array<{ question: string; answer: string }>) {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: items.map((item) => ({
      '@type': 'Question',
      name: item.question,
      acceptedAnswer: { '@type': 'Answer', text: item.answer },
    })),
  };
}

export function breadcrumbSchema(trail: Array<{ name: string; path: string }>) {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: trail.map((item, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: item.name,
      item: `${SITE_URL}${item.path}`,
    })),
  };
}
